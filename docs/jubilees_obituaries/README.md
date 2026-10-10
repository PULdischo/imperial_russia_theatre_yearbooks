# Jubilees and obituaries in the Yearbooks

Every jubilee notice and obituary in the scanned jubilee/obituary sections of the
*Ежегодникъ Императорскихъ театровъ* (Yearbook Scans - Originals), 1890-91 to 1910-11,
with the ballet-relevant ones pulled out.

## Files

| File | What it is |
|---|---|
| `catalogue.csv` | Every entry: 353 person entries from the scanned sections and stand-alone articles (`source_type` = `section`), 71 notices from the Season Reviews (`review`), 101 roster-only death marks (`roster`), plus 28 section-heading and other-article rows. |
| `ballet_entries.csv` | The subset with `relevance` = `core` or `mentions`. |
| `unscanned_worth_getting.md` | Jubilee, obituary and memorial items the Yearbooks contain that are not in the scans, ranked. |
| `AUDIT_2026-10-10.md` | What has been verified, how far, and the known gaps. |
| `roster_deaths_matched.csv` | Every roster death mark and whether the catalogue has the person. |
| `review_deaths_matched.csv` | The reviews' death lists paired with obituaries and rosters. |
| `first_read/` | The per-section first readings (A–H), the Season Review notices (`R_reviews.csv`), the contents-page listings (`T1`, `T2`) and the reader briefs. |
| `blind_second_read/` | An independent second reading of every heading name and date (V1–V5). |
| `build/` | `compare_readings.py` (first vs second read → `reading_comparison.csv`) and `build_catalogue.py` (writes the two CSVs above). |

## Stand-alone articles on one person

Six scanned articles are not under a «Юбилеи» or «Некрологи» heading in the Yearbook but share the
form (portrait flanked by the years or «XXV», service record, roles): Іогансонъ (1891-92), Камышевъ
(1892-93), Манохинъ (1895-96), Петипа (1896-97) — each written for a jubilee — and Всеволожской
(1899-00, a sketch of his work as a designer) and Волконскій (1901-02, on his leaving the
directorship). They are in the catalogue with `kind` = `biographical_feature`; the occasion is in
`notes`. Read once (`first_read/J_features.csv`), with no blind second read.

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

Not second-read: roles, evidence quotes, and the `none` verdicts themselves.

## Notices from the Season Reviews

The reviews report jubilee benefits, farewell performances and memorial performances that often have
no article of their own. These are in `catalogue.csv` with `source_type` = `review`: `source_file` is
the review `page_id`, `pdf_page` the block number, `printed_page` the review page's printed folio.
`name_verbatim` is the name as printed, usually in an oblique case; the nominative is in `notes`.
Kinds: `jubilee`, `farewell`, `memorial_feature`, and `death_notice` for death-list names that have
no obituary in the scanned sections. Death-list names that do have an obituary are not repeated.
These rows rest on the database's existing review transcription and were read once.

`see_also` lists other entries that look like the same person (same surname and matching initials),
e.g. a jubilee notice in a review and the obituary years later. It is a pointer, not an identity claim.

## Death marks in the rosters

The printed rosters mark a death with a dagger and date («† 4 іюня 1891 г.»). `roster_deaths_matched.csv`
(from `build/match_roster_deaths.py`) checks all 192 such rows — 170 people — against the catalogue:
71 rows match an obituary or death notice, 121 rows (101 people) do not, almost all in seasons whose
volumes print no obituaries. Those 101 are in `catalogue.csv` as `kind` = `death_mark`,
`source_type` = `roster`, with the name and date as stored in the database (not re-read here).

Their tier comes from the roster section: ballet troupe, dance teachers, designers and machinists,
and the ballet or opera-and-ballet orchestra are `core`; doctors, clerks, drama-course teachers and
the drama-theatre orchestras are `none`; the rest are `undecided` (44: orchestra players whose
orchestra the roster data does not state, non-dance staff of the school, wardrobe and lighting
staff). `ballet_entries.csv` includes the undecided rows.

Printed date conflicts found, each read on the scans on both sides:
Соловьевъ (roster † 4 октября 1890, obituary 9 октября); Мейеръ (roster † 28 марта 1893, obituary
25-го марта, twice); Всеволожскій (roster † 28 октября 1909, obituary † 29 октября);
Константиновъ П. А. (ballet roster † 25 декабря 1906, orchestra roster † 27 декабря, same volume).
The roster also supplies the year the obituary omits for Шенекерль (9 декабря 1895).

## Review death lists

`review_deaths_matched.csv` (from `build/match_review_deaths.py`) pairs the 53 names in the Season
Reviews' "Умерли: …" lists with the obituaries. 43 have an obituary in the catalogue; 6 fall in seasons
with no scanned obituary section and are confirmed as ballet artists from the rosters (Разуевъ,
Троицкая, Ахмакова, Литавкинъ С. С., Дмитріевъ М. А., Гиллертъ); 2 are in no roster (Кондараки,
Анненкова); 2 are Imperial family deaths. Every name the first pass called ballet only from its
position in a ballet review is now confirmed.

Four places where the review and the obituary disagree in print:
Смирнова (review and rosters Е. К. / Евгенія Кирилловна, obituary «Евгенія Дмитріевна»),
Пуни (review «Н. П.», obituary and rosters Николай Цезаревичъ),
Никитинъ (review 24 July 1896, obituary 23 July), Казаковъ (review 16 Sept 1892, obituary 17 Sept).

## Not yet done

- The supplements have not been checked for obituaries (deferred; see `unscanned_worth_getting.md`).
- Coverage is limited to what was scanned: e.g. 1894-95 jubilee pp. 333-367 and
  1907-08 obituary pp. 287-291 are not in the scans.
