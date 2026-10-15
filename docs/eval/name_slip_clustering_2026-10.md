# Do scribal-looking name slips cluster? — 2026-10-15

Read-only analysis for RG. Nothing was edited, merged or corrected. Scripts and the full variant list:
`docs/eval/name_slip_clustering_2026-10/` (`substantive_variants.csv`, 724 rows). Query log: `docs/query_log.md`, 2026-10-15 entries.

## Short answer

**Yes, they cluster — by list and by period, and they run in people, but the data cannot yet say how much of that is the 1890s
hand-copying and how much is extraction noise.** What is solid, from the database as it stands:

- **By list: Ballet is the heavy one.** 50 substantive changes per 1,000 re-listed entries in BalletArtists, 29 in Musicians,
  14–18 in ProductionTeam / Administrators / TheaterSchoolStaff (chi-square vs. even spread: 148 on 5 df; not chance).
- **By season: rising, not flat.** ~15 per 1,000 in 1891-92..1894-95, ~25–35 in 1895-96..1903-04, ~45–55 from 1904-05, peak 79 in
  1908-09 (chi-square 168 on 20 df). The rise is concentrated in **Musicians from 1905-06** (48→78→56→123→48→79 per 1,000)
  and in the 1908-09 volume generally.
- **By volume/page: yes.** Per list × season × city volume, chi-square is 489 on 139 df. Pages carrying ≥4 changes: 30 observed vs 14 expected
  by chance; ≥5: 13 vs 3. The top 10% of pages hold 41% of all changes. Worst volumes: musicians 1908-09 MSK/SP, productionteam 1908-09,
  balletartists 1908-09 MSK (all ~120 per 1,000), balletartists 1904-05 SP (106), musicians 1906-07 MSK (104).
- **By person: very strongly.** 341 people carry all 724 changes; 68 people carry 304 of them (≥3 each); 164 people show a
  reversal (A→B→A), i.e. the same two spellings alternate. This is the signature of per-page reading/typesetting noise on a hard surname,
  not of one copying slip that then persisted.
- **By city:** no clear difference. Moscow 305 / SP 314 changes where a city is recorded; Moscow Ballet 213 on 4,100 entries (52 per 1,000)
  vs SP Ballet 198 on 4,659 (42); Musicians Moscow 92 on 3,363 (27) vs SP 116 on 4,533 (26).

## What was counted

Population: 2,559 live `entities.person` (superseded IS NULL); 23,979 entries; 2,307 people with 2+ seasons. For each person, consecutive
distinct (season, surname, first name, patronymic) tuples from `analysis.person_entry` clean columns: 20,515 transitions. Classes:

| class | n | note |
|---|---|---|
| identical | 16,824 | |
| orthographic only (ѣ/е, і/и, ѳ/ф, ъ/ь, -ія/-ья, doubled letter, parenthetical, ordinal-formatting) | ~2,070 | not counted below |
| a patronymic/first name present on one side only | ~895 | listed, not counted; mostly the patronymic being supplied in a later volume |
| **substantive: 1–2 letters differ** | 653 | surname 443, first name 106, patronymic 96 (+ multi-field) |
| **substantive: different name** | 71 | patronymic 36, first name 20, surname 11, multi-field 12 (includes bracketed maiden names such as «Эльпе (Петропавловская)») |

Rates use "re-listed entries" (the entry belongs to a person who already appeared in an earlier season) as the exposure, because the
first volume (1890-91) can show no change at all. 48 of the 724 are same-season comparisons across two lists
(mostly TheaterSchoolStaff vs BalletArtists, e.g. Чекетти Генрихъ/Энрико).

## Substantive changes by season × list (counted at the later season)

