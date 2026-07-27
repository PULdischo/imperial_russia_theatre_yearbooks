# Processing pipeline: PDFs → DuckDB (DashScope Qwen VL)

Originally sketched for local Qwen VL on Adroit; given the corpus is ~1,300
pages, we switched to the DashScope-hosted Qwen VL API (the approach the
original prototype notebook used) rather than standing up local GPU serving.
**Stages 1-5 below are now real, working scripts**, validated end-to-end on a
12-page pilot (see `docs/eval/run_history.csv` for the numbers). Stage 6
(interface) is still a sketch.

---

## Repo layout (as built)

```
imperial_theater_yearbooks/
  pdfs/                     # source PDFs
  docs/                     # schema.md, structural_survey.md, overview.md,
                            # research_questions.md, this file, eval/
    eval/
      gold/                 # 12-page hand-transcribed ground truth + builder scripts
      known_issues.md       # persistent ledger of extraction issues, see below
      run_history.csv       # eval_against_gold.py summary per run, over time
  pipeline/
    schemas/                # pydantic models mirroring docs/schema.md exactly
      dates.py              # best-effort Russian date -> ISO-shaped string
      roster.py             # RosterPage + flatten_roster_page
      repertoire.py         # RepertoirePage + flatten_repertoire_page
    prompts/                # roster_system.txt, repertoire_system.txt
    render_pages.py         # Stage 1
    extract.py              # Stage 2 (single-page CLI, used for smoke tests)
    run_pilot.py            # Stage 2 (batch driver over a manifest)
    parse_and_validate.py   # Stage 3
    quality_checks.py       # Stage 3.5 -- gold-free structural self-consistency checks
    eval_against_gold.py    # Stage 4
    build_duckdb.py         # Stage 5
  outputs/                  # generated, gitignored; not the dataset of record until stage 5
    pilot/                  # the 12-page validation run lives here
      images/ raw/ parsed/
      imperial_theaters.duckdb
  app/
    streamlit_app.py        # Stage 6 -- not yet built
```

`.env` (gitignored) holds `DASHSCOPE_API_KEY`. `outputs/` should be treated as
disposable working space — the `.duckdb` file is the artifact worth keeping
around; everything else can be regenerated from `pdfs/` + the pipeline
scripts + the raw JSON (which is itself cheap to keep, since re-parsing it
never requires another API call).

---

## Stage 0 — Environment

`.env` with `DASHSCOPE_API_KEY`; `pip install openai pydantic python-dotenv
pymupdf duckdb`. No GPU, no cluster access needed — this whole pipeline runs
on a laptop.

## Stage 1 — Render pages to images

`pipeline/render_pages.py`. Input: `pdfs/`. Output: `outputs/images/{page_id}.png`
+ `outputs/manifest.csv` (same columns as `docs/eval/gold/source_pages.csv`).
Idempotent (skips existing images). **DPI matters a lot**: 150dpi produced
frequent character-level misreads (digit transpositions, letter confusions);
300dpi eliminated nearly all of them in side-by-side testing. `render_pages.py`
defaults to 300.

```
python pipeline/render_pages.py --pdf-dir pdfs --out-dir outputs --dpi 300
python pipeline/render_pages.py --limit 5   # smoke test a handful of PDFs
```

## Stage 2 — Extraction (DashScope Qwen VL)

Two entry points, same underlying call:

- `pipeline/extract.py` — single page, used for iterating on prompts during
  development (`--image`, `--kind roster|repertoire`, `--page-id`, ...).
- `pipeline/run_pilot.py` — batch driver over a manifest CSV (season/city/
  entity_type per page_id). Calls the model once per page and saves **only**
  the raw JSON response to `{out-dir}/{page_id}.raw.json` — parsing is a
  separate stage (3) precisely so re-parsing after a schema/logic fix never
  requires another API call.

```
python pipeline/run_pilot.py --manifest docs/eval/gold/source_pages.csv \
    --images-dir outputs/pilot/images --out-dir outputs/pilot/raw
```

Prompt per `entity_type`: `roster_system.txt` for the five Spiski types,
`repertoire_system.txt` for Repertoire. Model: `qwen3-vl-plus` via DashScope's
OpenAI-compatible endpoint, `response_format={"type": "json_object"}`.

The RepertoireTables page-count skew in `overview.md` matters here for cost
planning: late-season Repertoire pages are ~4x the early seasons' page count
for the same span.

## Stage 3 — Parse and validate

