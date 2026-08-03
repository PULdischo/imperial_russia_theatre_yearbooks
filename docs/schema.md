# Entity/field schema (draft v1)

Informed by `structural_survey.md`. Two entity families, six tables. Designed so
that structural drift found in the survey (growing role hierarchies, changing
theater rosters, multi-period tenures) is *data*, not schema — we don't want a
model that needs a migration every time the printed source adds a role.

Transcription unit for the Spiski tables is **one row per printed appearance in
one volume** (a "person entry"), not a deduplicated master person record.
Linking the same person across years/volumes is a separate, later task (name +
patronymic + overlapping dates) — attempting it during transcription would mean
guessing at identity while we're still trying to get the printed page faithfully
captured.

Dates: store the printed string verbatim always (`*_date_text`), plus a parsed
[Undate](https://github.com/dh-tech/undate-python) value (`*_date_undate`) using
its partial/uncertain-precision model where the print is genuinely ambiguous.
No Gregorian conversion — the source is Old Style (Julian) throughout, and we
decided to keep it as printed.

---

## Shared: `source_pages.csv`

One row per digitized page. Every other table's `page_id` joins here.

| column | type | notes |
|---|---|---|
| `page_id` | string (PK) | synthetic, e.g. `RepertoireTables_1898-99_p019` |
| `entity_type` | enum | `Repertoire`, `Administrator`, `BalletArtist`, `Musician`, `ProductionTeam`, `TheaterSchoolStaff`, `Graduate`, `ProductionStats` |
| `season` | string | academic year as printed in the filename, e.g. `1898-99` |
| `city` | enum, nullable | `SP` \| `Moscow` — only meaningful for BalletArtists/Musicians, which are split at the file level |
| `source_file` | string | original PDF filename |
| `source_page_index` | int | 0-based page index within the PDF |
| `printed_page_number` | string, nullable | the page number printed on the physical page (verbatim — some are stylized like `— 115 —`) |

---

## Spiski family (Administrators, BalletArtists, Musicians, ProductionStaff,
## TheaterSchoolStaff, Graduates once sourced)

### `person_entry.csv`

One row per person per printed appearance.

| column | type | notes |
|---|---|---|
| `entry_id` | string (PK) | |
| `page_id` | FK → source_pages | |
| `entity_type` | enum | same set as above, restricted to the Spiski types |
| `institution` | string | top-level heading, verbatim, e.g. `Императорское С.-Петербургское Театральное Училище` |
| `heading_path` | string, nullable | every heading between the institution and this person's own entry, verbatim, top-to-bottom, joined with ` / ` (e.g. `Хозяйственное отдѣленіе / Полицiймейстеры / Маріинскій театръ`). Nesting depth is not fixed across types or years (survey found up to 4 levels). **Originally split into separate `department`/`position` columns; collapsed after the first extraction smoke test showed the boundary between "standing department heading" and "this person's specific role" is a visual/typographic judgment call (indentation, bold weight) that a model can't reliably reproduce from text alone.** If a clean single "role" value is needed for analysis, derive it downstream (e.g. last segment of `heading_path`) in the analysis layer rather than forcing the split at capture time. |
| `list_number` | string, nullable | the printed enumeration (`1.`, `52.`) — many entries are unnumbered (e.g. named officers before a numbered artist list) |
| `family_name` | string | verbatim, including printed ordinal suffixes (`Алексѣева 1-я`) |
| `first_name` | string, nullable | verbatim — some foreign-staff entries print family name only |
| `patronymic` | string, nullable | verbatim |
| `rank_or_title` | string, nullable | civil rank (`колл. сов.`) or honorific (`Солистъ Его Императорскаго Величества`), verbatim |
| `service_class` | string, nullable | Table-of-Ranks class where printed (`VII кл.`) — survey found this starts appearing by 1907, absent in 1890-91 |
| `instrument` | string, nullable | Musicians only |
| `subject_taught` | string, nullable | TheaterSchoolStaff only |
| `tenure_note_text` | string, nullable | the full parenthetical/trailing tenure note, verbatim, uncleaned — the source of truth `person_entry_service` rows are parsed from |
| `credit_summary_text` | string, nullable | the full performance-tally text for BalletArtists (e.g. `Въ 11 балетахъ—33; въ 8 операхъ—43. Всего—76 разъ`), verbatim — source of truth for `person_entry_credit` rows |

### `person_entry_service.csv`

Child of `person_entry`. Exists because tenure notes can describe **more than
one period** for the same person (survey found e.g. "съ 14 іюня 1879 г. по 1
іюля 1899 г. и съ 1 декабря ... г." — left and rejoined) — a single start/end
pair on the parent row can't represent that faithfully.

| column | type | notes |
|---|---|---|
| `period_id` | string (PK) | |
| `entry_id` | FK → roster_entry | |
| `period_order` | int | 1-based, order as printed |
| `start_date_text` | string, nullable | verbatim, e.g. `съ 1 мая 1882 г.` |
| `start_date_undate` | string, nullable | Undate-serialized |
| `end_date_text` | string, nullable | verbatim; null = still active as of this volume |
| `end_date_undate` | string, nullable | Undate-serialized |
| `end_type` | enum, nullable | `died` (†) \| `left service` (`Оставилъ службу`) \| `other` \| null (still active) |

### `person_entry_credit.csv`

Child of `person_entry`. BalletArtists performance tallies — both the
category totals and the optional named-role breakdown ("Въ томъ числѣ:
Спящая красавица (красавица)—5") are unbounded in count, so both go here
rather than as wide columns.

| column | type | notes |
|---|---|---|
| `credit_id` | string (PK) | |
| `entry_id` | FK → roster_entry | |
| `credit_type` | enum | `category_totals` \| `named_work` |
| `label` | string | for `category_totals`: `балетахъ`/`операхъ`/`драмѣ`/`Всего`; for `named_work`: the work title |
| `role_name` | string, nullable | only for `named_work` — the character name in parens |
| `category_production_count` | number | only for `category_totals`: `балетахъ`/`операхъ`/`драмѣ`; e.g. 'Въ 10 балетахъ'|
| `category_credit_count` | number | usually an integer, but the printed ledger occasionally uses a fractional value (e.g. `.5`) for a role split between two artists — kept as printed, not rounded |

---

## Repertoire family

Long/tidy by design — per the survey, the theater roster itself changed twice
in this 18-year run (5 combined columns → 3+2/3 separate blocks, with a third
Moscow venue added), so theater cannot be a fixed column set.

### `event_entry.csv`

One row per (date, session, theater) box-office record — this is the grain
receipts are actually printed at, even when multiple works share the bill.

| column | type | notes |
|---|---|---|
| `event_id` | string (PK) | |
| `page_id` | FK → source_pages | |
| `season` | string | |
| `city` | enum | `SP` \| `Moscow` |
| `date_text` | string | verbatim day+weekday, e.g. `31 Четвергъ` |
| `month_text` | string | verbatim month header this row falls under |
| `year_text` | string | verbatim year(s) as printed at the top of the block, e.g. `1898 г.` or `1898—1899 гг.` |
| `date_undate` | string | Undate-serialized calendar date (Julian, as printed) |
| `time_of_day` | enum | `unspecified` (single performance) \| `morning` (`УТРО`) \| `evening` (`ВЕЧЕРЪ`) |
| `theater` | string | verbatim theater name — value, not column: `Маріинскій`, `Александринскій`, `Михайловскій`, `Большой`, `Малый`, `Новый`, or others as they appear |
| `event_status` | enum | `performed` \| `no_performance` — see below |
| `bill` | string, nullable | work titles and genres verbatim, e.g. `Коппелія, бал. Танцы и группы изъ балета Талисманъ` |
| `receipts_text` | string, nullable | verbatim, e.g. `3462 р. 15 к.` |
| `receipts_rubles` | int, nullable | parsed |
| `receipts_kopecks` | int, nullable | parsed |
| `annotation` | string, nullable | benefit-performance / anniversary notes printed in the cell, verbatim |

**`event_status` and the completeness problem it doesn't solve on its own.**
`no_performance` (formerly named `is_dark` — renamed because "dark cell" is
theater jargon, not intuitive to a researcher) means the model read an
explicit printed dash: the theater really was closed that date, and that's
a fact about the source, not a gap in our data. But a *third*, more common
situation isn't representable by any value of this column at all: the
model's recall on this table is non-deterministically incomplete (see
`docs/eval/known_issues.md` #1) and simply omits some (date, theater)
cells from its output entirely. A missing row and a row that was never
expected look identical from inside this table — you cannot tell "the
theater was open every day this month" from "we don't know what happened
on the 14th" by querying `raw.performance_session` alone.

That third state — **`not_captured`** — is deliberately *not* added as a
third literal value here, because it isn't something transcribed from the
page; it's an inference from "here's the date/theater grid this page
should cover, here's what we actually got, here's the gap." It belongs in
`analysis.performance_session` instead, built by `build_duckdb.py`: for
each Repertoire page, the expected theater roster (era- and city-aware —
see below) is crossed with the page's observed date range, left-joined
against what was actually captured, and any missing combination is
inserted as a synthesized row with `session_status = 'not_captured'` and
no work/receipts data. This makes completeness directly queryable (e.g.
"what fraction of expected cells are `not_captured`, by season") instead
of invisible.

Two assumptions this reconciliation rests on, both worth stating rather
than leaving implicit: (1) the source prints one row per calendar day with
no skipped days within a page's date range, so a page's min/max captured
date defines its full expected range; (2) the "expected" theater roster
per page is inferred from which cities actually appear among that page's
*captured* sessions (for post-1898-99 single-city-block pages) or assumed
to be both cities (for pre-1898-99 combined pages, keyed on season) — see
`docs/structural_survey.md` for the era boundary and the Новый театръ
introduction date this depends on. If a page loses *every* session for an
entire city block to a recall failure, this method can't detect that gap
(there's no surviving evidence of which city was expected), which is a
known limit, not a silent error.

### `performance_work.csv`

Child of `performance_event` — a bill can list more than one work under a
single receipts figure (e.g. two one-act comedies).

| column | type | notes |
|---|---|---|
| `work_id` | string (PK) | |
| `event_id` | FK → performance_event | |
| `work_order` | int | 1-based, order printed in the cell |
| `work_title` | string | verbatim |
| `genre` | string, nullable | verbatim abbreviation (`оп.`, `бал.`, `ком.`, `др.`, `сц.`, `вод.`, `траг.`, `пьеса`, `карт.`, etc.) |

---

## Open questions to revisit once Graduates/ProductionStats are sourced

- Confirm Graduates fits the Spiski shape as-is (likely: institution = the
  theater school, position = graduating class/specialty, plus a graduation
  date instead of a tenure start).
- ProductionStats structure is still unconfirmed — likely closer to the
  Repertoire family (work × season aggregate) but needs a real sample page
  before committing to `performance_work`-shaped columns vs. something new.