| Season | Ballet | Musicians | ProdTeam | Admin | SchoolStaff | Grad | All | per 1,000 re-listed |
|---|---|---|---|---|---|---|---|---|
| 1891-92 | 6 | 6 | 3 | 0 | 2 | 0 | 17 | 15 |
| 1892-93 | 11 | 4 | 1 | 0 | 1 | 0 | 17 | 15 |
| 1893-94 | 14 | 1 | 0 | 1 | 4 | 0 | 20 | 19 |
| 1894-95 | 15 | 2 | 0 | 0 | 2 | 0 | 19 | 17 |
| 1895-96 | 14 | 4 | 1 | 3 | 3 | 1 | 26 | 24 |
| 1896-97 | 22 | 3 | 3 | 1 | 2 | 0 | 31 | 28 |
| 1897-98 | 24 | 9 | 0 | 2 | 2 | 0 | 37 | 33 |
| 1898-99 | 27 | 11 | 0 | 2 | 2 | 0 | 42 | 38 |
| 1899-00 | 24 | 5 | 0 | 0 | 2 | 0 | 31 | 27 |
| 1900-01 | 20 | 6 | 0 | 0 | 1 | 0 | 27 | 24 |
| 1901-02 | 25 | 6 | 0 | 1 | 1 | 0 | 33 | 29 |
| 1902-03 | 19 | 7 | 0 | 0 | 1 | 0 | 27 | 25 |
| 1903-04 | 26 | 8 | 4 | 1 | 2 | 0 | 41 | 37 |
| 1904-05 | 34 | 13 | 3 | 2 | 2 | 0 | 54 | 48 |
| 1905-06 | 29 | 18 | 5 | 5 | 3 | 1 | 61 | 56 |
| 1906-07 | 23 | 27 | 2 | 1 | 2 | 0 | 55 | 51 |
| 1907-08 | 21 | 18 | 0 | 2 | 1 | 0 | 42 | 41 |
| 1908-09 | 24 | 27 | 6 | 1 | 2 | 0 | 60 | 79 |
| 1909-10 | 21 | 12 | 3 | 1 | 7 | 1 | 45 | 53 |
| 1910-11 | 11 | 20 | 2 | 0 | 3 | 0 | 36 | 42 |
| **All** | 410 | 207 | 33 | 23 | 45 | 3 | 721 | 34 |
| per 1,000 re-listed | 50 | 29 | 18 | 14 | 17 | - | | |

Note 1906-07 and 1908-09 are the Musicians peaks; 1909-10 TheaterSchoolStaff (7, 63 per 1,000) is mostly Голяховскій/Тихомировъ-type known cases.

## Kind of slip

| kind | n | share |
|---|---|---|
| surname, 1–2 letters (Межакова/Лежакова type; Пржебылецкая/Пржбелецкая; Бекефи/Бекеффи) | 443 | 61% |
| first name, 1–2 letters (Юрій/Юлій; Сергѣй/Сергій; Евдокія/Евлокія) | 106 | 15% |
| patronymic, 1–2 letters | 96 | 13% |
| patronymic, different name (Михайловна→Леонидовна; Маріусовна→Васильевна; Прокофьевичъ→Прохоровичъ) | 36 | 5% |
| first name, different | 20 | 3% |
| surname, different | 11 | 2% |
| more than one field | 12 | 2% |

Whole-patronymic changes are rare (36 transitions) and spread thin: 0–2 a season in Ballet until 1902-03, then 3–8 a season from
1903-04 (Ballet patronymic changes 1–4 a year up to 1902-03, 6–8 from 1904-05). They do **not** spike in 1906-07 (5 Ballet patronymic
changes of 391 re-listed entries, split 4 Moscow / 1 SP); the "1906-07 Moscow ballet list rewrote patronymics" is visible instead as additions
(25 patronymic-missing→present transitions in Ballet that year, no more than a normal year). Nor do production lists show a visible jump at 1906-07 (ProductionTeam has only 33 changes in total, so the table cannot see a format effect).

## Same-page copying hypothesis

For each substantive change, was the new value held by another person within ±3 entries on the same page, or anywhere on the page?

- Surname (465 changes): 9.9% have the same surname within ±3 (baseline for ordinary entries: 12%).
- First name (128): 2.3% ±3, 16% page-wide (baseline 20% / 52%).
- Patronymic (143): 10.5% ±3, 19% page-wide (baseline 22% / 51%).
- Any field combined: 64 of 724 (8.8%) within ±3; 93 (12.8%) page-wide.

The new value is *less* often on the neighbouring entries than ordinary names are, so the data give no statistical support for same-page
copying as a general cause. **At least 631 of 724 (87%) changes cannot be explained by a same-page source.** The ones that can are
individual, e.g. Трекова 2-я under Грекова 1-я (already scan-confirmed) and the Лидія Кякштъ patronymic. The baselines are rough
(common first names/patronymics match neighbours by coincidence), so this is a coarse screen, not a proof for any single case.

## Confirmed vs unverified (read this before quoting any number)

