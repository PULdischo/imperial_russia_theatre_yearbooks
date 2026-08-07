# Verbatim deliverables — output format comparison

Scope: the **verbatim/`raw` layer only** — the data exactly as transcribed
from the scans (see `docs/research_questions.md` for why this layer exists
separately from the derived `analysis` layer). This doc maps out candidate
output *formats* for handing that layer to the researcher and compares them.
The equivalent comparison for the **research dataset** (the deduplicated
person/theater/work entity layer, built on top of this one) is a separate
follow-up doc — some formats considered here (especially OpenRefine) are
really about *getting to* that next layer, and are noted as such below.

Six tables feed every format below: `source_pages`, `person_entry`,
`person_entry_service`, `person_entry_credit`, `event_entry`,
`event_entry_performance` — field-by-field detail in `docs/schema.md`.

## The three axes

- **Accessibility** — can the researcher open this and start working with a
  tool they already use, with no new tool-learning curve?
- **Performance** — does it stay responsive at our actual scale (1,299
  pages; ~20-25k rows in each of the larger tables) for loading, filtering,
  browsing?
- **Utility** — what kind of work does the format actually support well:
  reading/annotating, pivoting/filtering, cleaning/reconciling, or
  scripting/reproducibility?

## Comparison at a glance

| Format | Accessibility | Performance | Utility | Status |
|---|---|---|---|---|
| DuckDB file | Low — needs a client (Python/R/DuckDB CLI/DBeaver) | Excellent — instant joins/filters at this scale | Best for reproducible cross-table analysis; poor for cleaning | **Built** (`build_duckdb.py`), pushed to a private HF dataset |
| CSV bundle (6 files) | High — every tool opens CSV | Good — largest table is ~32k rows, trivial for any tool | Per-table filtering; cross-table work is manual (VLOOKUP-style) | **Exists** (`parse_and_validate.py`) |
| Excel workbook (1 file, 6 sheets) | Highest for Sheets/Excel users | Good, same data as CSV bundle | Same as CSV, but one file instead of six | **Built** (`build_excel_workbook.py`) — 6MB, drag into Drive to get a native multi-tab Sheet |
| OpenRefine project | High — Refine opens CSV/Excel directly | Good up to tens of thousands of rows (in range here) | **Best for cleaning/reconciliation** — faceting, clustering, this is the on-ramp to the research dataset | No new format — reuses the CSV/Excel bundle |
| Obsidian vault (1 note/page) | High, if already an Obsidian user | Good for browsing; large due to embedded page images | Best for reading/annotating page-by-page, close to how the researcher already thinks about "a page in the yearbook" | **Built** (`build_obsidian_vault.py`) — 378MB (1,299 pages + downscaled images), down from 12.8GB at archival resolution |

## DuckDB file

