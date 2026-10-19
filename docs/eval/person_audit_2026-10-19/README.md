# M8 and M9 regenerated -- 2026-10-19

The two broad worklists from the 2026-10-12 person audit (`../person_audit_2026-10-12/`), which were never triaged,
regenerated against current production (live persons 2548; receipts 3,216,919,085; Wikidata 177), after the 2026-10-15
queue merges/splits, Мосолова/Поливановъ, issue #154 (216 misplaced ordinals) and the 761 restored dropped ordinals.
Same code: `../person_audit_2026-10-12/audit.py`, run with its output directory pointed at a scratch folder; only M8 and M9
were kept. Read-only; nothing merged, split or corrected. A signal is a WORKLIST, never a rule.

- `M8_first_start_date_varies.csv` -- 379 rows (was 380). Within one list, a person's first printed start date is not
  always the same. 251 "different years", 128 "same year". By list: BalletArtists 159, Musicians 100, ProductionTeam 45,
  TheaterSchoolStaff 38, Administrators 37.
- `M9_listed_after_leaving_or_death.csv` -- 197 rows (was 194). An entry prints «Оставилъ службу ...» or «† ...», but the
  person is still in later seasons of the same list. 179 left service, 18 died. By list: BalletArtists 66, Musicians 55,
  TheaterSchoolStaff 35, Administrators 23, ProductionTeam 18.

Against 2026-10-12 (compared by surname + first name + list, since ids and display names moved with the merges and the
restored ordinals): most differences are the same people under a new display name (e.g. «Бакинъ 2-й», «Брыкинъ 2-й») or a
longer span. Really gone from M8: Гердтъ, Павелъ (1860 x20 / 1866 x1), Чумакова, Ольга (Graduates; the two 1893/1894 women,
split 2026-10-12). Really new in M9: Адольфи 1-й, Іоганъ-Фридрихъ (left 1 Jan 1897, listed 1897-98..1899-00); Штейнсъ, Іосифъ
(note 1 Sept 1896, listed to 1910-11 -- the printed transfer between two Petersburg orchestras, see the 2026-10-12 README);
Ѳедорова, Софія (note 15 Aug 1909, listed 1910-11).

Not yet done: the automatic first pass (M8: one odd date inside a run vs a run that splits into two consistent dates;
M9: a return after a gap vs continuous listing after the note), then scan checks, then cases to RG one at a time.

## Automatic first pass (2026-10-19)
`first_pass.py` -> `M8_first_pass.csv`, `M9_first_pass.csv` (bucket rules in the script's docstring). Read-only. M9 counts
each leaving/death note once per person and list (134 notes = the 197 note-season rows of M9).

| M8 bucket (379) | rows | reading |
|---|---|---|
| odd_single_date | 140 (100 differ only in the day or one year digit) | one season's date disagrees with all the rest: a slip in that season |
| clean_split_near | 67 | two blocks, dates differ only in day/month or one digit: the print changed its date from that season on |
| clean_split_1908_format | 30 | two blocks, the second starting 1908-09 or 1909-10 |
| same_season_two | 27 | two dates in one season (two posts / two rows), otherwise consistent |
| **clean_split** | **21** | two blocks with a real jump, not at 1908: post change, re-engagement, or two people |
| **scattered** | **94** (70 different years, 24 same year) | no simple pattern |

The 1908 re-basing is in the data: between consecutive seasons, the number of people (same list) whose printed start YEAR
changes peaks at 1907-08 -> 1908-09 for BalletArtists (40, against 0-22 at every other step) and is raised for ProductionTeam
and Administrators in 1908-10; a smaller peak at 1890-91 -> 1891-92 (BalletArtists 15, Musicians 16).

| M9 bucket (134 notes) | notes | reading |
|---|---|---|
| note_reprinted | 59 (8 deaths) | every later listing repeats the note: the volume prints people who left during the season |
| reengaged | 30 | a later listing prints a start date after the leaving date: returned to service |
| left_one_of_two_posts | 5 | the note closes one of two posts in the same list (e.g. Каменевъ, Исторія церкви vs Законъ Божій) |
| note_printed_late | 2 (both deaths) | listed one more season without the note, which appears a volume later (Байкова, Краюшкинъ) |
| **continuous_after** | **36** | listed straight after with no note and no new start date |
| **return_after_gap** | **2** | listed again after a missing season (Адольфи, Фердинандъ; Егорова 1-я) |

**Left for scan checks: 153** -- M8 clean_split 21 + scattered 94, M9 continuous_after 36 + return_after_gap 2. The other
buckets are explained by the print's own habits; a sample of each should still be scan-checked before they are set aside.

## Scan checks of the 38 M9 notes -- PAUSED 2026-10-19 (RG)
Verdicts in `M9_scan_checks.csv`, evidence in docs/query_log.md (2026-10-19 "M9 scan checks"). Done: case 1 Іогансонъ (explained:
left teaching, then honorary member), case 2 Адамовъ (unconfirmed printed leaving, no change), cases 3 + 37 the Адольфи brothers (both
1897 notes unconfirmed, left as printed, uncertain list #38). **Resume at case 4, Баклановъ, Петръ Михайловичъ**: his 1907-08 «Оставилъ
службу 1 августа 1908 г.» is printed (seen at page size) and he is listed 1908-09..1910-11; still to zoom, read 1908-09, look for a
return note, and put it to RG. Cases 5-36 and 38 not started (working order = the list in M9_first_pass.csv, buckets
continuous_after then return_after_gap). 13 of the 38 have their later rows under a different heading (mostly promotions).
