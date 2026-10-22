# Jubilees and obituaries in the Yearbooks

Every jubilee notice and obituary in the scanned jubilee/obituary sections of the
*Ежегодникъ Императорскихъ театровъ* (Yearbook Scans - Originals), 1890-91 to 1910-11,
with the ballet-relevant ones pulled out.

## Files

| File | What it is |
|---|---|
| `jubilees_obituaries_all_entries.csv` | Every entry (702 rows, 655 of them person entries). `source_type` says where each comes from: `section` (357: the scanned sections, stand-alone articles and other files), `review` (87 + 7 work milestones), `roster` (101 death marks), `repertoire` (112 + 10 institutional or event anniversaries). Check columns: `date_check`, `tier_check`. |
| `jubilees_obituaries_ballet_only.csv` | The subset with `relevance` = `core` or `mentions`. |
| `jubilees_obituaries_person_links.csv` | Each of the 655 person entries linked to a `research.person` record, or marked as having none (2026-10-22; see "Links to the people in the database"). |
| `unscanned_worth_getting.md` | Jubilee, obituary and memorial items the Yearbooks contain that are not in the scans, ranked. |
| `AUDIT_2026-10-10.md` | What has been verified, how far, and the known gaps. |
| `repertoire_date_check.csv`, `repertoire_annotations_matched.csv` | The Repertoire's annotations against the catalogue, both directions. |
| `roster_deaths_matched.csv` | Every roster death mark and whether the catalogue has the person. |
| `review_deaths_matched.csv` | The reviews' death lists paired with obituaries and rosters. |
| `first_read/` | The per-section first readings (A–H), the Season Review notices (`R_reviews.csv`), the contents-page listings (`T1`, `T2`) and the reader briefs. |
| `blind_second_read/` | An independent second reading of every heading name and date (V1–V5). |
| `build/` | `compare_readings.py` (first vs second read → `reading_comparison.csv`) and `build_catalogue.py` (writes the two CSVs above); `build_obsidian_notes.py` (the Russian/English reading notes, see below). |

## Stand-alone articles on one person

Six scanned articles are not under a «Юбилеи» or «Некрологи» heading in the Yearbook but share the
form (portrait flanked by the years or «XXV», service record, roles): Іогансонъ (1891-92), Камышевъ
(1892-93), Манохинъ (1895-96), Петипа (1896-97) — each written for a jubilee — and Всеволожской
(1899-00, a sketch of his work as a designer) and Волконскій (1901-02, on his leaving the
directorship). They are in the catalogue with `kind` = `biographical_feature`; the occasion is in
`notes`. Read once (`first_read/J_features.csv`), with no blind second read.

## Obsidian reading notes (in progress, 2026-10-12)

`build/build_obsidian_notes.py` makes one Russian/English note per ballet-relevant entry that has a
full text, with the catalogue's metadata as properties and a "My notes" section that survives
rebuilds. The Russian is a single machine reading of each page (`pipeline/run_reviews.py`, one pass)
and the English a machine translation (`pipeline/translate_reviews.py`); both live under
`outputs/jubilees_obituaries/`, which is not in git. Reading copies only — quote from the scan.
The steps are in the script's header.

## Relevance tiers

- `core` — a career in ballet: dancers, ballet masters, régisseurs, teachers, ballet composers and
  conductors, ballet-orchestra players. By RG's ruling (2026-10-10) also: designers and machinists,
  administrators over the ballet, the ballet critic Плещеевъ, players in the combined
  opera-and-ballet orchestras, and drama actors who began in ballet.
- `mentions` — not a ballet person, but the text says something about ballet (see `evidence_verbatim`).
- `none` — no ballet content.

`tier_basis` says whether the tier is the reader's call or RG's ruling.

## How it was checked

