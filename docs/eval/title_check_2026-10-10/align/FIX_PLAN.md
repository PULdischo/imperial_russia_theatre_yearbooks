# Column-structure read: findings and fix plan (issue #151 follow-up 15, 2026-10-11)

524 pages (every Repertoire page with a stored morning/evening split) were read blind for the structure of every cell;
134 differences against the stored data were triaged, 55 priority cells read in detail (every sub-cell's figure and lines),
and the affected columns read row by row. Scripts: `compare_structure.py`, `triage_structure.py`, `compare_detail.py`.

## What the stored data got wrong (all verified on the scan; none of it visible to the weekday or receipts-order checks)
1. **A half-performance filed under the neighbouring row.** Where a row prints a closed day (a dash) or a day whose
   evening half is a dash, the following day's morning half was stored under the earlier row: the Saturday shows a
   performance (a closure invented), the Sunday shows only its evening. 12 cells (1894-95 pair008 МАЛ 22; 1899-00 p026 АЛЕК 13;
   1900-01 p006 МАР 15 and p020 АЛЕК 31; 1903-04 p017 НОВ 14, p022 МАР 18, p025 НОВ 2; 1904-05 p010 МАР 31 and 7; 1905-06 p013
   НОВ 6, p029 НОВ 2; 1909-10 p020 БОЛ 29).
2. **A whole column one slot early** (a displaced half pushes every later cell up a row until a split absorbs it):
   1907-08 p025 МАЛ 5-13 (9 sessions), 1902-03 p018 АЛЕК 21-27 (6 sessions + 1 duplicate), 1905-06 p021 МАЛ 26-27 (2).
3. **Exact duplicates of a neighbouring cell on a dash row**: 1893-94 pair006 АЛЕК 16, pair010 АЛЕК 20, 1897-98 pair010 МАР 22.
4. **The French troupe's cell filed under Александринскій** on that column's dash row, the Михайловскій cell left empty:
   1892-93 pair012 19 Dec, pair014 9 and 16 Jan (3 sessions).
5. **One undivided printed cell stored as a morning + evening pair**: 1890-91 pair020, 1891-92 pair016, 1892-93 pair012,
   1903-04 p017, 1904-05 p022 (5 cells).
6. **Two printed halves stored as one session** (both halves' works, the evening's figure): 11 cells on 1900-01 pp. 12, 16, 17,
   26, 1902-03 pp. 14-15, 1903-04 p013.
7. **A half-performance with its own figure missing from the stored data altogether** (about 16 cells, listed below).

## Stage A (APPLIED 2026-10-11 by `apply_structure_fixes.py`; rebuilt; backup outputs/full_run_pre_promote_backup_2026-10-11_structure)
69 operations on 30 pages: 25 session relabels in group 1, 18 in group 2 (3 columns), 13 deletes of duplicates/empties,
3 theater fixes, 5 merges, 11 splits. Adds no work title or figure that is not already stored except one morning figure
(1900-01 p026 МИХ 4, «625 р. 50 к.», two readers agreed). Net sessions 13 fewer, 10 more.

## Stage B (APPLIED 2026-10-11 by `apply_dropped_halves.py`: 17 sessions, each with 2-3 agreeing reads; see known_issues #151 follow-up 16)
| cell | what the print has that the stored data lacks | reads |
|---|---|---|
| 1899-00 p014 АЛЕК 27/28 | 28 morning «Шутники, ком.» 445 р. 10 к.; the figure was attached to 27's «Женитьба Бѣлугина» (printed with no figure) | read + my own look |
| 1899-00 p024 АЛЕК 30 | evening «Накипь, ком.» 1650 р. 89 к. | agree |
| 1900-01 p016 МИХ 10 | evening «Madame Lili \| Le verre d'eau» 534 р. 50 к. | agree |
| 1900-01 p018 МИХ 17 | evening «Les brebis de Panurge \| La mégère apprivoisée» 302 р. 50 к. | agree |
| 1900-01 p027 НОВ 9 | morning «Снѣгурочка» 715 р. 70 к. | agree on figure, title spelling differs |
| 1901-02 p020 АЛЕК 30 | evening «Комета, эпизодъ» 2018 р. 98 к. | agree |
| 1901-02 p021 МАЛ 30 | evening «Нефтяной фонтанъ» 1531 р. 83 к. | agree |
| 1903-04 p006 АЛЕК 19 | evening «Пустоцвѣтъ, ком.» 1716 р. 64 к. | agree |
| 1903-04 p018 АЛЕК 26 | evening «Плоды просвѣщенія, ком.» 1806 р. 32 к. | agree |
| 1900-01 p022 АЛЕК 14 | evening «Выгодное предпріятіе» (the stored session has the morning's «Царь Борисъ» with this figure) | single |
| 1900-01 p017 МАЛ 6 | evening «Кинъ, ком.» 1166 р. 13 к. (stored has the figure under «Ромео и Джульетта») | single |
| 1900-01 p008 МИХ 29 | morning «Представленіе Сіамской Придворной труппы.» (no works, no figure) | single |
| 1897-98 pair022 МАР 22 | German troupe: morning charity performance + «3-ter Akt ... Walküre» | single |
| 1898-99 p019 НОВ 27 | evening «Риголетто» 1414 р. 39 к. | agree on figure |
| 1898-99 p014 АЛЕК 29/30 | 29 evening «Наталья Борисовна Шереметева \| Воробышекъ» 1438 р. 71 к. is stored under 30; 30's own cell not located | needs column read |
| 1893-94 pair018 АЛЕК 13 | evening half partly hidden at the fold | single |
| 1900-01 p010 АЛЕК 5 | morning jubilee repeat 274 р. 34 к. vs «Накипь» 1632 р. 96 к. | reads disagree |

## Dismissed
* 1890-91 pair024 (ALX/MIH/MAR/BOL/MAL, "30" and "6" occur in two months: label collision, stored dates are right) and 1908-09 p001 МАР 5 (reader error).
* 54 closure days stored as a morning+evening pair of empty sessions where print has one dash (1906-07 pp. 34-35 and others): harmless, tidy-up only.
* 25 print-split cells with one half a dash stored as one unspecified session: time-of-day precision only.
* 1910-11 p009 МИХ 9/10 Nov: the print itself repeats 1006 р. 75 к.
