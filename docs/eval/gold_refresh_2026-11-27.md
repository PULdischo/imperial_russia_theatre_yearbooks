# Roster gold refresh, 2026-11-27

Goal: bring `docs/eval/gold/_build_roster.py` up to date so `eval_against_gold.py`
works as a regression check again. Before: roster 76.4% (949/1,242 fields) on
`outputs/full_run/parsed`. After: **97.3% (1,418/1,458)**. Repertoire unchanged at 97.8%.

All scan reads are by Claude, from `docs/eval/gold/images/` (checked by Claude, not RG).

## Rulings

- **Tenure notes (RG, option C):** the gold holds the whole printed note after the name,
  brackets included («(съ 1 сентября 1889 г.). Первая скрипка.»). The scorer compares
  tenure notes without brackets and stops (`norm_tenure`), and reports the run's count of
  notes with a closing bracket but no opening one separately (2,435 now).
- **Heading end punctuation (Claude, by the same reasoning, for RG to confirm):** the
  scorer compares heading segments without a printed end colon or stop (`norm_heading`).
  The stored rows keep them on BalletArtists and Musicians and not on TheaterSchoolStaff.

## What changed in the gold

- Conventions ruled after the gold was made: #137 office roots on Administrators headings,
  the school and ProductionTeam roots, `service_class` without the final stop.
- Gold transcription errors fixed (the print agrees with the data): «Владимиръ» (Теляковскій,
  Кусовъ 1907-08); Аршеневскій 1890-91 «1889», not «1839»; «Вильеръ - де-Лиль - Адамъ»
  printed with spaced hyphens in 1890-91; «И. д.» spacing; Журналистъ sits in the
  Распорядительное отдѣленіе (column break); Шенкъ's «Завѣдывающій центральною
  библіотекою.» is a note under his entry, not a heading; Алексѣева 2-я's printed
  «† 25 мая 1891 г.» added; tenure notes now carry the printed instrument (Musicians) and
  second lines.
- Partial pages completed: musicians_1890-91_SP now has all 37 entries (was 14);
  theaterschoolstaff_1906-07 gains Абрамова («И. д. фельдшерицы»).

## The 40 remaining mismatches are data errors (NOT fixed; for RG)

1. **FIXED 2026-11-27 (RG "yes, promote both").** **Musicians 1890-91 SP:** «Капельмейстеръ
   военной музыки» (Оглоблинъ) and all 31 «Музыканты» are printed under «Оперный оркестръ»,
   but stored without it (Направникъ and Кучера have it). 32 fields. The opera list runs on
   through p001 (Nos. 32-74) and p002 (Nos. 75-103, then «Балетный оркестръ»), and RG's
   2026-10-02 rule makes continuation pages follow p000, so all 104 rows were changed
   (`docs/eval/fix_musicians_1890-91_opera_heading_2026-11-27.py`, heading_path only).
   Tested on a copy of production; production = tested copy; against the backup
   (`outputs/backups/musicians_1890-91_opera_heading_2026-11-27/`) only those 104 rows differ in
   raw/analysis.person_entry and research.person_appearance; review links unchanged (20,194),
   0 shift blocks. Roster gold 97.3 -> 99.5. Sqlite not rebuilt (Andy). Not checked: other SP
   seasons store the opera musicians as bare «Музыканты» too; whether their scans print
   «Оперный оркестръ» above them is open. Also seen on p002: the 12 ballet-orchestra rows have
   institution «Императорское С.-Петербургское Театральное Училище» (series uses «Оркестры.»).
