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
