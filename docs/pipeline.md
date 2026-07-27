# Processing pipeline sketch: PDFs → DuckDB (Adroit + Qwen VL)

This is a design sketch, not working code — the goal is to agree on stages,
I/O contracts, and repo layout before implementing against real Adroit
access. Code blocks below are illustrative.

**Assumptions to confirm with Princeton Research Computing before committing
to specifics** (I don't have current, reliable numbers for these and don't
want to assert stale ones): Adroit's GPU partition name(s), GPU model/memory
per node, per-user/per-group allocation limits, current scratch storage path
convention and purge policy, and which containerization/module approach RC
recommends for serving a vision-language model. Confirm via
https://researchcomputing.princeton.edu/systems/adroit and RC support before
the sbatch template below is treated as more than a placeholder.

---

## Repo layout

```
imperial_theater_yearbooks/
  pdfs/                     # source PDFs (as now, tracked or synced separately)
  docs/                     # schema.md, structural_survey.md, overview.md,
                            # research_questions.md, this file, eval/
  pipeline/
    schemas/                # pydantic models mirroring docs/schema.md exactly
    prompts/                # one prompt template per entity_type
    01_render_pages.py
    02_extract.py
    03_parse_and_validate.py
    04_eval_against_gold.py
    05_build_duckdb.py
    slurm/
      extract.sbatch
  outputs/                  # generated; not the dataset of record until step 5
    images/                 # {page_id}.png, mirrors pdfs/ tree
    manifest.csv            # source_pages.csv for the whole corpus
    raw/{run_id}/{page_id}.json      # untouched model output, one per page
    parsed/{table}.parquet           # validated, schema-conformant rows
    validation_errors.csv
  imperial_theaters.duckdb  # final deliverable, built by stage 5
  app/
    streamlit_app.py
```

`outputs/` and `imperial_theaters.duckdb` should live on scratch during
processing but get copied to durable storage (departmental space, OneDrive,
wherever the group keeps things that must survive a scratch purge) as soon
as a stage completes — HPC scratch filesystems are typically **not backed up
and subject to periodic purge**. Treat scratch as ephemeral working space,
never as the archive.

---

## Stage 0 — Stage the PDFs and environment

- Move `pdfs/` to Adroit scratch (Globus for the bulk transfer, or `rsync`/
  `scp` for incremental updates) — this is a one-time-ish step, repeated only
  when new PDFs (Graduates/ProductionStats, once sourced) show up.
- Set up the Python environment once, on a login node: `pymupdf`, `duckdb`,
  `pydantic`, plus whichever serving stack we pick for Qwen VL (`vllm` is the
  usual choice for throughput on a shared GPU; `transformers` directly is
  the fallback if vLLM support for the chosen Qwen VL checkpoint lags).
- Pull the Qwen VL checkpoint once into a shared cache directory
  (`HF_HOME` on scratch or wherever RC recommends for model caches) rather
  than re-downloading per job.
- **Model size vs. GPU memory is the open decision** — pick a checkpoint
  size (7B/32B/etc., possibly quantized) that actually fits what Adroit's
  GPU partition offers. Don't assume a large checkpoint fits a
  teaching-oriented cluster's GPUs; confirm memory before picking a size, and
  budget time for a quantization step if the first choice doesn't fit.

## Stage 1 — Render pages to images (CPU, cheap)

`pipeline/01_render_pages.py` — reuses the `pymupdf` pixmap approach from the
original notebook and this session's inventory script. Input: `pdfs/`.
Output: `outputs/images/{page_id}.png` + `outputs/manifest.csv` (the
corpus-wide equivalent of the `source_pages.csv` we built for the gold set —
same columns: `page_id`, `entity_type`, `season`, `city`, `source_file`,
`source_page_index`, `printed_page_number`).

No GPU needed. Runs once; re-run only for newly added PDFs (idempotent —
skip a page if its image already exists, exactly like the original notebook
did).

```python
# illustrative, not final
for pdf_path in discover_pdfs(PDFS_DIR):
    entity_type, season, city = parse_folder_and_filename(pdf_path)
    doc = pymupdf.open(pdf_path)
    for i, page in enumerate(doc):
        page_id = make_page_id(entity_type, season, city, i)
        out_path = IMAGES_DIR / f"{page_id}.png"
        if not out_path.exists():
            page.get_pixmap(dpi=200).save(out_path)
        manifest_rows.append({...})
```

## Stage 2 — Extraction (GPU, Qwen VL)

`pipeline/02_extract.py`, run as a Slurm job (array job over manifest
shards, or one long job iterating the manifest — depends on Adroit's queue
behavior for shared GPUs, confirm with RC). Serves the Qwen VL checkpoint
locally and prompts once per page with:

