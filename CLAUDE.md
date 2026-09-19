# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A pipeline that turns 144 scanned volumes of the *Ежегодникъ Императорскихъ
театровъ* (1890/91–1907/08) into (1) a diplomatic verbatim transcription and
(2) a linked research dataset (resolved people/works/theaters/performances).
Pre-1918 Cyrillic orthography (ъ, ѣ, і, ѳ) is preserved verbatim throughout —
never modernize it. See `README.md` for the full narrative and the two
Mermaid ER diagrams; `docs/pipeline.md` and `docs/schema.md` for stage-by-
stage and field-by-field detail. This file is the operational summary.

**This is a research dataset — any answer about what the data contains must
be grounded in an actual query, not memory or a prior turn's cached number,
and every such query gets logged to `docs/query_log.md`.** Full protocol:
`.claude/skills/imperial-theater-db/SKILL.md`.

## Setup

Dependencies live in `pyproject.toml`, pinned to exact versions in
`uv.lock`. One command, on any machine:

```
uv sync
```

That provisions the right Python (3.13, per `.python-version` — uv
downloads it if missing; don't rely on a system Python) and installs the
locked versions. Run pipeline scripts through it:

```
uv run python pipeline/<script>.py ...
```

`uv run` uses the project venv whether or not you've activated it; plain
`python` will not unless you `source .venv/bin/activate` first. Add the
optional Anthropic SDK — only `run_reviews.py --provider anthropic` needs
it — with `uv sync --extra anthropic`.

The code's actual floor is Python 3.10 (the pydantic models evaluate PEP
604 `X | None` annotations at runtime); 3.13 is what the lockfile is
resolved and validated against.

**On the historical `opencv-python-headless==4.10.0.84` pin (dropped
2026-09-07):** opencv is now unpinned and the project runs 5.x. The pin
existed for one reason — recent releases (4.11+, 5.x) ship wheels for
macOS 13.0+ only, and on the previous dev machine (macOS 12.7.6) an
unpinned install silently fell back to compiling from source, needing
`cmake` and hanging or failing for many minutes. `4.10.0.84` was the last
release with a macOS-12-compatible wheel. That constraint was always about
the OS version, never the Python version. It no longer applies on macOS
13+, and 5.0.0.93 was verified equivalent before dropping the pin: every
cv2-dependent intermediate in `row_detect.py` (decode, `_binarize`,
`_table_x_bounds`, `_row_darkness_profile`, `_detect_line_curves`,
`_detect_vertical_dividers`) hashed byte-identical under 4.10.0.84 and
5.0.0.93 across all four gold Repertoire pages. Caveat: those pages are
raw renders, so detection bails before the dewarp/crop path — that half is
unverified across versions, worth a look on the first real ScanTailor
batch. If you ever set up on macOS 12 again, restore the pin.

Requires `.env` with `DASHSCOPE_API_KEY` (Alibaba DashScope, OpenAI-compatible
endpoint, model `qwen3-vl-plus`). No GPU needed — runs on a laptop.

## The pipeline (dev loop)

Each stage writes files the next stage reads; nothing is re-derived silently.
Run against a scratch dir first (e.g. `outputs/pilot`), not `outputs/full_run`
(the production artifacts already published to HF/Cloud Run).

```
python pipeline/render_pages.py --pdf-dir pdf --out-dir outputs/<run> --dpi 300
#   NB: --pdf-dir must be given explicitly. The script's own default is
#   `pdfs` (no such directory here -- the scans live in `pdf/`), and
#   discover_pdfs() silently yields nothing for a missing/empty dir
#   rather than erroring, so the wrong path looks like a clean no-op run.
python pipeline/run_pilot.py --manifest outputs/<run>/manifest.csv \
    --images-dir outputs/<run>/images --out-dir outputs/<run>/raw --max-concurrent 8
python pipeline/parse_and_validate.py --manifest outputs/<run>/manifest.csv \
    --raw-dir outputs/<run>/raw --out-dir outputs/<run>/parsed
python pipeline/quality_checks.py --parsed-dir outputs/<run>/parsed --out outputs/<run>/quality_flags.csv
```

