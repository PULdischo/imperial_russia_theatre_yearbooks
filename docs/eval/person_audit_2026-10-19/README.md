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

### 2026-10-19 (later): groups, scan reads, fixes applied
The 34 notes left were grouped (`M9_groups.csv`). All of group 1 and group 2 were read on the scans, zoomed, before any change
(query log 2026-10-19). Applied with RG's approval, one rebuild (`rebuild_after_raw_edit.sh`), backup
`outputs/full_run_pre_promote_backup_2026-10-19_post_change_end_type/`:
- `docs/eval/raw_fix_post_change_end_type_2026-10-19.py`: 28 service periods closed by «назначенъ / переведенъ / освобожденъ»
  re-marked left service -> other.
- `docs/eval/raw_fix_m9_misattributed_and_spellings_2026-10-19.py`: Иванова 1902-03 and Неменскій 1904-05 lose a leaving note that is
  printed under their neighbour (Офицерова, Каффи); misreads to the print: «Жвирблисъ», «Мололова» (print slip for Мосолова), «1 декабря»,
  «Московскимъ» x2, «Гельцеръ», «О-Іоши».
Result: left service 983 -> 953, other 127 -> 155; receipts, live persons 2548, Wikidata 177, research.person 2646, works and every
person_link unchanged; 0 shift blocks.
**Still open:** group 2's remaining notes (Потанинъ, Тарновскій, Ѳедорова 1-я, Ѳедорова 2-я Софія, Егорова 1-я) await RG's verdict
(printed and confirmed; unconfirmed leaving or return); group 3 (9) and group 4 (Баклановъ, Ѳедорова 2-я Лидія x2). Seen, not checked:
productionteam_1902-03_p001 entry 20, «1. Каффи ... Оставилъ службу 1 августа 1903 г.» (same page as Иванова, under «Костюмеры»).

### PAUSED 2026-10-19 (RG: "come to a pause point")
Group 2 done: Иванова and Неменскій fixed (misattributed notes); Потанинъ, Тарновскій, Ѳедорова 1-я, Софія Ѳедорова -> continuing
service, Егорова 1-я -> two periods (possibly never left), all in `research.person_tenure_note` (new research table; source
`pipeline/research_corrections/person_tenure_discrepancies.csv`; uncertain list #39). **Resume with group 3** (9 notes, M9_groups.csv:
one more season only), then group 4 (Баклановъ, Ѳедорова 2-я Лидія x2). Open side items: Адамовъ and the Адольфи brothers could join the
tenure table (RG to say); productionteam_1902-03_p001 «1. Каффи ... Оставилъ службу 1 августа 1903 г.» unchecked; the new table is not
yet in the Datasette export.

### M9 scan checks DONE 2026-10-19
All 38 notes decided. research.person_tenure_note now holds 19 people (source pipeline/research_corrections/person_tenure_discrepancies.csv;
uncertain list #39 summarises): group 2 (5), Адамовъ, the Адольфи brothers, group 3 (9), group 4 (Баклановъ, Лидія Ѳедорова). Raw fixes on
the way: 28 post-change end types, 3 misattributed leaving notes (Иванова, Неменскій, Каффи), several misreads. Каффи Иванъ/Дмитрій kept
apart (#40). Left for later: M8 (115 rows to scan-check after the first pass); the 10 other «перемоніймейстеръ» entries; the 913 rows
whose credit line is duplicated inside the tenure note; the new table in the Datasette export (Andy).

## PAUSED 2026-10-19 (end of day) -- where to resume
Done today: M8/M9 regenerated and auto-sorted; all 38 M9 notes decided (research.person_tenure_note, 19 people); 28 post-change end
types; 3 misattributed leaving notes (Иванова, Неменскій, Каффи Иванъ); Каффи Иванъ/Дмитрій kept apart (#40); 913 duplicated ballet
tallies removed from tenure notes; «церемоніймейстеръ» on 10 entries; 39 tally misreads on 7 entries (Щелкунчикъ, Коппелія, Конекъ-Горбунокъ ...).
**Resume options, in RG's order of interest:**
1. M8: 115 rows left after the first pass (`M8_first_pass.csv`: clean_split 21, scattered 94) -- group by pattern first, as for M9.
2. ~52 other misspelled credit titles corpus-wide (raw.person_entry_credit.label: «Копекъ-…» 39, «Копелія» 8, «Копеллія» 3, «Копелкъ-горбунокъ»
   2) -- scan-check each; «Копелія» may be a genuine print variant.
3. Proposed separate task: review mentions linked across different ordinals (e.g. «Смирнова 2-я» -> Смирнова 4-я) -- read-only check.
4. For Andy: research.person_tenure_note is not yet in build_datasette.py; research_dataset.sqlite last built 2026-10-15.

## M8 group 5: the 21 unexplained print variations (2026-10-30)

RG 2026-10-30: "labels only". No per-person note: each of the 21 is recorded by its row in `research.person_tenure` (the chosen
date, the `basis` label and every printed date with its seasons). Still to decide: which date wins when a run's date changed once
(refresh-year flag), Гуняшевъ's neighbour slip, Мацкевичъ's 1909-10 «7 іюня 1903».