Each section was read entry by entry from page images (the PDFs' text layers are unusable).
A second reader, blind to the first, then re-read every heading name and date.
Of 338 headings paired between the two readings, 320 matched exactly; the rest differed only in
how much of the heading was copied (bracketed aliases, titles for names), except three names, settled on the scan in favour of the
second read: Борншейнъ, Платонова Юлія Ѳедоровна, Пфейферъ Ѳедоръ. No death or jubilee date
disagreed across the 316 entries where both readings give one.

**The tiers were then read a second time** (2026-10-11/12). Every one of the 347 section entries was
re-read in full by a reader who was not shown the first verdict (`first_read/tier_second_read/`:
brief, worklists, outputs, `tier_comparison.csv`). 332 verdicts agree. No entry the first read called
`none` turned out to have ballet content in its text. The 15 differences are all about how to class
a fact both readers saw: five moved to `core` under RG's rulings (a ballet set by Васильевъ В. В.;
ballet-orchestra service by Эзеръ, Дровинъ, Помазанскій, Вейкманъ); four school posts moved to or stay
at `mentions` under the school-staff ruling (Бостремъ, Маннъ, Боборыкинъ, Спиро; Ришардъ and Орловъ
were there already); RG ruled on the rest on 2026-10-12 — posts that touched the ballet where the notice never names it:
Кистеръ and Бегичевъ (heads of the theatres) `core`; Альбрехтъ (Inspector of Music) and Юмашевъ
(assistant head of productions) `mentions`; Правдинъ (head of the school's drama classes) `none`; Куликовъ's list of plays stays `mentions` on a comedy
titled «Представленіе Эсмеральды въ провинціи», which the second reader took for a look-alike.
The result for each entry is in the `tier_check` column. Three entries are cut off in the scan and
tiered on what is visible (Панчинъ, Бларамбергъ, Лентовскій).

Read once only: roles, the English glosses, and the six stand-alone articles.

## Notices from the Season Reviews

The reviews report jubilee benefits, farewell performances and memorial performances that often have
no article of their own. These are in `jubilees_obituaries_all_entries.csv` with `source_type` = `review`: `source_file` is
the review `page_id`, `pdf_page` the block number, `printed_page` the review page's printed folio.
`name_verbatim` is the name as printed, usually in an oblique case; the nominative is in `notes`.
Kinds: `jubilee`, `farewell`, `memorial_feature`, and `death_notice` for death-list names that have
no obituary in the scanned sections. Death-list names that do have an obituary are not repeated.
These rows rest on the database's existing review transcription and were read once.

The first sweep was a keyword search (jubilee, death, funeral, farewell, benefit words). Two wider
searches during the audit (last appearances, «чествованіе», «-лѣтіе», daggers, wreaths and addresses)
added nine more notices, kept separately in `first_read/R2_reviews_wider_search.csv`.

Finally every block of review text in the database (3,790 blocks, 1.4 million characters) was read
through by 14 readers, flagging by meaning and not by wording (`first_read/review_full_read/`: the
brief and the flags). Of 188 flags, 124 were already in the catalogue; I read the other 64 in
context. Added from them: Ауэръ's last participation (22 Oct 1906), the second Чайковскій memorial
performance (22 Feb 1894), the Чайковскій monument-fund performance in Moscow (7 Apr 1895), and the
ballet's wreath at Барцаль's jubilee (which moves him to `mentions`). Two further kinds were added
for things the read turned up that are not jubilees or farewells in the strict sense (kept at RG's
decision, 2026-10-11):

- `departure` — a leaving noted in passing, with no farewell: Кякштъ (1908), Гримальди (1906),
  Кшесинская's withdrawal (1912-13), Стрепетова (1890).
- `work_milestone` — an anniversary or round-number performance of a work, not a person: the 200th
  «Дочь Фараона» (1901), the 100th «Спящая Красавица» (1903), the 50th «Щелкунчикъ» (1905), 50 years
  of «Конекъ-Горбунокъ» (1912), and three opera ones. These are not counted as person entries.

Read and left out: composers called «покойный» long after their deaths; anecdotes from decades
earlier (Андреянова 1848, Прихунова 1856, Лебедева); charity evenings for the artists' home and for
monument funds other than Чайковскій's; state occasions (Alexander III, the emancipation jubilee);
Толстой; a veiled allusion to Моттль's death; М. И. Петипа's benefit of 9 Feb 1903 (no anniversary
stated); the 75 years of «Жизнь за Царя» and 25 of «Евгеній Онѣгинъ» mentioned in passing.

`see_also` lists other entries that look like the same person (same surname and matching initials),
e.g. a jubilee notice in a review and the obituary years later. It is a pointer, not an identity claim.

## Death marks in the rosters

The printed rosters mark a death with a dagger and date («† 4 іюня 1891 г.»). `roster_deaths_matched.csv`
(from `build/match_roster_deaths.py`) checks all 192 such rows — 170 people — against the catalogue:
71 rows match an obituary or death notice, 121 rows (101 people) do not, almost all in seasons whose
volumes print no obituaries. Those 101 are in `jubilees_obituaries_all_entries.csv` as `kind` = `death_mark`,
`source_type` = `roster`, with the name and date as stored in the database (not re-read here).

Their tier comes from the roster section. `core`: ballet troupe, dance teachers, designers and
machinists, and the ballet or opera-and-ballet orchestra. `mentions` (RG, 2026-10-10): staff of the
theatre school who did not teach dance, wardrobe and lighting staff, and the music librarians.
`none`: doctors, clerks, drama-course teachers and the drama-theatre orchestras.

For 25 orchestra players the stored heading is only «Музыканты». `build/roster_orchestra_lookup.csv`
gives the orchestra for each, found by following the list's headings and numbering back through the
roster pages: 17 are in the opera-and-ballet orchestra, 6 in the Alexandrinsky, Mikhailovsky or Maly
orchestras, 2 are librarians of the Central Music Library.

The 52 core roster-only deaths were then re-read on the roster scans by readers who were not shown
the stored date (`first_read/roster_death_recheck/`; 59 roster rows, plus three 1910-11 rows read by the
main session). Every date agrees. Three names gain an ordinal the database row lacks (Ячменева 1-я,
Брыкинъ 1-й, Александровъ 2-й). The `mentions` and `none` roster rows were not re-read.

Printed date conflicts found, each read on the scans on both sides:
Соловьевъ (roster † 4 октября 1890, obituary 9 октября); Мейеръ (roster † 28 марта 1893, obituary
25-го марта, twice); Всеволожскій (roster † 28 октября 1909, obituary † 29 октября);
Константиновъ П. А. (ballet roster † 25 декабря 1906, orchestra roster † 27 декабря, same volume).
The roster also supplies the year the obituary omits for Шенекерль (9 декабря 1895).

## The Repertoire's annotations

The Repertoire tables print a line above some performances: «Бенефисъ г-жи …», «Прощальный бенефисъ …»,
«… за 25-ти-лѣтнюю службу», «Спектакль въ память …». `build/match_repertoire_annotations.py` checks
these 1,755 annotated events against the catalogue in both directions.

- **`repertoire_date_check.csv`** — each dated jubilee, farewell and memorial notice already in the
  catalogue against what the Repertoire prints that day. 58 are confirmed by an annotation naming the
  person on the same date (46 of them core ballet); the result is in the catalogue's
  `date_check` column. Where it is blank the Repertoire simply has no annotation that day
  (the early seasons annotate little), which is not a contradiction.
- **Two dates corrected from it.** Крутикова's farewell: the stored review text has 25 January 1901;
  the review page prints 23-го января (the typeface's 3 looks like a 5) and so does the Repertoire.
  Палечекъ's farewell: the review text has 14 February 1910; the Repertoire has 14 February 1911.
- **`repertoire_annotations_matched.csv`** — the 172 annotations with jubilee, farewell or memorial
  wording (Russian and French) and whether the catalogue already has the occasion. The 122 that it
  did not are added with `source_type` = `repertoire`; for these `name_verbatim` is the annotation
  itself, except on the ballet-relevant rows. New for ballet:
  **Леньяни's farewell benefit** (28 Jan 1901, «Камарго»), **Трефилова's farewell performance**
  (24 Jan 1910, «Лебединое озеро»; also in the 1909-10 season-stats notes) and the 25-year benefit
  of the Mariinsky machinist-mechanic **Н. А. Бергеръ** (27 Dec 1905) — all three read on the
  Repertoire scans. `mentions` where a ballet was on the bill: the opera singer Власовъ's farewell
  («Жизель»), the Шаховской memorial (a comedy-ballet), the Чайковскій 10-year memorial in Moscow
  («Лебединое озеро», act 3) and two institutional jubilees. The rest are drama, opera and
  French-troupe occasions, tier `none`.
- The season-statistics footnotes were checked too: they name nothing the annotations do not.
- **The 25 ballet-relevant review notices the Repertoire could not confirm by name** were then re-read
  on the review scans by a reader who was not shown the date on file
  (`first_read/review_date_recheck/`). All 25 agree. Five of them print no date for the event itself
  (Гиллертъ's death, the departures of Кякштъ, Гримальди and Кшесинская, the Grand Duchess's death);
  the catalogue already gives those as a season or a governing date.

## Other files searched

Read in full on 2026-10-12 for deaths, jubilees, farewells and commemorations
(`first_read/other_files_search/`): the Theatre School reports for every season (95 pages), the two
reports of the Society of Russian Dramatic Writers and Opera Composers, Bessel's memoir of
Tchaikovsky (1896-97, Supplement 1) and Карнѣевъ's «Двѣ забытыя русскія танцовщицы» (1909, issue IV).
The school reports are statistics and graduate lists and carry no such notices; the only deaths are
daggers on Theatre-Literary Committee pages filed with them (Григоровичъ and Стороженко, already in
the catalogue from the rosters, and Кирпичниковъ, added). The Society reports print no list of dead
members. Three stand-alone pieces were added as `biographical_feature` (`first_read/K_other_files.csv`):
Карнѣевъ's sketches of Н. К. Богданова and Е. И. Андреянова (`core`; a historical article marking no
anniversary) and Bessel's memoir (`mentions`; it never names a ballet).

## Review death lists

`review_deaths_matched.csv` (from `build/match_review_deaths.py`) pairs the 53 names in the Season
Reviews' "Умерли: …" lists with the obituaries. 43 have an obituary in the catalogue; 6 fall in seasons
with no scanned obituary section and are confirmed as ballet artists from the rosters (Разуевъ,
Троицкая, Ахмакова, Литавкинъ С. С., Дмитріевъ М. А., Гиллертъ); 2 are in no roster (Кондараки,
Анненкова); 2 are Imperial family deaths. Every name the first pass called ballet only from its
position in a ballet review is now confirmed.

Three places where the review and the obituary disagree in print, each read on both scans:
Смирнова (review and rosters Е. К. / Евгенія Кирилловна, obituary «Евгенія Дмитріевна»),
Никитинъ (review 24 July 1896, obituary 23 July), Казаковъ (review 16 Sept 1892, obituary 17 Sept).
A fourth, Пуни, was not a conflict: the review page prints «Н. Ц. Пуни», as the obituary and rosters do;
«Н. П.» was a misread in the stored review text.

## Reading notes in Obsidian (Russian and English)

`build/build_obsidian_notes.py` writes one note for every ballet-relevant entry (`core` or `mentions`)
that has a full text: 79 obituaries, 27 jubilees and 12 articles and memorials, 118 notes. One-line
notices from the reviews, rosters and Repertoire get no note. The notes live in the Obsidian vault under
`Jubilees and obituaries/`, with an index note listing them by season.

**They are for reading, not citing.** The Russian is a single machine reading of each page
(`pipeline/run_reviews.py`, 220 pages, not checked against the scans) and the English is a machine
translation of it (`pipeline/translate_reviews.py`). Quote from the scan.

Each note carries the catalogue's fields as properties, the text as a two-column table
(Русскій | English), the catalogue's print conflicts and corrections where there are any, the person's
other notices, and a `## My notes` section. Everything under `## My notes` is kept on every rebuild;
the rest is regenerated, so do not edit it by hand. To rebuild (steps in the script's header):
`--segment`, then the translator (it only translates new blocks), then `--build --vault <folder>`.
If `--segment` changes how an entry is cut, its block numbers shift: delete that entry's rows from
`outputs/jubilees_obituaries/translations.csv` before translating again.

## Links to the people in the database (2026-10-22)

`jubilees_obituaries_person_links.csv` gives every person entry a `research.person` record (`person_id`), or
says there is none. It is keyed by `entry_id`, the same id the Obsidian notes carry. Made by
`build/link_persons.py`, which reads the production database without changing it:

- **Automatic** (274 links): a roster death mark goes to its own roster entry. A review notice goes to the
  person the review-mention layer already links in that block, if the surname agrees. Any other entry is
  linked only when exactly one record agrees on the surname and on every name or initial printed. Spellings
  are compared with ѣ/і/ѳ/ъ folded, for matching only. The match is refused if a record still appears on
  the rosters more than a season after the death, or if the ordinals disagree.
- **Read by Claude** (106 cases in `build/person_link_decisions.csv`, each with its basis): every entry with
  several candidates or a near-miss name. These were decided from the catalogue's role, city and dates against
  each record's roster span; no scan was read for this step. 42 were linked and 64 have no record.
- **No record** (339 of the 655): mostly drama and opera people, whom the rosters do not list, and people who
  died or retired before 1890-91. Among the ballet-relevant entries, 47 of 266 have no record.
- **А. А. Богдановъ** (obituary, 1907-08): linked by RG's decision (2026-10-22) to the production-list credit
  «Богдановъ, А. Н.» (Moscow, 1890-91). The initials conflict on the scans, so the case is also entry 42 in
  `docs/eval/uncertain_person_identities.md`.

Coverage: 219 of the 266 core and mentions entries are linked (182 of 212 core). In all, 316 entries
point to 274 people. As a check, no linked person has deaths in seasons more than two apart, or a jubilee or
farewell after a death. Name variants were linked where the person is plainly the same one: Осипъ/Іосифъ,
Левъ/Леопольдъ Ауэръ, German names against the rosters' Russian forms (Брауэръ, Рамзе, Шварцъ). A
patronymic conflict is noted in `basis`: Смирнова (already above), Корсакъ, Бекке. Things this found that
belong to other layers are in `FOR_MAIN_THREAD.md`.

The links are decisions and can be revised: change a row in `build/person_link_decisions.csv` and re-run.
`person_id`s follow production, and the script follows merges (`superseded_by_person_id`). If people are merged
or split later, re-run it.

## Loading into the database (2026-10-22, tested on a copy only)

`build/load_jubilees_obituaries.py --db <file>` writes three tables:

| Table | Rows | What |
|---|---|---|
| `raw.jubilee_obituary_entry` | 702 | The catalogue verbatim, plus `entry_id` and `catalogue_row`. |
| `entities.jubilee_obituary_person_link` | 655 | The person links and their basis, from `jubilees_obituaries_person_links.csv`. |
| `research.jubilee_obituary` | 702 | The queryable table. `person_id` points to `research.person` and follows later merges; `is_person` and `link_status` are included. |

It has **not** been run on production. The script refuses any path under `outputs/full_run`, and the pipeline
does not call it. It was tested on a copy of production on 2026-10-22, with these results:
- All integrity checks pass, and 316 links point to 274 people.
- A second run gives the same result.
- `pipeline/build_research_model.py` rebuilds the research layer on the copy without error, and no link is left
  pointing at a missing person afterwards.

`person_id` is a plain column with no declared foreign key. `build_research_model.py` drops and recreates
`research.person`, and a declared key would block that. The loader checks every id itself instead.

What happens next is up to RG:
- **Before running it on production**, re-run `build/link_persons.py`, after the main thread's person merges.
- **Wiring it into the build** means calling it after `build_research_model.py`. Adding it to
  `build_datasette.py`'s `TABLES` would also put it in the published sqlite, which Andy republishes.

## Not yet done

- The supplements have not been checked for obituaries (deferred; see `unscanned_worth_getting.md`).
- Coverage is limited to what was scanned: e.g. 1894-95 jubilee pp. 333-367 and
  1907-08 obituary pp. 287-291 are not in the scans.