**Repertoire pages specifically get two additional passes, routinely, on
every page — not gated behind a screening heuristic (RG, 2026-09-01:
cost isn't the constraint here, accuracy is).** `run_pilot.py`'s default
single-call-per-page path is prone to real, confirmed cross-date
content bleed from row-boundary misdetection (`docs/eval/known_issues.md`
#1/#68); row-level and column-wise extraction fail in different ways
from each other and from the baseline, so running all three and cross-
checking is the actual mitigation, not any one method alone:

```
python pipeline/run_pilot.py --manifest outputs/<run>/manifest.csv \
    --images-dir outputs/<run>/images --out-dir outputs/<run>/raw_rowlevel \
    --row-level --max-concurrent 8
python pipeline/run_pilot.py --manifest outputs/<run>/manifest.csv \
    --images-dir outputs/<run>/images --out-dir outputs/<run>/raw_columnwise \
    --column-level --max-concurrent 8
python pipeline/quality_checks.py --parsed-dir outputs/<run>/parsed \
    --out outputs/<run>/quality_flags.csv \
    --page-raw-dir outputs/<run>/raw --row-raw-dir outputs/<run>/raw_rowlevel \
    --column-raw-dir outputs/<run>/raw_columnwise
```

Then the normal sequence continues as above (`eval_against_gold.py`,
`build_duckdb.py`) — the two extra passes and the cross-check are an
addition to the standard flow, not a fork of it.

**This literal recipe is for the single-page-format seasons (1898-99
onward, 81% of Repertoire pages) only.** For the two-page-spread
seasons (1890-91–1897-98, `outputs/repertoire_spreadfix_v6`), don't
run it as shown above — both extra passes were tried against this
format specifically and neither works the way this section implies:

- **`--column-level` against the whole, unsplit spread image measured
  14–63% receipts agreement with the baseline** (`docs/eval/
  known_issues.md`, 2026-09-08 addendum) — explicitly rejected, not a
  viable cross-check for this format as-is.
- **`--row-level --cropped-images` hits a real, still-open bug**: the
  header-band reattachment it depends on doesn't work reliably on
  cropped/split images. The project's own conclusion, unchanged since
  2026-09-08: *"`--cropped-images` should not be used for production
  row-level runs."* Running it will rediscover this, not produce a
  usable second opinion.

**What was actually done instead**, and is already complete: physically
split each spread page into top/bottom halves (`pipeline/
split_spread_pages.py`), run `--column-level` on each half (this makes
each half resemble the single-page format the method already works
well on), deduplicate the deliberate overlap between halves
(`dedup_split_overlap.py`), then hand-verify against the scans — this
last step is the bulk of `docs/eval/known_issues.md` issue #70 and most
of this project's session history. `outputs/repertoire_spreadfix_v6/
raw_columnwise/*.raw.json` is the result, and it — not a fresh
full-page call — is what `parse_and_validate.py` actually reads for
these seasons. Don't propose or run a "row-level/column-wise
cross-check" for spread-season pages as if it were a gap; the
equivalent quality-assurance work already happened, just structured
around this format's real constraints instead of the generic recipe
above.

```
python pipeline/eval_against_gold.py --parsed-dir outputs/<run>/parsed \
    --gold-dir docs/eval/gold --out outputs/<run>/eval_report.txt --run-id <label>
python pipeline/build_duckdb.py --parsed-dir outputs/<run>/parsed \
    --manifest outputs/<run>/manifest.csv --db outputs/<run>/imperial_theaters.duckdb
```

Then the entity-resolution / research-layer stages, run in order against the
same `.duckdb` file (each is additive, safe to re-run):

```
python pipeline/build_entities.py --db outputs/<run>/imperial_theaters.duckdb
python pipeline/validate_performance_dates.py --db outputs/<run>/imperial_theaters.duckdb
python pipeline/link_wikidata.py --db outputs/<run>/imperial_theaters.duckdb --pilot \
    --export-review-queue outputs/<run>/wikidata_review_queue.csv
python pipeline/build_research_model.py --db outputs/<run>/imperial_theaters.duckdb
python pipeline/build_datasette.py --db outputs/<run>/imperial_theaters.duckdb \
    --out outputs/<run>/research_dataset.sqlite
```

Optional parallel exports of the verbatim layer (`docs/verbatim_deliverables.md`):

```
python pipeline/build_excel_workbook.py --parsed-dir outputs/<run>/parsed \
    --manifest outputs/<run>/manifest.csv --out outputs/<run>/imperial_theaters.xlsx
python pipeline/build_obsidian_vault.py --parsed-dir outputs/<run>/parsed \
    --manifest outputs/<run>/manifest.csv --images-dir outputs/<run>/images \
    --out-dir outputs/<run>/obsidian_vault
```

`pipeline/extract.py` runs a single page through the model (`--image`,
`--kind roster|repertoire`, `--page-id`) — for iterating on a prompt without
paying for a full batch run.

## "Tests" — there's no unit test suite; correctness is measured two ways

- **`pipeline/eval_against_gold.py`** scores a parsed run against the 12-page
  hand-transcribed ground truth in `docs/eval/gold/`. This is the closest
  thing to a regression test — after any change to a prompt, a pydantic
  schema, or the flatten logic, re-run it and compare against
  `docs/eval/run_history.csv`; append the new summary line there rather than
  letting a result live only in a chat transcript.
- **`pipeline/quality_checks.py`** runs gold-free structural self-consistency
  checks (credit sums, duplicate keys, suspiciously-zero dark-cell pages,
  etc.) on any parsed output — this is what scales past the 12 gold pages.
- Findings from both go in `docs/eval/known_issues.md`, triaged by cause
  (genuine model error vs. inherent VLM non-determinism vs. gold-set
  inconsistency vs. open convention question) — check it before re-diagnosing
  something already tracked.
- The gold CSVs are generated by `docs/eval/gold/_build_roster.py` and
  `_build_repertoire.py` (hand-transcribed Python data structures, run
  directly with no args — they write into their own directory). Edit the data
  structures in those scripts, not the CSVs, and re-run them to regenerate.

## Architecture: four schemas in one DuckDB file, each built from the last

`raw` → `analysis` → `entities` → `research`, each schema built by a
different pipeline script, each strictly additive (never rewrites the layer
below it):

- **`raw`** (`build_duckdb.py`) — one row per printed appearance, verbatim,
  page-centric. The reproducibility guarantee; never hand-edited. Tables:
  `source_pages`, `person_entry`, `person_entry_service`,
  `person_entry_credit`, `event_entry`, `event_entry_performance`.
- **`analysis`** (`build_duckdb.py`, `validate_performance_dates.py`) —
  derived columns/rows on top of `raw` via SQL only (e.g. `role_normalized`,
  `theater_canonical`, the `not_captured` completeness-gap synthesis, the
  day-of-week-validated `corrected_date_undate`). No new facts, no
  hand-editing.
- **`entities`** (`build_entities.py`, `link_wikidata.py`) — the working
  record-linkage layer: crosswalks (`person_link`, `work_link`), review
  queues (`person_candidate`, `work_genre_candidate`), and an append-only
  merge log. This is pipeline-internal audit state, **not published**.
- **`research`** (`build_research_model.py`) — the final, simplified,
  directly-queryable layer with real FKs baked in (no crosswalk joins at
  query time): `theater`, `work`, `person`, `event`, `performance`,
  `person_appearance`. This is what gets exported to `research_dataset.sqlite`
  (`build_datasette.py`) and is the layer published to HF / served on Cloud
  Run.

**Non-obvious things that took real effort to establish — don't rediscover
these the hard way:**

- The LLM-facing raw JSON (`outputs/<run>/raw/*.raw.json`) and the Pydantic
  models in `pipeline/schemas/` intentionally keep an *older* shape than the
  flattened tables — e.g. the model is still asked for `is_dark`
  (bool)/`session` (`"day"`/`"morning"`/`"evening"`)/`end_type="resigned"`,
  which only becomes `event_status`/`time_of_day`
  (`"unspecified"`/…)/`"left service"` at the flatten boundary
  (`flatten_roster_page`/`flatten_repertoire_page` in `pipeline/schemas/`).
  This is deliberate — it means schema/naming changes never require
  re-running the (paid, non-deterministic) extraction step, only re-running
  `parse_and_validate.py` against JSON already on disk. When renaming a
  field, change the flatten output, not the LLM-facing contract, unless the
  model genuinely needs to capture something new.
- DuckDB has no `ALTER TABLE ADD FOREIGN KEY`, and rejects `UPDATE` on any
  table whose primary key has an incoming FK (self-referential or not). This
  is why `entities.work.excerpt_of_work_id` and
  `entities.person.superseded_by_person_id` are plain columns with no
  `REFERENCES` clause, and why schema-building scripts use `CREATE TABLE`
  (inline constraints) + `INSERT INTO ... SELECT` rather than
  `CREATE TABLE AS SELECT` + `ALTER`.
- `raw.event_entry_performance.performance_id`, `entities.work.work_id`, and
  `entities.work_link.raw_performance_id` are three different IDs for
  related-but-distinct things — don't assume any two are interchangeable.
- `research.event` and `research.performance` are kept as separate tables on
  purpose: ~35% of events list more than one work, and receipts are printed
  once per event, not once per work. `research.performance` deliberately has
  no receipts column at all, specifically so summing it can never
  double-count; only sum `receipts_total_kopecks` on `research.event`.
- `outputs/` is gitignored and treated as disposable *except* the raw
  `*.raw.json` responses (re-parsing them is free) and the final `.duckdb`
  file (the actual deliverable) are worth keeping — everything else
  regenerates from those plus the pipeline scripts.

## Publishing: HF dataset repo + Cloud Run (`spiski`)

`research_dataset.sqlite` (`build_datasette.py`'s output) is what gets
served — a Datasette instance with `datasette-auth-passwords` (basic auth),
`datasette-llm` + `datasette-agent` (chat/explore assistant, model
`qwen-plus` via DashScope's OpenAI-compatible endpoint), and
`datasette-secrets` installed. Both publish targets are configured with
files under `outputs/full_run/` — which is gitignored, so **none of this
config persists in git**; if it's missing, recreate it from what's below
before publishing.

**HF dataset repo** (`apjanco/imperial-russian-theater-yearbooks`, private):
push `imperial_theaters.duckdb` + `docs/` + `README.md` via
`huggingface_hub.HfApi().upload_file(...)`. The `xet` upload backend is
unreliable in this environment (`ConnectError`/`RuntimeError: client has been
closed`, reproducibile even with retries) — set `HF_HUB_DISABLE_XET=1` before
calling it; that consistently works when plain `xet` doesn't.

**Cloud Run** (`spiski`, project `prozhito-234812`, region `us-east1`) is
built via `datasette publish cloudrun`, which has **no `--config` flag** —
only `--metadata`. In this installed Datasette version (1.0a37), `--metadata`
no longer feeds `datasette.allowed()` permission checks (confirmed by direct
testing) — a `permissions` block placed there is silently ignored, so
`datasette-agent`'s UI links never render even though the plugin loads fine.
Split the permissions out into their own file and inject it with a real
`--config` flag via `--extra-options` (the one publish-time hook that lets
you append arbitrary flags to the generated `datasette serve` command):

`outputs/full_run/llm_plugins/datasette_permissions.json` (create if missing):
```json
{
  "permissions": {
    "datasette-agent": true,
    "datasette-agent-explore": true,
    "datasette-agent-background": true,
    "execute-sql": true
  }
}
```

`outputs/full_run/datasette_metadata_cloudrun.json` keeps `title`,
`description`, `databases.research_dataset.tables.*` (per-table
descriptions/facets/sort), and `plugins` (`datasette-auth-passwords`'s
password hash, `datasette-llm`'s `default_model`) — **no `permissions` key**,
that plugin config genuinely does still work via `--metadata`, only
`permissions` doesn't.

Before publishing, write the DashScope key into the plugins dir (never typed
literally — always via `.env` indirection) so `llm`'s
`extra-openai-models.yaml` (`api_key_name: dashscope`) can resolve it:
```
python -c "
import os, json
from dotenv import load_dotenv
load_dotenv()
json.dump({'dashscope': os.environ['DASHSCOPE_API_KEY']},
          open('outputs/full_run/llm_plugins/keys.json', 'w'))
"
```

Then, **on Windows, in Git Bash specifically**: MSYS silently rewrites any
command-line argument that looks like a Unix absolute path (anything
starting with `/`) into a Windows path before the program ever sees it — so
`--plugin-secret llm user-path /app/plugins` was actually shipping
`LLM_USER_PATH=C:/Program Files/Git/app/plugins` inside the container
(confirmed by pulling the built image via a throwaway Cloud Build step and
inspecting `env`/`llm models list` directly — `Unknown model: qwen-plus` at
runtime was the visible symptom). Prefix the whole publish command with
`MSYS_NO_PATHCONV=1` to stop that:

```
MSYS_NO_PATHCONV=1 python -m datasette publish cloudrun \
  --service spiski \
  --metadata outputs/full_run/datasette_metadata_cloudrun.json \
  --plugins-dir outputs/full_run/llm_plugins \
  --install datasette-auth-passwords \
  --install datasette-llm \
  --install datasette-agent \
  --install datasette-secrets \
  --plugin-secret llm user-path /app/plugins \
  --extra-options "--config plugins/datasette_permissions.json" \
  outputs/full_run/research_dataset.sqlite
```

This build+push **always** crashes on Windows at the very end with a
`PermissionError` during `tempfile`'s cleanup (`datasette/utils.py`'s
`temporary_docker_directory`, a `with` block whose `finally: tmp.cleanup()`
runs after the image is already built and pushed — confirmed by reading that
source directly). That crash is harmless noise, not a failed build; check
`gcloud builds list --limit=1` to confirm `SUCCESS`, then finish the deploy
manually (the crash means `publish cloudrun`'s own trailing `gcloud run
deploy` call never runs):

```
gcloud run deploy spiski \
  --image us-docker.pkg.dev/prozhito-234812/datasette/datasette-spiski:latest \
  --platform=managed --region us-east1 --allow-unauthenticated \
  --project prozhito-234812
```

Delete `outputs/full_run/llm_plugins/keys.json` again once deployed — it's
never meant to persist on disk between publishes.