`pipeline/parse_and_validate.py`. Reads raw JSON + the manifest, validates
each page against the pydantic models in `pipeline/schemas/`, and writes
**merged, corpus-level** CSVs (`roster_entry.csv`, `service_period.csv`,
`roster_entry_credit.csv`, `performance_session.csv`, `performance_work.csv`)
plus `validation_errors.csv` for anything that failed to parse — a bad page
never takes down the rest of the run.

```
python pipeline/parse_and_validate.py --manifest docs/eval/gold/source_pages.csv \
    --raw-dir outputs/pilot/raw --out-dir outputs/pilot/parsed
```

## Stage 3.5 — Gold-free structural quality checks

`pipeline/quality_checks.py`. Runs on **any** parsed output, gold or not —
this is the mechanism that scales past the 12 pages we have ground truth
for. Looks for internally-inconsistent patterns that correlate with known
VLM failure modes (see `docs/eval/known_issues.md`): a heading_path that
re-includes the institution name, a rank-class token stranded outside
`service_class`, credit totals that don't sum, duplicate `(date, theater,
session)` keys, a receipts_text that failed to parse, a whole multi-week
Repertoire page with zero dark cells (a strong signal the model dropped
blank cells this run), inconsistent theater-name spelling within one page.

Flags are triage signals, not verdicts — e.g. a genuinely duplicate person
(someone who really holds two listed roles) will trip the duplicate-entry
check without being wrong. The point is to route a full run's limited human
review budget at the highest-risk pages instead of a uniform random sample.

```
python pipeline/quality_checks.py --parsed-dir outputs/pilot/parsed \
    --out outputs/pilot/quality_flags.csv
```

## Stage 4 — Eval against gold

`pipeline/eval_against_gold.py`. Scores a parsed run against
`docs/eval/gold/`: roster rows compared positionally within a page (list
order has held reliably so far); Repertoire rows compared by
`(day_number, theater_prefix, session)` since row order there is *not*
stable run to run (the model sometimes emits date-by-date, sometimes
theater-by-theater — both are complete, valid answers, just not
comparable positionally). Append the summary line to
`docs/eval/run_history.csv` after each run so a prompt/schema change can be
judged by whether the number actually moved.

```
python pipeline/eval_against_gold.py --parsed-dir outputs/pilot/parsed \
    --gold-dir docs/eval/gold --out outputs/pilot/eval_report.txt \
    --run-id <date>_<model>_<short description>
```

Pilot result (12 pages, `qwen3-vl-plus`, 300dpi): roster 78.0%, repertoire
95.6%, grand total 82.4%. See `docs/eval/known_issues.md` for what's driving
the gap — mostly non-deterministic recall on dark cells and a handful of
prompt-fixable field-boundary confusions, not wholesale extraction failure.

## Stage 5 — Build the DuckDB file

`pipeline/build_duckdb.py`. Loads Stage 3's CSVs into a `raw` schema
(straight load, the reproducibility guarantee) and builds a small `analysis`
schema on top via SQL (currently: `role_normalized` from the last segment of
`heading_path`, `receipts_total_kopecks` computed from the rubles/kopecks
split) — always additive, never overwriting `raw`.

```
python pipeline/build_duckdb.py --parsed-dir outputs/pilot/parsed \
    --manifest docs/eval/gold/source_pages.csv --db outputs/pilot/imperial_theaters.duckdb
```

Output is a single portable file — copy it off wherever it was built, no
server needed to query it.

## Stage 6 — Interface (not yet built)

`app/streamlit_app.py` — a thin, read-only browsing/query layer over the
`.duckdb` file (per `research_questions.md`): pick an entity type, filter by
season/city, view results as a table, click through to the source page image
for verification, and a raw-SQL box for anything the filters don't cover.
Runs anywhere the `.duckdb` file and images live.

---

## Improving run to run

`docs/eval/known_issues.md` + `docs/eval/run_history.csv` together are the
mechanism for this: known_issues records *what's* wrong and why (bug vs.
inherent VLM variance vs. a gold-transcription problem vs. an unresolved
convention question), run_history records whether a given fix actually moved
the aggregate score. Before changing a prompt or schema field, check
known_issues for whether it's already tracked; after a run, update both
files rather than letting a finding live only in a chat transcript.

## Open questions

1. Multi-sample consensus for the dark-cell recall problem (issue #1 in
   known_issues.md) isn't implemented yet — worth prototyping once a second
   pilot round is warranted.
2. Where does the `.duckdb` file (and the image set) live long-term —
   departmental storage, shared drive, eventual public deposit? Determines
   whether Stage 6 ships as "download the file and run this script" or
   something hosted.
3. Full-corpus cost/throughput estimate should be built from the actual
   pilot per-page timing now that we have it, not the earlier guess — worth
   revisiting before committing to a full ~1,300-page run.
