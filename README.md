# Imperial Theater Yearbooks

Turning scanned volumes of the **Ежегодникъ Императорскихъ театровъ**
("Yearbook of the Imperial Theatres") into structured, queryable data —
who worked at the Imperial Theatres, what was performed, when, and for how
much — spanning 18 consecutive seasons, 1890/91 through 1907/08.

## What this is

The Ежегодникъ was an official annual publication of the Imperial Theatres
administration in late Tsarist Russia, covering the state-run opera, ballet,
and drama companies in St. Petersburg and Moscow. Each yearbook bundled
several distinct kinds of tables and lists — a day-by-day performance
calendar with box-office receipts, and personnel rosters for every part of
the operation, from dancers and musicians to administrators, decorators,
and stagehands. The volumes are scanned as PDFs (one PDF per season per
entity type), and the text is in **pre-1918 Russian orthography** — the
hard sign (ъ) at word endings, "yat" (ѣ), decimal-i (і), and "fita" (ѳ) are
all original spelling, not OCR noise, and this project preserves them
verbatim rather than modernizing them.

The goal is to transcribe every page faithfully into structured spreadsheets
(CSVs, and a queryable database), so the material becomes usable for
research — repertoire and programming history, institutional/organizational
history, and prosopography of the dancers, musicians, and administrative
staff of the Imperial Theatres. See `docs/research_questions.md` for the
fuller research framing.

## The materials

`pdfs/` holds the source scans, one folder per entity/table type:

| Folder | What it is |
|---|---|
| `RepertoireTables` | Day-by-day performance calendar: date, theater, work performed, genre, box-office receipts |
| `Spiski_Administration` | Theatre administration staff roster |
| `Spiski_BalletArtists` | Ballet company roster (St. Petersburg and Moscow companies, separate files) |
| `Spiski_Musicians` | Orchestra roster (SP and Moscow, separate files) |
| `Spiski_ProductionTeam` | Backstage/technical staff (decorators, machinists) |
| `Spiski_TheaterSchoolStaff` | Imperial Theater School faculty and staff |
| `Spiski_Graduates`, `Spiski_ProductionStats` | Not yet sourced — see `docs/overview.md` |

144 PDFs, 1,299 scanned pages as of the last inventory (`docs/overview.md`
has the full breakdown and per-season page counts — worth reading before
assuming page count scales evenly with season, it doesn't: the Repertoire
table format changes partway through the run and roughly quadruples in page
count, documented in `docs/structural_survey.md`).

## How it's modeled

Full field-by-field spec: **`docs/schema.md`**. The short version:

- **Two layers, one source of truth.** A `raw` layer holds exactly what was
  transcribed — one row per printed appearance, verbatim text, provenance
  linked back to the source page. A `analysis` layer sits on top of it,
  built entirely by SQL transforms (never hand-edited), for the
  normalization, controlled vocabulary, and eventual person-deduplication
  work that real research questions need. The raw layer is the
  reproducibility guarantee; the analysis layer is what most queries
  actually touch. See `docs/research_questions.md` for why this split
  matters and what it does/doesn't solve (e.g. it does not by itself
  resolve the same person appearing across multiple years' volumes — that's
  a deliberately separate, later task).
- **Long/tidy, not wide.** The Repertoire calendar is modeled as one row per
  (date, session, theater) rather than one column per theater, because the
  actual set of theaters printed side-by-side changes partway through the
  18-year run (a third Moscow venue gets added, and the whole table
  reformats). Personnel rosters use a single free-text `heading_path` field
  for the institution → department → role hierarchy rather than fixed
  department/position columns, because that hierarchy visibly deepens
  season over season and isn't the same shape twice.
- **Dates stay as printed.** Pre-1918 Russia used the Julian ("Old Style")
  calendar; dates are kept exactly as printed rather than converted to the
  Gregorian calendar, alongside a best-effort parsed value for sorting.
- Chosen conventions were revised at least once already based on real
  extraction results — e.g., person roster entries originally split
  "department" and "position" into separate columns, and that split was
  abandoned in favor of one verbatim `heading_path` field once testing
  showed the boundary between the two is a visual/typographic judgment call
  a model can't reliably reproduce from text alone.

## How the text gets extracted

Each page image is sent to a vision-language model (Qwen VL, via Alibaba's
DashScope API) with a system prompt tailored to that page's table family
(one prompt for the Repertoire calendar shape, one for the personnel-roster
shape), asking for a JSON object matching the target schema. The full
pipeline, in order:

1. **Render** — PDF pages → PNG images (300dpi; lower resolutions produced
   noticeably more character-level misreads in testing).
2. **Extract** — call the model on each page image, save the raw JSON
   response untouched.
3. **Parse & validate** — validate raw responses against the schema, flatten
   into the flat CSV tables, log anything that fails to parse rather than
   silently dropping it.