- a system prompt fixed per `entity_type` (five variants, one per Spiski
  type, plus the Repertoire prompt) instructing the schema-conformant JSON
  shape from `docs/schema.md`
- the page image
- a request for structured JSON output matching the relevant table(s)
  (`roster_entry`/`service_period`/`roster_entry_credit` or
  `performance_session`/`performance_work`)

Output: `outputs/raw/{run_id}/{page_id}.json` — the **untouched** model
response, one file per page, never overwritten. `run_id` (date + model
version + prompt version) makes it possible to re-run with a new model or
prompt without destroying the previous run's output, and to compare runs
later.

```python
# illustrative
for page_id, image_path, entity_type in manifest_rows:
    prompt = load_prompt(entity_type)
    response = model.generate(image=image_path, prompt=prompt)
    (RAW_DIR / run_id / f"{page_id}.json").write_text(response)
```

This is the stage where the RepertoireTables page-count skew in
`overview.md` matters for planning: late-season Repertoire pages are ~4x the
early seasons' page count for the same span, so throughput estimates should
be built from a realistic page-type mix, not just total page count ÷
pages-per-hour.

## Stage 3 — Parse and validate

`pipeline/03_parse_and_validate.py`. Parses each raw JSON response into
pydantic models that mirror `docs/schema.md`'s tables field-for-field.
Validates: required fields present, dates parseable (verbatim string always
kept; attempt an Undate parse, don't fail the row if that parse doesn't
resolve — flag it instead), numeric fields actually numeric, foreign keys
resolve within the page. Rows that fail validation go to
`outputs/validation_errors.csv` with the reason, for human review — never
silently dropped.

Output: `outputs/parsed/{table}.parquet`, one file per schema table, still
keyed by `page_id`/`entry_id`/`session_id` etc. exactly as in `schema.md`.
This is the raw/verbatim layer, ready to load.

## Stage 4 — Eval gate

`pipeline/04_eval_against_gold.py`. Runs stages 2–3 over the 12
`docs/eval/gold` pages specifically (or a rotating held-out sample once the
gold set grows) and diffs the result against `docs/eval/gold/*.csv` using the
methodology in `docs/eval/README.md` (exact-match on names/dates, numeric
match on receipts, structural checks like session-splitting on multi-receipt
cells, recall on child rows). **Gate, don't just report**: don't promote a
new model/prompt version to a full-corpus run until it clears an agreed
threshold. Re-run this any time the prompt, model checkpoint, or rendering
DPI changes.

## Stage 5 — Build the DuckDB file

`pipeline/05_build_duckdb.py`. Loads `outputs/parsed/*.parquet` into a `raw`
schema inside `imperial_theaters.duckdb` (straight load, no transformation —
this is the reproducibility guarantee). Then builds an `analysis` schema on
top via versioned SQL (or dbt, if the group already uses it) applying the
normalization/controlled-vocabulary and entity-resolution work described in
`research_questions.md` — this is where `*_normalized` columns and any
`person_id` crosswalk get created, always as new columns/tables alongside
the raw ones, never overwriting them.

```sql
-- illustrative
CREATE SCHEMA raw;
CREATE TABLE raw.roster_entry AS SELECT * FROM 'outputs/parsed/roster_entry.parquet';
-- ... one per table

CREATE SCHEMA analysis;
CREATE TABLE analysis.roster_entry AS
SELECT *,
       normalize_department(department) AS department_normalized,
       normalize_position(position)     AS position_normalized
FROM raw.roster_entry;
```

Output: `imperial_theaters.duckdb` — copy this off scratch immediately, it's
the deliverable.

## Stage 6 — Interface

`app/streamlit_app.py` — a thin, read-only browsing/query layer over the
`.duckdb` file (per `research_questions.md`): pick an entity type, filter by
season/city/department, view results as a table, click through to the
source page image (from `outputs/images/`, which should ship alongside the
`.duckdb` file or get archived together) for verification, and a raw-SQL box
for anything the filters don't cover. Runs anywhere the `.duckdb` file and
images live — doesn't need Adroit or any ongoing pipeline access.

---

## Open questions to settle before implementation

1. Confirm Adroit GPU partition specifics (memory, queue limits) → picks the
   Qwen VL checkpoint size and whether quantization is needed.
2. vLLM vs. plain `transformers` for serving — depends on what's easiest to
   get running under Adroit's module/container setup; ask RC what's already
   proven to work there for VLM inference.
3. Where does the `.duckdb` file (and the image set) live long-term once
   built — departmental storage, shared drive, eventual public deposit? This
   determines whether Stage 6's app is distributed as "download the file and
   run this script" or hosted somewhere persistent.
4. Batch size / job splitting strategy for Stage 2, once real per-page
   inference time is measured on Adroit hardware — the RepertoireTables
   season-length skew in `overview.md` means a naive even split across array
   tasks will load-imbalance badly.