2. **Administrators 1907-08:** «баронъ» (Кусовъ) and «графъ» (Бергъ) are missing from
   rank_or_title. The same two rows are also missing them in 1906-07; every other season has
   «баронъ, …» / «графъ, …» (the #137 convention).
3. **Administrators 1907-08:** the printed heading «Помощники дѣлопроизводителя:» is missing
   for Посниковъ and Шенкъ.
4. **Administrators 1890-91:** the printed heading «Полиціймейстеры:» is missing for
   Старженецкій-Лаппа and Клечковскій.
5. **TheaterSchoolStaff 1906-07:** Боборыкинъ has the stored note «съ 1 сентября 1903 г.»;
   nothing is printed after his name (that is Смирновъ's date).
6. **TheaterSchoolStaff 1906-07:** Абрамова is stored under «Лекарскій помощникъ /
   И. д. фельдшерицы»; the print sets «И. д. фельдшерицы.» as its own heading at the same
   level. Structure question rather than a clear error.

Also seen, not scored: 2,435 tenure notes have a closing bracket but no opening one.

## Uncertain in the gold

- administration_1907-08 Шарыпинъ: the only printed heading is «VIII кл.», after the
  «Помощники дѣлопроизводителя» entries; the gold puts him under «Распорядительное
  отдѣленіе» with no position, like the stored row.
- The musicians entries 12-31 were read on the scan after the stored rows had been seen.

## Follow-up: the same heading gap in other St Petersburg seasons (FIXED 2026-11-27, RG "Yes, fix all 16")

Every SP season's first scan page (1891-92 .. 1909-10; 1905-06 also p001) was read by Claude.
The print is the same throughout: «Оркестры.» > officials > «Оперный оркестръ.» (1891-93) or
«Оркестръ оперы и балета.» (1893-94 on) > capellmeisters, «Репетиторы балета», «Капельмейстеръ
военной музыки», «Музыканты» — all under the orchestra heading until the theater orchestras.
Stored rows with institution «Оркестры.»/«Оркестры» that lack the orchestra root:

| season | Музыканты | also missing the root |
|---|---|---|
| 1891-92 | 101 | Капельмейстеръ военной музыки (1) |
| 1892-93 | 99 | Капельмейстеръ военной музыки (1) |
| 1893-94 | 123 | Капельмейстеръ военной музыки (1) |
| 1894-95 | 125 | |
| 1895-96 | 121 | Капельмейстеръ военной музыки (1) |
| 1896-97 | 124 | |
| 1897-98 | 125 | |
| 1898-99 | 135 | Капельмейстеръ военной музыки (1) |
| 1899-00 | 128 | |
| 1900-01 | 141 | |
| 1901-02 | 130 | Капельмейстеръ военной музыки (1) |
| 1904-05 | 137 | |
| 1905-06 | 91 | Второй капельмейстеръ оперы, Капельмейстеръ балета, И. об. помощника капельмейстера балета, Репетиторы балета (3), Капельмейстеръ военной музыки (7 in all) |
| 1906-07 | 127 | |
| 1908-09 | 126 | |
| 1909-10 | 127 («Музыканты:») | Аккомпаніаторъ, Репетиторы балета: (3) |

About 1,977 rows in 16 seasons. Already consistent: 1902-03, 1903-04, 1907-08, 1910-11, 1911-12.
Not touched: the officials above the orchestra heading («Инспекторъ музыки», «Завѣдывающій
оркестрами», librarians) and the library rows at the end (#130's deferred library question).
1909-10 stores its root as «Оркестръ оперы и балета.» (with the stop) — a fix would follow each
series' own p000 form (#130 rule).

**Applied 2026-11-27:** `docs/eval/fix_musicians_sp_opera_heading_2026-11-27.py`, 1,977 rows on 66 pages
(per season as in the table, plus the extra rows listed), heading_path only, each season's own root.
Re-parse diff: 1,977 heading_path values, nothing else. Tested on a copy; production = tested copy;
vs backup `outputs/backups/musicians_sp_opera_heading_2026-11-27/` only raw/analysis.person_entry and
research.person_appearance differ (1,977 rows each); 0 shift blocks; review links unchanged (20,194).
No bare «Музыканты» row is left in an SP main-orchestra list. Sqlite not rebuilt (Andy). Moscow not checked.

## Follow-up: Moscow Musicians (1,109 rows FIXED 2026-11-27, RG "Yes, fix the 1,109"; the other findings below NOT fixed)

First scan page read by Claude for 1898-99 .. 1911-12 (1911-12 also p001); 1890-97 rows already
carry the root in the series' own form (#130 rule). **The print differs from St Petersburg:** the
«Оркестръ оперы и балета.» heading is printed in 1890-91 .. 1905-06 and in 1911-12, but NOT in
1906-07, 1907-08, 1908-09, 1909-10, 1910-11 («Оркестры.» > officials/capellmeisters > «Музыканты»
directly), so the bare «Музыканты» stored for those five seasons is verbatim.

Rows stored without the printed root (seasons that print it):

| season | rows | where |
|---|---|---|
| 1894-95 | 46 | p002 continuation of the musicians list (Nos. ~80-125) |
| 1896-97 | 52 | p001 «Музыканты:» (Nos. 25-76) |
| 1898-99 | 129 | Репетиторы (2), military bandmaster (1), Музыканты (126) |
| 1899-00 | 33 | p003 continuation (Nos. 100+) |
| 1900-01 | 127 | ballet capellmeister + acting 2nd (stored nested under it), Репетиторы (3), military (1), Музыканты (121) |
| 1901-02 | 89 | capellmeisters (3), Репетиторы (3), military (1), Музыканты (82) |
| 1902-03 | 130 | Репетиторы (3), military (1), Настройщикъ (1), Музыканты (125) |
| 1903-04 | 94 | military (1), Настройщикъ (1), Музыканты (92) |
| 1904-05 | 133 | Репетиторы: (3), military (1), Настройщикъ (1), Музыканты: (89) + p002 Музыканты (39) |
| 1905-06 | 140 | capellmeisters (3), Репетиторы (2), Аккомпаніаторы (2), military (1), Настройщикъ (1), Музыканты (130), «И. сб.» (1) |
| 1911-12 | 136 | Музыканты: p001-p004 (institution is the running head «МОСКОВСКІЕ ОРКЕСТРЫ.») |

About 1,109 rows. Also found, a different shape:
- headings lost or garbled on whole continuation pages: 1901-02 p002 (39 rows, no heading),
  1903-04 p002 (38 rows, no heading, invented institution «Списокъ скрипачей, альтовъ, …»),
  1896-97 p002 (49 rows, heading «Оркестръ оперы и балета. Завѣдывающій дѣлами оркестровъ и
  капельмейстеръ оперы. Музыканты:»), 1892-93 p002 (1 row «Балетный оркестръ / Музыканты / Музыканты»);
- 1890-91 p002: 2 rows «Музыканты» (Nos. 1-2), probably the first two ballet-orchestra musicians
  (not scan-checked);
- Малый-theatre orchestra rows filed under institution «Императорское С.-Петербургское Театральное
  Училище» (1894-95 6, 1896-97 3, 1899-00 5, 1905-06 15, 1907-08 12) and 1898-99 p004 (15 rows,
  Nos. 21-35, the Малый list's continuation) under «Оркестры.».

**Applied 2026-11-27:** `docs/eval/fix_musicians_msk_opera_heading_2026-11-27.py`, 1,109 rows on 36 pages
(per-season counts as in the table), heading_path only, root in each season's own p000 form
(1894-97 «Оркестръ оперы и балета. …», 1898-1906 «… / …», 1911-12 «Оркестръ оперы и балета. / …»).
1900-01's «Капельмейстеръ балета / И. об. 2-го капельмейстера балета» kept its (wrong) nesting under the
new root. Re-parse diff: 1,109 heading_path values only. Tested on a copy of production (md5 79b05203);
production = tested copy; vs backup `outputs/backups/musicians_msk_opera_heading_2026-11-27/` only
raw/analysis.person_entry and research.person_appearance differ (1,109 rows each); 0 shift blocks;
review tables identical. Sqlite not rebuilt (Andy).

**Lost/garbled Moscow headings FIXED 2026-11-27 (RG "Yes, fix those"):** `docs/eval/fix_musicians_msk_lost_headings_2026-11-27.py`,
127 rows; each page read on the scan (plain continuations, no heading or title printed).
1896-97 p002 (49) «Оркестръ оперы и балета. Музыканты:»; 1901-02 p002 (39) and 1903-04 p002 (38)
«Оркестръ оперы и балета / Музыканты», 1903-04 also institution «Оркестры» (was the invented
«Списокъ скрипачей, …»); 1892-93 p002 Альбрехтъ: stray «Музыканты:» cleared from rank_or_title, which
stops `_repair_musicians_stray_heading` doubling the segment. The 1901-02 blank came from a stale
`_HEADING_PATH_RESTORE_FIXES` entry in `pipeline/parse_and_validate.py` (removed). Production = tested
copy; vs backup `outputs/backups/musicians_msk_lost_headings_2026-11-27/` only the 127 rows differ;
0 shift blocks. Still open: 1890-91 p002 two rows, 1900-01 nesting, misfiled Малый institutions.