1. **These counts are all of the pipeline's extraction + print.** The extraction (VLM) is non-deterministic and its misreads are
   mixed in. The shape of the data points mostly that way: 164 people alternate between two spellings; many variants are one
   character that looks like another in the type (н/п, и/н, б/в, л/д: Халинъ/Халипъ, Путырскій/Путарскій, Належда/Надежда,
   Аистовъ/Дистовъ). A scribal slip should *persist* once copied; an alternating pair more likely reflects page-by-page reading.
2. **Scan-confirmed print slips** are the ones already written up in `docs/eval/genuine_print_typos.md` and
   `uncertain_person_identities.md` (about 15 name-field cases among these transitions: Кулле Фелоровичъ, Петипа 2-я Васильевна, Кякштъ Юрьевна,
   Трекова 2-я, Сергѣевъ Георгіевичъ, Адамовъ Ерофѣевичъ, Давильеръ, Романовъ/Рахмановъ, Голяховскій Власьевичъ/Галяховскій, Беттенштелтъ, Людольфи, …).
   That is **roughly 2% of the 724** — i.e. 98% is unverified, not "known to be extraction errors".
3. **One new scan check this session**, full-resolution PDF image: Пржебылецкая / Пржбелецкая / Пржбылецкая, Анна Николаевна
   (SP ballet). 1899-00 no. 93 prints «Пржбелецкая» (scan-confirmed as printed; the extraction was right). 1900-01 no. 89 prints a surname
   that reads «Пржбылецкая/Пржбылецая» at page size (the к is faint; **not letter-confirmed**). 1897-98, 1898-99 and 1902-04 read
   «Пржебылецкая». So this surname is genuinely not stable in print, which fits RG's expectation, and it is one person with five
   spellings: the "more than 2 letters" test hides how much of the slip count is one name.
4. **Not done:** a systematic random sample of the 724 on the scans. My automated crops (position inferred from the entry number) missed on
   two-column spread pages, and only the one pair above was located by hand. The sample of 14 pairs drawn in `crop.py` is listed in the
   notes folder; a proper check needs list-number-based location (about 15 minutes per page-pair by eye). I would give this a
   separate session if RG wants a confirmed-vs-extraction fraction, since that fraction is the thing every conclusion above depends on.

## Unmerged split-name pairs (reported only)

| person(s) | seasons | what splits them | reading |
|---|---|---|---|
| Мосолова, Вѣра Владиміровна 1773bf9c (1892-93..1905-06) / Мосолова 1-я, Вѣра Ильинишна 11d2b00a (1906-07..1910-11) | one record ends where the other starts | patronymic Владиміровна vs Ильинишна (and «1-я» added) | Same start «съ 1 сентября 1893 г.», same list, adjacent seasons, no overlap. 11d2b0's 1907-08 row carries «Владиміровна» in the tenure-note field (the patronymic shifted into the note). Patronymic changed in print at 1906-07, the volume where the 1-я designation appears. Looks like one person; **a patronymic change coinciding with the new designation**. |
| Поливановъ, Василій Ивановичъ 8cf4ecef (1903-04, 1905-06) | two rows | none found in the database | Only one live record, `съ 23 декабря 1868 г.`, both rows Ивановичъ. No unmerged partner exists in `entities.person`; the quoted «Ивановичъ» split is not visible in the current data (may be the 1904-05 gap). |
| Дюжикова Римма Павловна / Дюжикова, Римма (a4f31111) | | missing patronymic | pending `name_variant_shared_start` |
| Розай, Георгій Альфредовичъ / Розай, Георгій | | missing patronymic | pending |
| Голласъ, Антонъ Францевичъ / Голласъ | | surname-only record | pending |
| Грибенъ, Августъ Ѳедоровичъ / Грибенъ | | surname-only record | pending |

The four pending candidates are bare-surname/short records with the same start date as the long record, not true name changes.
Of the 15 `entities.person_candidate` rows overall, 4 are these pending ones, 9 were `family_name_variant` and 2 `patronymic_variant` (all rejected).

## Caveats

- The classifier is mine (letters, not meaning): `docs/eval/name_slip_clustering_2026-10/an.py`; surnames edited at ≤2 letters can still be genuinely different people (siblings, homonyms), though entity resolution already joined these records.
- Counting is per transition; one confusable surname repeated across 20 years counts as many transitions, which is part of why a few people dominate (Чекетти 16 transitions; Костровской/Кастровскій, Гордонъ, Бекефи, Пащеевъ each ≥6).
- Nothing was corrected; every spelling quoted is as stored.