Already the pipeline's Stage 5 output (`imperial_theaters.duckdb`). Single
portable file, `raw` schema mirrors these six tables exactly (plus an
`analysis` schema the researcher won't need for verbatim work).

- **Accessibility**: lowest of the group for a non-technical researcher —
  requires installing something (DuckDB CLI, `duckdb` Python/R package, or a
  GUI like DBeaver/Harlequin) before the first query. Fine for anyone
  comfortable with SQL or pandas; a barrier otherwise.
- **Performance**: this is not a "big data" problem — the whole file is a
  few hundred MB at most and every query is sub-second.
- **Utility**: the only format here that does real cross-table joins (e.g.
  "every roster entry with more than one service period") without manual
  work. Weakest at cleaning/normalization — no faceting or clustering UI.

## CSV bundle / Excel workbook

The CSVs are already a pipeline byproduct (`outputs/<run>/parsed/*.csv`) —
no new work to produce them. An Excel workbook is one packaging step on top
(one `.xlsx` with a sheet per table, via `openpyxl`/pandas), useful mainly so
the researcher deals with one file instead of six and each sheet arrives
pre-split rather than requiring six separate imports into Sheets.

- **Accessibility**: highest of any format for a Sheets/Excel-comfortable
  researcher — double-click and it opens, no import step for Excel; CSVs
  need one extra "import as UTF-8" step in Sheets (see the encoding note
  below).
- **Performance**: fine at this scale — the largest table
  (`person_entry_credit`, ~32k rows × 6 columns) is nowhere near either
  tool's row/cell limits.
- **Utility**: good for exactly what pivot tables and filters are for —
  slicing one table at a time (e.g. all `BalletArtists` entries in a given
  season, or summing receipts by theater/year in `event_entry`).
  Cross-table questions (e.g. "this person's credits AND their service
  periods") require the researcher to do their own lookup/join, since
  neither tool enforces or auto-follows the `entry_id`/`event_id` foreign
  keys the way SQL does.

**Encoding gotcha worth flagging now, since we hit this class of bug
repeatedly during extraction**: a bare UTF-8 CSV opened by *double-clicking*
in Excel (as opposed to using its "Data > From Text/CSV" import) often
guesses the wrong codepage and silently mangles the pre-reform Cyrillic
characters (ъ, ѣ, і, ѳ) into mojibake — it doesn't error, it just looks
wrong. Two fixes, either works: write the CSVs with a UTF-8 BOM (`utf-8-sig`)
so Excel's double-click path detects UTF-8 correctly, or ship the Excel
workbook instead of raw CSVs (an `.xlsx` has no encoding ambiguity at all).
Google Sheets' explicit CSV import dialog doesn't have this problem either
way. Given the researcher uses both Sheets and Excel-adjacent tools, the
Excel workbook is the safer default deliverable; if we still ship CSVs
(e.g. for OpenRefine), write them `utf-8-sig`.

## OpenRefine

Not a distinct file format — Refine imports the same CSV bundle or Excel
workbook directly, so this line item adds no new build work. It's included
because it's the one tool here actually built for the next task the
researcher described (cleaning verbatim text as groundwork for the research
dataset):

- **Faceting** surfaces every distinct `heading_path`, `theater`, `family_name`,
  etc. value at a glance — useful for spotting the OCR variant-spelling
  issues already tracked in `docs/eval/known_issues.md` (e.g. the
  Полицiймейстеры/Палиціймейстеры and Экзекуторъ/Эксекуторъ pairs).
- **Clustering** (key collision / nearest-neighbor methods) is exactly the
  mechanism needed to group spelling variants of the same theater or person
  name before they become separate rows in the research dataset's
  deduplicated entity tables.
- This is the natural bridge to the research-dataset doc: whatever
  clustering/normalization decisions get made in Refine on the verbatim
  data become the input to that layer's entity-resolution step. Worth
  keeping that OpenRefine project file (or at least its operation history,
  which Refine can export separately) alongside the research-dataset
  deliverable for provenance, rather than treating the cleaning pass as
  throwaway exploration.
- **Performance**: comfortable at our row counts; Refine's UI can get sluggish
  well above 100k rows, and our largest table is ~32k.

## Obsidian vault

**Built** (`pipeline/build_obsidian_vault.py`). **One note per source
page** (1,299 notes, one per `source_pages` row), because that's the
natural unit for "verbatim, exactly as it appears in the scans" — it
mirrors how the researcher already thinks about the material (a page in a
given year's yearbook), rather than one note per transcribed row (~44k
notes across `person_entry` + `event_entry`, which would turn the
vault into a flat data dump rather than something meant to be read).

Actual note shape (e.g. for `administration_1907-08_p000`):

```markdown
---
page_id: administration_1907-08_p000
entity_type: Administrators
season: 1907-08
city:
source_file: ForUpload_1907-08_Spisok_Administration.pdf
source_page_index: 0
printed_page_number:
---
![[administration_1907-08_p000.jpg]]

| # | Family name | First name | Patronymic | Heading | Rank/title | Class | Instrument | Subject | Tenure | Credits |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. | Вильеръ-де-Лиль-Адамъ | Александръ | Фердинандовичъ | Чиновники особыхъ порученій, ... | колл. сов. |  |  |  | (съ 19 сентября 1882 г.). ... |  |

[[administration_1907-08_p001|Next page ->]]
```

Repertoire pages get a sessions table instead (Date/Theater/Session/Status/
Works/Receipts/Annotation, works flattened to `Title (genre); Title2
(genre2)`); six entity-type index notes group pages by season, and a
`Home.md` links to those.

- **Accessibility**: high if the researcher is already in Obsidian daily —
  no new tool, and it supports exactly the workflow of reading a page,
  annotating it, and linking observations across pages/seasons.
- **Performance**: 1,299 notes is comfortably within what Obsidian handles
  well. The real constraint, as anticipated, was disk/sync size from the
  page images: the archival 300dpi PNGs average ~9.9MB each (12.8GB across
  the corpus), which would make the vault impractical to sync via Obsidian
  Sync or a cloud folder. Fixed by generating a separate, disposable
  *viewing* copy per page (long edge capped at 1600px, JPEG quality 82) for
  the vault, leaving the archival images untouched — this took the vault
  down to 378MB total (369.8MB images + 8.7MB notes), a ~34x reduction,
  with no loss of legibility at normal reading zoom.
- **Utility**: best of any format here for close reading, annotation, and
  building up qualitative/contextual notes page-by-page — genuinely
  different work from what Sheets/OpenRefine/DuckDB support. Not meant for
  aggregate analysis; a researcher who wants "total receipts by theater by
  year" should go to Sheets or DuckDB, not grep through vault notes.

## Recommendation

Ship more than one deliverable rather than picking a single winner — each
format earns its place because it matches a different piece of how this
researcher actually works, not because one is objectively best:

1. **Excel workbook** — built. Primary handoff for Sheets/pivot-table work
   — one file, no encoding surprises.
2. **The same CSV bundle** (already produced, write `utf-8-sig`) as the
   OpenRefine input, since that's where the cleaning/clustering pass toward
   the research dataset actually happens.
3. **DuckDB file** — built, pushed to a private HF dataset, kept as the
   reproducibility artifact and the option for any cross-table question the
   other two can't answer without manual joins.
4. **Obsidian vault** — built. Page-by-page reading/annotation experience
   alongside the tabular ones.

Building the Obsidian export and the Excel packaging step were both small,
mechanical additions to the existing pipeline (they read the same
`parsed/*.csv` output `build_duckdb.py` already consumes) — not a new
extraction or schema change.