4. **Quality-check** — gold-free structural self-consistency checks (does a
   heading repeat where it shouldn't, do credit totals sum correctly, does a
   multi-week performance page suspiciously have zero dark/blank cells,
   etc.) that scale to pages with no hand-transcribed ground truth to
   compare against.
5. **Eval against gold** — score against a 12-page hand-transcribed ground
   truth set (`docs/eval/gold/`) covering all entity types and a range of
   seasons, chosen deliberately to include the structurally hardest cases
   found in the source, not just easy pages.
5. **Build** — load everything into a single portable DuckDB file (`raw` +
   `analysis` schemas).
6. **Browse** — (planned) a small read-only Streamlit/Gradio app over the
   DuckDB file.

Full stage-by-stage detail, script names, and CLI usage: `docs/pipeline.md`.

## Extraction quality and how it improves run to run

Vision-language extraction from a 100+ year old scanned table is not
one-shot-perfect, and several of the failure modes are inherent to how
these models work (sampling variance, occasional field-boundary confusion)
rather than one-time bugs to stamp out. Rather than chase a perfect single
run, the project tracks this explicitly:

- **`docs/eval/known_issues.md`** — a living ledger of what's gone wrong,
  why, whether it turned out to be a real model error vs. a
  gold-transcription inconsistency vs. an inherent recall/non-determinism
  issue, and what fixed it (or didn't — including at least one documented
  case where a prompt fix was tried, tested, and confirmed *not* to help,
  so the fix moved to deterministic post-processing instead).
- **`docs/eval/run_history.csv`** — the accuracy score and page count for
  every extraction run, so a prompt or schema change can be judged by
  whether it actually moved the number.

## Project status

- Schema, structural survey, and a 12-page hand-transcribed gold set: done.
- Pipeline (all 6 stages) built and validated on the 12-page gold set, then
  on a full 78-page entity type (Administration) with zero pipeline
  failures.
- A full-corpus extraction run (~1,300 pages, all entity types) is the
  current in-progress milestone.

## Repo layout

```
pdfs/               source PDF scans (see table above)
docs/
  introduction.md         non-technical, step-by-step walkthrough of the whole process
  schema.md              field-by-field data model
  structural_survey.md   how the printed table formats vary across the run
  overview.md             corpus inventory stats
  research_questions.md   what this data can answer, and modeling tradeoffs
  pipeline.md             pipeline stages, scripts, usage
  verbatim_deliverables.md   output-format comparison for the verbatim layer
  research_dataset.md       entity-resolution plan for the research layer
  entity_centric_model.md   plan for a Person/Performance/Work/Theater-centric v2 (not yet built)
  eval/
    gold/                 12-page hand-transcribed ground truth + builder scripts
    known_issues.md        extraction issue ledger
    run_history.csv        accuracy per run, over time
pipeline/
  schemas/            pydantic models mirroring docs/schema.md
  prompts/            per-table-family system prompts
  render_pages.py     stage 1
  extract.py          stage 2 (single-page CLI, for debugging/smoke tests)
  run_pilot.py        stage 2 (concurrent batch driver, retry + usage logging)
  parse_and_validate.py  stage 3
  quality_checks.py      stage 3.5 (gold-free structural checks)
  eval_against_gold.py   stage 4
  build_duckdb.py        stage 5
  build_excel_workbook.py   stage 5b -- verbatim layer as one .xlsx (docs/verbatim_deliverables.md)
  build_obsidian_vault.py   stage 5c -- verbatim layer as one-note-per-page Obsidian vault
  build_entities.py         stage 5d -- entity resolution (entities schema: theater/work/person, docs/research_dataset.md)
  build_datasette.py        stage 5e -- entities schema as a browsable Datasette SQLite site
outputs/            generated (gitignored) -- images, raw model output, parsed
                    CSVs, and the final .duckdb file, per run
.env                DASHSCOPE_API_KEY (gitignored)
```

## Running it

```
python pipeline/render_pages.py --pdf-dir pdfs --out-dir outputs/<run> --dpi 300
python pipeline/run_pilot.py --manifest outputs/<run>/manifest.csv \
    --images-dir outputs/<run>/images --out-dir outputs/<run>/raw --max-concurrent 8
python pipeline/parse_and_validate.py --manifest outputs/<run>/manifest.csv \
    --raw-dir outputs/<run>/raw --out-dir outputs/<run>/parsed
python pipeline/quality_checks.py --parsed-dir outputs/<run>/parsed --out outputs/<run>/quality_flags.csv
python pipeline/eval_against_gold.py --parsed-dir outputs/<run>/parsed \
    --gold-dir docs/eval/gold --out outputs/<run>/eval_report.txt --run-id <label>
python pipeline/build_duckdb.py --parsed-dir outputs/<run>/parsed \
    --manifest outputs/<run>/manifest.csv --db outputs/<run>/imperial_theaters.duckdb
```

Requires a `DASHSCOPE_API_KEY` in `.env`. See `docs/pipeline.md` for what
each stage actually does and why it's split up this way (mainly: so
re-parsing or re-scoring a run never requires paying for the API call
again).
