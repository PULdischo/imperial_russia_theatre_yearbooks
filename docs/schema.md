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

Vocabulary (RG, 2026-10-22): an **event** is one theater on one date in one
session (morning, evening, or unspecified when the day had only one), a row of
`event_entry` / `research.event`; it can contain more than one **performance**,
one work on its bill (`event_entry_performance` / `research.performance`).
Receipts belong to the event. Not "evening" or "night": events include
matinees, and event counts include `no_performance` and `not_captured` rows
unless said otherwise. A date when a theater gave nothing is a **no-performance
event** (`event_status = no_performance`; a dash in the printed cell), not a
"dark" night or day; "closed" only where the yearbook gives a reason (Lent, mourning). "Session" means only the slot (`time_of_day`) and the
raw JSON's `"sessions"` key, which keeps its name (renaming it would mean
re-extracting); the dated ledger in `docs/eval/known_issues.md` still says
"session" for an event. (`season_stat_check`'s `repertoire_sessions`-style
columns were renamed `repertoire_events` etc. the same day.)


**Decided 2026-10-22, BUILT the same day — discipline and company (RG).** `art_form` became
`discipline`: the kind of performing art, defined by its personnel (RG: Russian and French
drama "don't feature the same actors (unlike opera singers)"). Values: `ballet`, `opera`,
`Russian drama`, `French drama` for the Directorate's troupes ("opera", not "Russian opera":
"they didn't call it 'Russian opera'"); visiting troupes take a discipline by the same rule
instead of the catch-all `visiting troupe`: `German drama`, `Italian drama`, `French drama`
(Réjane, Bernhardt), `Russian drama` (Moscow Art Theatre), `Japanese drama`, `Italian opera`
(Moscow 1893-94, 1896-97; Угетти 1899-1902), `German opera` (SP 1897-98), `opera` (Любимовъ's
Russian-language troupe), `German operetta` (the Vienna operetta troupe, SP 1900-02, and
the German-language «Die Fledermaus», Михайловскій 1909-10). A new `company` column =
city + discipline for the Directorate's seven companies ("St. Petersburg ballet", "Moscow Russian
drama", "St. Petersburg French drama" …), RG: troupe and company "are both defined by city + the type of art", the
exceptions being visiting troupes, which get their own name (from the annotation) or a
placeholder ("visiting German drama troupe, St. Petersburg", "visiting Italian opera troupe,
Moscow" …) for the unnamed German-language and Italian opera seasons. "Art form" is
left free for what a work is. `item_kind` / `item_kind_basis` / `research.event.item_kinds` became
`genre_family` / `genre_family_basis` / `genre_families` (RG: "a much better description"),
values unchanged; the three genre levels are printed genre (`verbatim_genre`) → normalised
genre (deferred) → genre family.
---

## Shared: `source_pages.csv`

One row per digitized page. Every other table's `page_id` joins here.

| column | type | notes |
|---|---|---|
| `page_id` | string (PK) | synthetic, e.g. `RepertoireTables_1898-99_p019` |
| `entity_type` | enum | `Repertoire`, `Administrators`, `BalletArtists`, `Musicians`, `ProductionTeam`, `TheaterSchoolStaff`, `Graduates`, `ProductionStats` |
| `season` | string | academic year as printed in the filename, e.g. `1898-99` |
| `city` | enum, nullable | `SP` \| `Moscow` — only meaningful for BalletArtists/Musicians, which are split at the file level |
| `source_file` | string | original PDF filename |
| `source_page_index` | int | 0-based page index within the PDF |
| `printed_page_number` | string, nullable | the page number printed on the physical page (verbatim — some are stylized like `— 115 —`) |

---

## Spiski family (Administrators, BalletArtists, Musicians, ProductionTeam,
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
| `rank_or_title` | string, nullable | Despite the one name, corpus-wide content shows this holds two genuinely different kinds of fact, and their mix varies sharply by `entity_type`. **RANK** — institutionally conferred status: a Table-of-Ranks civil/court grade (`ст. сов.`, `колл. сов.`, `надв. сов.`, `тит. сов.`, `неимѣющій чина`...) or a court honorific (`Солистъ Двора Его Императорскаго Величества`, `Заслуженный артистъ Императорскихъ театровъ`) — dominant in Administrators (1483 non-blank) and much of TheaterSchoolStaff (543). **TITLE** — how the Yearbook labels the entry: an occupational role (`Капельмейстеръ`, `Концертмейстеръ`, `Репетиторъ балета`, a dual-role note like `(онъ же и библіотекарь Музыкальной библіотеки)`), a subject taught functioning as a teacher's title for TheaterSchoolStaff (`Танцы`, `Музыка`, `Французскій языкъ`, `Исторія`), or a workshop specialty functioning as a costumer/wigmaker's title for ProductionTeam (`Мужскіе парики`, `Женскіе костюмы балетной и французской труппъ`) — dominant in Musicians (52) and BalletArtists (60). Two further shapes land in this field but are **neither** rank nor title: BalletArtists' `1-я`/`2-я`/`3-я`/`4-я` values, confirmed by query (not assumed) to be a name-disambiguation device rather than a seniority marker — every instance checked pairs a distinct patronymic with each ordinal within a shared surname on the same page (e.g. Иванова: Елена Павловна=1-я, Марія Ѳедоровна=2-я, Александра Ивановна=3-я, Наталья Евдокимовна=4-я) — the same convention already printed directly into `family_name` elsewhere in the corpus (see `family_name`'s own note above, `Алексѣева 1-я`); a stray instance of that convention, not a new kind of fact — relocated onto `family_name_clean` rather than tagged-and-dropped. And dual-role/cross-reference notes (`(онъ же и режиссеръ)`, `(см. СПБ. балетъ)`) — administrative notes that happen to land here, conceptually closer to `tenure_note_text` — relocated onto `tenure_note_text_clean` (scan-verified first: print order is note-then-date, e.g. `Вальцъ, Карлъ Ѳедоровичъ (онъ же и декораторъ) (съ 3 октября 1861 г.)`), the same contamination pattern already fixed for `instrument` (known_issues.md #66). **This split is implemented, not just characterized** — `analysis.person_entry.rank_clean`/`title_clean` (pure SQL derivation, `raw.person_entry.rank_or_title` itself stays untouched/verbatim), `rank_or_title_excluded_reason` (audit-only, tags the 48 rows that are neither rank nor title after the two relocations above), and `research.person_appearance.rank`/`title` in place of the old `rank_or_title` column. **ProductionTeam addendum (2026-10-03, issue #132)**: the raw extraction put a workshop specialty ("Мужскіе парики", "Женскіе костюмы оперной и русской драматической труппъ") in `rank_or_title` on 43 rows but left it inside `tenure_note_text` on 204; `analysis.person_entry.title_clean` now carries it for every ProductionTeam row (trailing period dropped) and `tenure_note_text_clean` no longer repeats it. Raw is untouched; no other entity type is affected. Full write-up, including the classification's validation (0 mismatches against a Python reference across all 2208 non-blank values) and a DuckDB RE2-vs-Cyrillic gotcha hit along the way, in known_issues.md #67. |
| `service_class` | string, nullable | Table-of-Ranks class where printed (`VII кл.`) — survey found this starts appearing by 1907, absent in 1890-91 |
| `instrument` | string, nullable | Musicians only. A structured extraction sitting alongside `tenure_note_text`, not derived from it downstream — the opposite design call from `heading_path`'s department/position split above, and deliberately so. `heading_path` stayed one verbatim field because the department/position boundary is a visual/typographic judgment call (indentation, bold weight) a model can't reliably reproduce from text alone. An instrument name isn't that: it's a closed vocabulary (~40 known instrument names, see `_KNOWN_INSTRUMENTS` in `pipeline/parse_and_validate.py`) appearing as a literal, recognizable token in the sentence — the same kind of well-defined pattern that already justifies asking the model for structured `service_periods` (→ `person_entry_service`) alongside the verbatim tenure note, not a reason to avoid a dedicated column. `tenure_note_text` and `instrument` are also not simply the same fact in two places: cross-reference-stub rows routinely carry an instrument with no date in the same row (the date lives on a different "home" page), so `instrument` is independently useful information the verbatim field doesn't always carry in a fixed position. In practice `tenure_note_text` is genuinely messy free text (missing parens, missing dates, cross-reference-prefixed, dual-role parentheticals, compound dates, service/death notes appended) — every edge shape found and fixed in the #54-#65 issue arc was tractable specifically because the extraction lives in Python (a real lexicon, a boundary-safety check, page/index-keyed hand-fixes checked against scans), not as SQL regex reconstructing it from the raw sentence. |
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
| `entry_id` | FK → person_entry | |
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
| `entry_id` | FK → person_entry | |
| `credit_type` | enum | `category_totals` \| `named_work` |
| `label` | string | for `category_totals`: `балетахъ`/`операхъ`/`драмѣ`/`Всего`; for `named_work`: the work title |
| `role_name` | string, nullable | only for `named_work` — the character name in parens |
| `category_production_count` | number, nullable | only for `category_totals` rows other than `Всего`: the count of distinct productions in that category (the "10" in "Въ 10 балетахъ—45"), parsed from `credit_summary_text`. Null when the sentence doesn't print this figure (checked against the real corpus: present for 5,711/7,255 credit_summary_text values, 79%) |
| `category_credit_count` | number | the count after the dash (the "45" in "Въ 10 балетахъ—45"); usually an integer, but the printed ledger occasionally uses a fractional value (e.g. `.5`) for a role split between two artists — kept as printed, not rounded |

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
| `annotation` | string, nullable | benefit-performance / anniversary / charity notes printed in the cell, verbatim. A genre-less occasion line printed as a heading at the top of a cell («Бенефисъ г. X.», «Спектакль въ пользу ...», «Концертъ въ пользу инвалидовъ.») belongs here and not in `works` (issue #151, follow-up 3: 83 such lines had been stored as work no. 1 in the 1890-98 spread seasons and were moved); a session with such a note and no work is an annotation-only special (issue #141). Genre-less lines set like work lines («Концертное отдѣленіе», «Дивертиссементъ», «Гимнъ», «Сцена г. ...») stay works |
| `printed_page_number` | string, nullable | the page number actually printed on the physical page this event appeared on — for citation. Lives here, not just on `source_pages`, because a two-page-spread `page_id` (1890-91–1897-98) can combine content from more than one physical printed page; the session's own `date_undate` picks out which one. Backfilled from a scan-verified reference table (`pipeline/parse_and_validate.py --printed-page-numbers`), never derived from `page_id`/render-index — that inference has produced real bugs before (see `docs/eval/known_issues.md`'s printed_page_number build-out). |

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
on the 14th" by querying `raw.event_entry` alone.

That third state — **`not_captured`** — is deliberately *not* added as a
third literal value here, because it isn't something transcribed from the
page; it's an inference from "here's the date/theater grid this page
should cover, here's what we actually got, here's the gap." It belongs in
`analysis.event_entry` instead, built by `build_duckdb.py`: for
each Repertoire page, the expected theater roster (era- and city-aware —
see below) is crossed with the page's observed date range, left-joined
against what was actually captured, and any missing combination is
inserted as a synthesized row with `event_status = 'not_captured'` and
no work/receipts data. This makes completeness directly queryable (e.g.
"what fraction of expected cells are `not_captured`, by season") instead
of invisible.

`research.event` carries these placeholders forward (`date_confidence =
'synthesized_gap'`) with one exception (`build_research_model.py`, RG
2026-09-26, known_issues.md #93): a placeholder is left out when a real
event on the same page and theater resolves to the same *research-layer*
date. That happens when a printed day is misprinted (the analysis layer
places the gap on the true day, while the real row's date is only
corrected later by `validate_performance_dates.py`'s overrides), or when
a page's header can't be parsed and `RESEARCH_PAGE_MONTH_OVERRIDES`
supplies its month. `analysis.event_entry` keeps every placeholder
unchanged.

Two assumptions this reconciliation rests on, both worth stating rather
than leaving implicit: (1) the source prints one row per calendar day with
no skipped days within a page's date range, so a page's min/max captured
date defines its full expected range; (2) the "expected" theater roster
per page is inferred from which cities actually appear among that page's
*captured* events (for post-1898-99 single-city-block pages) or assumed
to be both cities (for pre-1898-99 combined pages, keyed on season) — see
`docs/structural_survey.md` for the era boundary and the Новый театръ
introduction date this depends on. If a page loses *every* event for an
entire city block to a recall failure, this method can't detect that gap
(there's no surviving evidence of which city was expected), which is a
known limit, not a silent error.

### `event_entry_performance.csv`

Child of `event_entry` — a bill can list more than one performance under a
single receipts figure (e.g. two one-act comedies).

| column | type | notes |
|---|---|---|
| `performance_id` | string (PK) | |
| `event_id` | FK → event_entry | |
| `performance_order` | int | 1-based, order printed in the cell |
| `performance_title` | string | verbatim. `[?]` marks a character the scan can't show (e.g. a digit hidden in the binding fold: "[?]-е д. бал. Пахита"); brackets never occur in printed titles (RG, 2026-09-29, issue #115) |
| `genre` | string, nullable | verbatim abbreviation (`оп.`, `бал.`, `ком.`, `др.`, `сц.`, `вод.`, `траг.`, `пьеса`, `карт.`, etc.) |

---

## Research-layer event and performance columns added 2026-10-12

Built by `build_research_model.py` (`build_art_forms`, `EVENT_FLAG_RES`); nothing here changes
`raw` or `analysis`. Rulings and open points: `docs/eval/known_issues.md`, entries of 2026-10-12.

**`research.event`**

| Column | Meaning |
|---|---|
| `time_of_day` | `morning` / `evening` / `unspecified`, as in `event_entry.time_of_day`. The yearbook labels a session only when a theater had two on one day, so `unspecified` is the single session of its day, not "unknown" |
| `receipts_verbatim` | the receipts as printed (`receipts_text`), beside the parsed `receipts_total_kopecks` |
| `annotation` | the printed heading or note of the cell (`event_entry.annotation`), verbatim |
| `is_benefit`, `is_charity`, `is_free`, `is_student_performance`, `is_reduced_price` | wording classes of the annotation (benefit / «въ пользу», «благотворительный» / «безплатный» / «для учащейся молодежи» / «по уменьшеннымъ цѣнамъ», with their French and German forms). They record what the annotation says and are not a judgement about prices. `is_benefit` is also set by a «Bénéfice de …» line stored as a performance title. A cell whose banner was not transcribed has all five false. One exception to "what the annotation says": `is_free` is also set from `pipeline/research_corrections/free_period_notes.csv`, for a note printed once that covers a run of days (Moscow, May 1896: «Всѣ послѣдующіе спектакли до конца сезона — безплатные.») |
| `has_anthem` | the bill includes the anthem |
| `n_works` | performances on the bill, not counting the anthem and heading lines stored as titles |
| `disciplines` | the distinct disciplines on the bill (see `research.performance.discipline`), in the fixed order of `DISCIPLINES` in `build_research_model.py`, joined by `; ` (`ballet; opera`). NULL when no performance on the bill has one. Was `art_forms` until 2026-10-22 |
| `companies` | the distinct companies on the bill (see `research.performance.company`), joined by `; ` (`Moscow ballet; Moscow opera`). NULL when no performance on the bill has one |
| `genre_families` | the distinct genre families on the bill (see `research.performance.genre_family`), in a fixed order, joined by `; ` (`ballet; opera; play; concert`). An event the Repertoire prints as a concert heading with no titled work reads `concert`. NULL when nothing on the bill has a kind |

**`research.performance`**

| Column | Meaning |
|---|---|
| `genre_family`, `genre_family_basis` | WHAT the item was, whoever gave it (RG, 2026-10-13; named `item_kind` until 2026-10-22): `ballet`, `opera`, `operetta`, `play`, `comedy-ballet`, `pantomime`, `divertissement`, `concert`, `recitation / reading`, `lecture`, `tableau / apotheosis`, `cinema`, `anthem`, or NULL (a handful of titles that cannot be placed). Derived from the printed label and title. `play` covers every spoken-drama label; the sub-type (comedy, drama, vaudeville, fairy tale …) is in `verbatim_genre` and is not normalised. A normalised genre between the two (comedy, drama, tragedy, vaudeville, шутка … across languages and spellings) was considered and deferred (RG, 2026-10-22): it would pay off mainly for drama; for ballet and opera nearly every performance prints «бал.» / «оп.», and the rarer labels («феерія», «фант. бал.», «опера-былина») each belong to one or two works. An operetta is `operetta` whichever company gave it; a divertissement is `divertissement` whether or not it is known to have been danced (`discipline` says `ballet` where it is). Concert and cinema are genre families only and have no `discipline` |
| `discipline` | the kind of performing art of the troupe that gave it, defined by its personnel (RG, 2026-10-22; named `art_form` until then): `ballet`, `opera`, `Russian drama`, `French drama` for the Directorate's troupes; for a visiting troupe the same rule gives `German drama`, `Italian drama`, `French drama`, `Russian drama`, `Japanese drama`, `Italian opera`, `German opera`, `German operetta` or `opera` (see the note at the top of this file). Decided by company, not by printed genre label (RG, 2026-10-12): a troupe is visiting when the yearbook prints no productions list for it, which covers the German-language performances of the whole period, the Italian and German opera seasons, and guests named in an annotation. Operettas go with the company that performs them (opera at the Маріинскій and Большой, Russian drama elsewhere). Comedy-ballets («ком.-бал.») are Russian drama. A work whose record has no genre takes, per performance, the genre printed on that performance, or else the genre printed for the same work in the same season (RG: "as long as they are in the same season"); the basis says so. NULL = deliberately unassigned: the anthem, a title with no genre printed that season, a divertissement outside ballet, a cantata |
| `company` | the troupe that gave it: city + discipline for the Directorate's seven companies (`St. Petersburg ballet`, `Moscow opera` …); a visiting troupe's own name from the event annotation (`Moscow Art Theatre`, `Vienna operetta troupe` …), or a placeholder when none is printed (`visiting German drama troupe, St. Petersburg`). NULL with `discipline` |
| `discipline_basis` | the rule that decided, in words (was `art_form_basis`). Read it before relying on an edge case; `docs/eval/art_form_review_2026-10-12.csv` lists the unassigned and doubtful ones |
| `includes_dance`, `includes_dance_basis` | a performance that is not a ballet but belongs to a work known to contain dancers (RG, 2026-10-12): the comedy-ballets, and the operas listed in `pipeline/entity_curation/works_with_dancers.csv` from named roles in the ballet rosters and from the season reviews. A performance is marked only in a season and city for which there is evidence (RG: "we can assume that all the performances of a production in one season were similar, but not beyond that"). The basis starts `direct:` when the source names that very performance or the printed genre is «ком.-бал.», and `season:` when dancers are attested in the work in that season and city. Excerpt rows are not marked. **The value is yes or blank, never no** (RG): blank means "not known", because the rosters credit dancers with 10 to 25 operas a season but name only a handful of them |
| `performance_source`, `performance_source_note` | `repertoire` for every performance the Repertoire prints. `supplied: …` for a performance the Repertoire cell does not name but another part of the same yearbook does (`pipeline/research_corrections/supplied_performances.csv`; RG, 2026-10-12). A supplied row has no `verbatim_title`, no `performance_order`, and is not counted in `work.appearance_count`; the note gives the evidence. `repertoire; work from …` for a performance the Repertoire does print but whose work the research layer takes from another part of the yearbook (`performance_work_overrides.csv`; first case 25 Jan 1904, «бал. Пахита» shown as its 3rd act per the ballet list): `verbatim_title` keeps the Repertoire's wording, `work_id` is the corrected work. Filter on `performance_source = 'repertoire'` for what the tables alone print |
| `is_ceremonial` | the anthem («Гимнъ», «Hymne»): "not a work, per se, but a ceremonial item" (RG). Still linked to its `work_id` |

A guest who performs in Russian or French looks like the house troupe unless the annotation names
the troupe; guest soloists appearing with a house troupe («Спектакль съ участіемъ …») are
classed with that troupe.

## Open questions to revisit once Graduates/ProductionStats are sourced

- Confirm Graduates fits the Spiski shape as-is (likely: institution = the
  theater school, position = graduating class/specialty, plus a graduation
  date instead of a tenure start).
- ProductionStats: settled (2026-10-09, below). It is a season aggregate (a count and
  receipts per category and theater), not an event table, so it has its own tables.

---

## Productions lists (BalletProductions) — `production_entry`, `production_entry_performance`

The per-season list of productions (списокъ пьесъ), "Балетъ" section,
one list per season × city (known_issues.md #101). Verbatim tier: the
printed description is NOT split into genre / acts / roles here — that
belongs to the research layer. CSVs: `outputs/<run>/parsed_verified/`, loaded into
`raw.*` by `pipeline/load_productions.py`. The creator names are split
out of `description_text` into `analysis.production_entry_credit`
(below).

### `production_entry` — one row per printed entry

| column | type | notes |
|---|---|---|
| `production_entry_id` | string, PK | `{page_id}__e{NNN}` (a page-break entry keeps its first fragment's ID) |
| `page_id`, `season`, `city` | string | city from the filename (`SP`/`Moscow`) — never printed on the page |
| `section_heading` | string, nullable | "Балетъ", or null on a continuation page |
| `printed_page_number` | string, nullable | "32-33" for a two-page spread; null if not printed |
| `entry_order` | int | order on the page |
| `list_number` | string | printed number, without `*` |
| `is_premiere` | bool | `*` printed before the number |
| `title` | string | bold / letter-spaced words only |
| `description_text` | string | everything between title and "Исполненъ", verbatim: genre, acts/scenes, authorship, a regular-type parenthetical title. Three asterisks printed as a triangle (an asterism: a withheld name) are recorded as the single character **⁂** (U+2042), e.g. "Петипа и Г⁂" — search for ⁂, not "***". Who is behind a pseudonym is research-layer information, never written into this field |
| `performed_text` | string | "Исполненъ: …" verbatim, up to (not including) "Всего" |
| `total_text` / `total_count` | string / int | "Всего—N разъ." and N (integer taken from the printed text) |
| `post_total_text` | string, nullable | text printed after Всего (extra part-performances not counted in the total) |
| `n_dates` | int | counted dates (excludes `outside_total`), comparable to `total_count` |
| `fragment` | string, nullable | `merged` if the entry spanned a page break |

### `production_entry_performance` — one row per printed date

| column | type | notes |
|---|---|---|
| `production_performance_id` | string, PK | `{production_entry_id}__d{NNN}` |
| `production_entry_id` | FK | |
| `date_order` | int | printed order (not always chronological in the print) |
| `year_text`, `month_text`, `day_text` | string | verbatim, year/month carried forward as the print implies |
| `note` | string, nullable | the per-date parenthetical, e.g. "2-я и 3-я карт." |
| `outside_total` | bool | a part-performance printed after Всего |
| `date` | ISO date, nullable | derived from the list's **season** (Aug–Dec = the season's first year, Jan–Jul = its second), not from the printed year (RG, 2026-09-28): the list belongs to its season by provenance. NULL if the printed day is impossible ("38 декабря") |
| `year_printed_matches_season` | bool, nullable | false when the printed year differs from the one the season implies (4 rows, e.g. "1897 г.—февраля 12" in the 1897-98 list); the printed year stays verbatim in `year_text` |

### `analysis.production_entry_credit` — one row per (name, role) mention in `description_text`

Built by `pipeline/build_production_credits.py` (issue #133): rule-based
parsing of the verbatim description, plus an explicit override list.
No new facts. Names stay exactly as printed (case endings, orthography,
the print's own slips). Converting them to the nominative and linking
them to persons belongs in the entities layer.

| column | type | notes |
|---|---|---|
| `credit_id` | string, PK | `{production_entry_id}__c{NN}` |
| `production_entry_id` | FK → `raw.production_entry` | |
| `credit_order` | int | printed order within the description; a name with two roles ("соч. и музыка") gives two consecutive rows |
| `name_printed` | string | verbatim, e.g. "М. И. Петипа", "Сенъ-Жоржа", "Л. И. Ивановымъ", "Тальони (отца)", "Г⁂", "⁂", "К. В." |
| `honorific_printed` | string, nullable | барона / князя / г-на / г. / гг. / лорда, as printed before the name. **Lower-case г. (гг.) is the honorific (господинъ); capital Г. is an initial** and stays in `name_printed` (RG, 2026-10-05), even where it doesn't match the person's known first name (Г. Минкуса, Г. Гертеля, Г. Сенъ-Жоржа, Г. Оге…, all as printed) |
| `qualifier_printed` | string, nullable | words scoping the credit, e.g. "4-го д.", "«Оживленнаго сада»", "нѣкоторые нумера", "частью", "«Конекъ-Горбунокъ»" |
| `role_text` | string, nullable | the printed role words, verbatim ("соч.", "музыка", "поставленъ балетмейстеромъ", "сюжетъ заимствованъ изъ сказки"…); null when the name follows the genre with no role word ("Балетъ Нюитера и С. Леона") |
| `role_category` | string | coarse label derived from `role_text`: `author` (соч., or no role word). "Соч." covers the ballet's authorship as a whole, scenario and choreography. These were often done by one person or shared between two (RG, 2026-10-03), so it is deliberately not split into librettist vs choreographer, `libretto` (либретто / программа / сюжетъ + a person / составлен(ъ/а)), `music`, `instrumentation`, `staging` (постановка / поставленъ / танцы…), `source` (the author of the tale/poem/novel the ballet is based on) |
| `is_pseudonym` | bool | name contains ⁂ |
| `is_collective` | bool | "и др.", "и друг.", "разныхъ авторовъ" — not a person |
| `note` | string, nullable | parser notes on an individual reading |

The same printed surname can be different people, and `role_category`
keeps them apart: "сказки **Перро**" (`source`, Charles Perrault) vs
"соч. Ж. **Перро**" (`author`, Jules Perrot).

---

## Season production stats — `season_stat_*` (raw) and `research.season_stat_*`

The yearbook's printed totals page for each season ("Всего въ теченіе сезона … было
спектаклей": counts, and from 1893-94 receipts and footnotes, per category and
theater). 19 pages, 1891-92 to 1910-11, none for 1890-91 (the page type starts in
1891-92) and none found for 1905-06. Hand-transcribed and checked on the scans
(`docs/season_stats/`, edited in `_build.py`), loaded by `pipeline/load_season_stats.py`.
These are season aggregates with no event key, so they sit beside the event tables and
do not join into them.

**Raw tier (verbatim):** `raw.season_stat_page` (season, printed page, heading, format),
`raw.season_stat_line` (one row per printed line with a number: `line_kind` is `venue`,
`part`, `subtotal` or `category`; `category_verbatim` as printed, `category` with the
ditto resolved; `count`; `receipts_verbatim` and `receipts_kopecks`; `footnote_refs`),
`raw.season_stat_footnote`, `raw.season_stat_dated_note` (jubilees and benefits listed by
date, from 1909-10). A number the print gets wrong stays as printed, with a `note`.

**Research tier:**

| table | one row per | notes |
|---|---|---|
| `research.season_stat_line` | printed line | the raw lines with `city` as `SP`/`Moscow`; PK (season, city, line_no) |
| `research.season_stat_footnote` | printed footnote | verbatim |
| `research.season_stat_check` | (season, city) | printed figures beside the same figures computed from `research.event` (below) |

`season_stat_check` columns: `printed_count` (every printed line with a number except the
ruled subtotals, which repeat their venue/part lines); `printed_count_with_receipts`;
`printed_receipts_kopecks` (sum of lines that print receipts; **NULL** in 1891-92 and
1892-93, whose pages print no receipts); `repertoire_events` (performed events, a
morning and an evening row counted separately); `repertoire_days` (distinct theater and
date); `repertoire_events_with_receipts`; `repertoire_receipts_kopecks` (sum of
`research.event.receipts_total_kopecks`); `repertoire_charity_text_events` and
`..._receipts_kopecks` (events whose annotation says «въ пользу»: from 1898-99 the page's own
footnote says its receipts EXCLUDE charity performances, so this is shown beside the
receipts, not subtracted, because which events the yearbook treated as charity is not
assumed); and the differences (Repertoire minus printed) `events_minus_printed`,
`days_minus_printed`, `receipts_minus_printed_kopecks`.

**How to read it.** This is a checksum on the Repertoire, not a correction of it, and a
difference is not an error in either source until a row is checked on the scans. Plain
events (`repertoire_events`) are the closest match to the printed counts (they beat both "days" and "only
receipted events" over the 34 seasons with a count-and-receipts page); the printed
count is usually within a few of them in the 1890s and drifts higher in the Repertoire
from 1901-02. 1907-08 and 1908-09 print category totals only, with no per-theater lines.
The genre- and theater-level comparison (families, ballet counted three ways) stays in
`pipeline/compare_season_stats.py`, because it needs judgment-based classification.

## Season review evidence — `research.review_assertion`

One row per **assertion a season review makes**: this performer danced this role,
in this work, on this date. Built by `pipeline/build_review_assertions.py` from
`entities.review_mention`; 1,952 rows over 19 seasons.

**Published.** RG, 2026-10-12: include it in the Datasette/HF dataset. It is in
`build_datasette.py`'s `TABLES`, so it exports to `research_dataset.sqlite` with
real foreign keys and Datasette renders the links.

| column | notes |
|---|---|
| `assertion_id` | PK |
| `page_id`, `block_id` | citation back into the **raw** layer, which is NOT published — plain columns, deliberately not FKs |
| `season`, `city`, `printed_folio`, `date_undate` | where and when; `date_undate` is the review's own date, Julian as printed |
| `role_surface`, `performer_surface`, `work_surface` | verbatim as printed, pre-reform orthography, inflected as the sentence has them |
| `performer_person_id` → `research.person` | **nullable**: 302 of 1,952 are unresolved |
| `performer_candidates_n`, `performer_candidate_ids` | the ambiguity itself, kept rather than hidden; ids are `|`-delimited, so this is not an FK |
| `work_id` → `research.work` | **nullable**: 737 unresolved |
| `link_method` | how the performer was resolved — `already-linked` 1,531, `unresolved` 302, `spiski-credit-role-season` 67, `spiski-credit-work` 30, `spiski-credit-role` 22 |
| `grammar` | the construction the mention was read out of (e.g. `role-performer`) |
| `work_source` | where the work came from (e.g. `block`) |

**The nulls are the point, not a defect.** An unresolved mention is still evidence
that the review names someone in a role; dropping those rows would silently narrow
the record. Verified before declaring the FKs: **zero dangling references** to
`person` or `work`.

**Do not join this to `research.performance` as if it were the same fact.** A
review asserts a casting; the Repertoire records a performance. They agree often
and disagree sometimes, and the disagreement is research material.

## Printed leavings contradicted by later lists — `research.person_tenure_note` (added 2026-10-19)

One row per person whose printed «Оставилъ/Оставила службу ...» is contradicted by the later lists (RG, 2026-10-19, M9 scan
checks, `docs/eval/person_audit_2026-10-19/`). The research layer reads their service as continuing to the last listing
(`research.person.last_attested_season` already does) and keeps the printed statement here. Raw keeps the note and its parsed
end date untouched. Source: `pipeline/research_corrections/person_tenure_discrepancies.csv`; the build fails unless the person
exists, prints that leaving date in that list, and is listed in every season `service_periods` names.

| column | meaning |
|---|---|
| `person_id` | FK to `research.person` |
| `list`, `city` | the list (entity_type) and city the leaving is printed in |
| `printed_leaving`, `printed_leaving_date`, `printed_in_seasons` | the note as printed, its date, the volume(s) printing it |
| `research_reading` | `continuing service`, or `two periods (possibly continuous)` (Егорова 1-я) |
| `service_periods` | the research reading in seasons; `;` separates periods |
| `discrepancy` | what the print says vs what the lists show, with the same-date colleagues who really left |
| `corroboration_found`, `corroboration_wanted` | evidence from the season reviews so far; what would settle it (reviews, RGIA дела) |
| `decided` | who decided and when |

Not yet in the Datasette export (`build_datasette.py` TABLES/SCHEMAS) -- add it there before the next publication.
