# Person field audit — 2026-11-01 (PAUSED for usage limits)

RG asked for a field-level audit of every person (all roster lists, ballet-production-list creators, review people and
credits, jubilee/obituary links, Wikidata): anything parsed wrongly, in the wrong field, missing or wrong. Then (same day):
"we never really audited leaving dates, moving dates, and death notices" -> leaving/transfer/death audit added.
Scope rulings: flags only (no full re-read); raw rows get field-placement fixes (RG approves each); coverage incl. review,
jubilee links, Wikidata. **Nothing in the database has been changed.** All scan readings are "checked by Claude".

## Files
- `audit.py` (checks -> R1..R8, P1..P3, C1, V1, V2, J1, W0/W1 CSVs), `build_worklist.py` -> `scan_worklist.csv` (1,565 flags)
- `build_r9.py` -> `r9_worklist.csv` (776 last listings with no end), `build_dates.py` -> `d1_worklist.csv` (1,565 stored ends),
  `d2_worklist.csv` (106 pre-gap listings), `d3_deaths.py` -> `D3_deaths.csv` (done, no scans)
- Reader briefs: `READER_BRIEF.md`, `READER_BRIEF_R9.md`, `READER_BRIEF_DATES.md`; `render.py` (uses `page_map.csv`, no DB needed)
- Readings: `slices/<slice>_results.csv`; `own_checks.md` (main-session checks)

## Progress when paused (rows read / total)
Flags: slice1 203/203, slice2 117/204, slice3 150/206, slice4 197/197, slice5 199/206, slice6 205/205, slice7 196/196, slice8 148/148
-> 1,415/1,565. R9: 49/159, 47/158, 102/153, 72/159, 57/147 -> 327/776. D1: 14/262, 5/260, 0 x4 -> 19/1,565. D2: 0/106.
**Resume:** for each slice, re-launch a reader with the same brief, telling it to skip items already in its results CSV.

## Main findings so far (checked by Claude; for RG's rulings, one at a time)
1. **Dropped leaving/transfer/death lines** — biggest. BalletArtists print them after the tally; often dropped entirely or stored in
   credit_summary_text with no end date (e.g. Бачуринъ 1897-98, Громова 1890-91, Корсакъ † 19.2.1896, Борегаръ 1892 ProductionTeam).
   Last listings with no end and no text: BalletArtists 288, Musicians 185, TSS 102, Admin 96, ProdTeam 64 (R9 measures the share).
2. **Systematic field splits**: Moscow Musicians «Name Patronymic» in first_name (~141-160 rows, 7 pages); Graduates «Surname, Name.»
   in family_name (~79 rows; whole of 1891-92 p000). Double given names stored as patronymic (Лидтке, Больмъ, Ваксманъ, Пуни) = convention Q.
3. **Wrong-column / garbage**: dates in rank_or_title (Admin 1901-02, 1909-10); instruments in rank/subject_taught or unfilled because
   print misspelt them; tallies duplicated into tenure notes (with wrong numbers); invented note (Гельцеръ 1909-10); encoding junk
   (Кустереръ «ү», Бочкина Arabic letters, «Александрă»); «Все—10—» for «Всего» (1890-91 MSK p001/p006); duplicated leaving notes (1910-11 MSK).
4. **Misreads** (dozens): к->н surnames (Ахмакова, Какорина, Кускова, Облакова, Франкъ, Корсакъ), Подруцкая, Іогансонъ, Тривчикъ,
   Алексѣева, Армсгеймеръ, Чернявская, Шеншинъ, Марковская; instruments (Тесситоре Гобой, Котрбанъ Вальдгорнъ); tally titles.
5. **Parse errors in dates**: wrong end_type (Бѣлова died -> left service); transfer-in stored as end (Адамовъ, Келеръ); death date
   copied into start (Стороженко); comma-shifted service row (Храписъ 1910-11); secondment end as service end (Дума); print-typo
   years (Корниловъ 1998, Степановъ 1802); unparsed print-typo months (вктября, севтября...). Convention Qs: year-only dates; transfers.
6. **1908-09 BalletArtists tallies** (new format) produced no credit rows at all.
7. **Wikidata**: Кунстъ, Фричъ, Шмидтъ 1-й wrong; Шмидтъ 2-й doubtful.
8. **Review credits**: wrong links (Богданова debut -> Богдановъ; Павлова costumes -> Павловъ; О. Николаева -> machinist; Вагнеръ 1849);
   non-credits stored as credits (1465, 1466, 1472); unresolved ones with clear people (А. Герберъ, Пономаревъ, Петипа, Н. Г. Легатъ).
   Parser faults: «Г.» honorific as initial; dropped initial when no stop; role attached to next name.
9. **Identity / merge candidates** (to person_merge_candidates_batch.md): Шиманъ (prod. list «Г. Шимана» = М. В. Шиманъ?), Золотаренко
   П. П. (= Петръ Петровичъ, † 1895?), Арендсъ Генрихъ/Андрей, Петипа Марія (1910-11), Каменскій Исаакъ = Неменскій; print-slip surnames
   Поповъ/Пановъ, Романовъ/Рахмановъ 2-й, Куришенская.
10. **Deaths (D3)**: 166 agree; 37 catalogue deaths with no stored death (~10 died in their last listed season: «†» likely dropped).
11. **Noise**: R7 «no tally» and R6 numbering flags are almost all the print's own (no dropped entries found by R6).

**Coordination:** a parallel session rebuilt production (build_entities.py) during the reads and committed this folder (66e07b4).
Before applying any fix, check what changed in production since and merge field-level (memory: promotion race).
