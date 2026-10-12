# Person merge candidates -- batch for the end (RG's decision, 2026-10-03)

RG: gather merge possibilities into ONE batch to be decided at the end, rather than merging as they turn up. Add candidates here (person prefixes, the evidence, the recommendation), do not apply them until RG says so.
Splits of wrongly merged homonyms are different: those fix a factual error and were applied when found (issue #132: Васильевъ, Кунъ 2-й).

| Candidate | person_ids (prefix) | Evidence | Recommendation |
|---|---|---|---|
| Зандинъ Михаилъ (ProductionTeam) | a9d821 (Ивановичъ, 1906-07/1907-08, Помощникъ декораторовъ, "съ 1 мая 1907") + 831b71 (Павловичъ, 1908-09/1909-10, Исп. об. главнаго Декоратора, "съ 1 мая 1887" [typo] / "съ 1 мая 1907") | same first name, same 1 May 1907 start date in 3 of 4 volumes, promotion path, no season overlap; only the patronymic differs in print (all four read at 4-5x, 2026-10-03) | merge |
| Лебедевъ Иванъ (ProductionTeam) | 1dd355 (Васильевичъ, 1907-08, "съ 3 іюня 1889") + ea76e8 (Афанасьевичъ, 1908-09 "съ 1 іюня 1899" [typo], 1909-10 "съ 3 іюня 1889") | identical start date 3 іюня 1889 and the same Маріинскій Бутафоръ post, no season overlap; patronymic differs in print | merge |
| Петипа, Маріусъ Ивановичъ (BalletArtists/TheaterSchoolStaff) | e04344 (1890-91..1907-08) + 0f4adf (1908-09..1909-10) | identical name and patronymic, consecutive seasons; found while linking ballet-list creators (issue #133, which links to e04344) | merge |
| Чекетти, Энрико / Генрихъ Цезаревичъ | 09350c (Энрико, TheaterSchoolStaff "Танцы", 1893-94..1900-01) + bfe3f9 (Генрихъ, BalletArtists, 1890-91..1902-03) | same patronymic; Генрихъ is the usual Russian rendering of Enrico; one man in two lists (company + school), so the seasons overlap; found during issue #133 (which links to 09350c) | merge (RG to confirm Генрихъ = Энрико) |

| Петипа Маріусъ Ивановичъ (TheaterSchoolStaff + ...) | two live person_ids with the same canonical name | surfaced when the 28 missing 1892-93 p001 rows were seeded (ambiguous, left unseeded); same name, same post (dancing teacher) | check and merge |
| Ширяевъ Александръ Викторовичъ | three live person_ids with the same canonical name | surfaced at the same step; a dancing teacher printed in two lists per season (Танцы / Репетиторъ танцевъ); likely one man | check and merge |
| Голяховскій Петръ (TheaterSchoolStaff 1904-05) | patronymic Власьевичъ (p001 no. 10) vs Васильевичъ (p002 no. 1) | print variant or two men; not merged | check |

Not candidates (checked, already one person): Бардюкъ/Бордюгъ Николай Кирилловичъ (d8f03d), Каменскій/Неменскій Исаакъ Осиповичъ (1efe21).

## Decisions (review session 2026-10-05, one candidate at a time; all seven decided and APPLIED 2026-10-05, see the end of this file)

| # | Candidate | RG's decision | Open note |
|---|---|---|---|
| 1 | Зандинъ Михаилъ (a9d821 + 831b71) | **MERGE** | RG: note for later investigation -- which patronymic is right (Ивановичъ 1906-08 vs Павловичъ 1908-10)? Decide the canonical patronymic when applying; both spellings stay verbatim in raw. |
| 2 | Лебедевъ Иванъ (PT 1907-08 Васильевичъ + ea76e8 Афанасьевичъ) | **MERGE the two ProductionTeam rows**, after splitting person 1dd355 into three men (done 2026-10-05, see below) | RG: note the patronymic issue for later (Васильевичъ vs Афанасьевичъ on identical post and start date 3 іюня 1889). |

**Split applied 2026-10-05 (factual fix, not a merge; backup outputs/full_run_pre_promote_backup_2026-10-05_split_lebedev):** person 1dd355 "Лебедевъ, Иванъ Константиновичъ" had absorbed, through a chain of confirmed `family_name_variant` merges flagged `unique_name_in_corpus` (the log still shows them), three different men: the Moscow flautist Иванъ Григорьевичъ (MSK Musicians 1890-91..1896-97, "съ 26 сентября 1885", left 1 апрѣля 1897; 10 entries incl. the "см. оперный оркестръ" ballet-orchestra lines) -> new person 7ca78604; the ProductionTeam Бутафоръ Иванъ Васильевичъ (1907-08, "съ 3 іюня 1889") -> new person 1134bfb0 (to be merged into ea76e8 with the batch); the Petersburg clarinetist Иванъ Константиновичъ (SP Musicians 1890-91..1900-01, "съ 1 сентября 1868", left 1 сентября 1900; 11 entries) stays on 1dd355. Live persons 3255 -> 3257, tombstones 2313 unchanged, orphans 0, shift blocks 0.
**Follow-up this exposed (not done):** the same chain-merge pattern (name-variant merges marked `unique_name_in_corpus` joining men with different printed patronymics, overlapping seasons or different cities) may have wrongly merged other homonyms. A patronymic-conflict count over live persons gives 245 hits, but most are spelling variants/glued fields; real-looking ones to check first: Исаенко Григорій Григорьевичъ (0825c5: Васильевичъ/Григорьевичъ), Петровъ Иванъ Степановичъ (527973: Степановичъ/Ивановичъ), Алексѣевъ Александръ (49b93c). A proper sweep needs patronymic normalisation (ѳ/ф, і/и, glued first-name+patronymic) first.
| 3+5 | Петипа Маріусъ Ивановичъ (e04344 + 0f4adf + 6310e8) | **MERGE all three** into e04344 | -- |
| 4 | Чекетти Энрико/Генрихъ Цезаревичъ (09350c + bfe3f9) | **MERGE**, display name **Энрико** | display override lives in build_research_model.py (RESEARCH_PERSON_DISPLAY_OVERRIDES); entities.person keeps the majority form Генрихъ |
| 6 | Ширяевъ Александръ (0c0f54 -> 6b54e5) | **MERGE**, record the print variant | the batch's "three persons" had already been reduced to two by the stage-1 merges; the 1890-91 school row genuinely prints Васильевичъ |
| 7 | Голяховскій Петръ (dd0ff7 -> 7fd62c) | **MERGE** | Васильевичъ printed 1901-06 (verified in the 1903-04 blind sample); 1890-93 volumes print the surname "Галяховскій" |

## Applied 2026-10-05

`docs/eval/person_merge_batch_apply_2026-10-05.py` (issue #125/#131 mechanism: tombstone + person_merge_log `confirmed_manual` + repoint + refresh canonical). Backup `outputs/full_run_pre_promote_backup_2026-10-05_merge_batch`. 7 persons absorbed (live 3257 -> 3250, tombstones 2313 -> 2320), survivors: 831b71 (Зандинъ), ea76e8 (Лебедевъ), e04344 (Петипа, keeps the Wikidata link and 142 production-credit links), 09350c (Чекетти), 6b54e5 (Ширяевъ, keeps its Wikidata link), 7fd62c (Голяховскій). Survived a full rebuild (merges persist as tombstones). Orphans 0, shift blocks 0, receipts identical.

## Open notes for later investigation (RG)

- **Зандинъ Михаилъ: Ивановичъ (1906-08) vs Павловичъ (1908-10)** and **Лебедевъ Иванъ: Васильевичъ (1907-08) vs Афанасьевичъ (1908-10)**: decide which patronymic is right. Until then the person's display patronymic is a tie of the printed forms and may flip between rebuilds (Зандинъ showed Павловичъ in the dry run, Ивановичъ after the rebuild; Лебедевъ shows Афанасьевичъ). Raw keeps both printings verbatim.
- **Chain-merge sweep**: person 1dd355 had absorbed three different men through `family_name_variant` merges flagged `unique_name_in_corpus` (see the 2026-10-05 query_log entries and issue #134's follow-up). Other homonyms may have been joined the same way; a sweep needs patronymic normalisation first. Real-looking suspects: Исаенко Григорій Григорьевичъ (0825c5: Васильевичъ/Григорьевичъ), Петровъ Иванъ Степановичъ (527973: Степановичъ/Ивановичъ), Алексѣевъ Александръ (49b93c).

## 2026-10-10 -- two ь/ъ pairs merged (issue #151, RG asked for them explicitly)

Оголейтъ/Оголейть Марія Германовна (9455596b -> 383eea63) and Галатъ/Галать Надежда (4f799a33 -> 35f5810e): scan-read, same name and the same service start; `docs/eval/title_check_2026-10-10/apply_person_merges.py`. Not part of the 2026-10-05 batch.

## Ordinal-shift queue: 42 pending `ordinal_shift` pairs (review session 2026-10-12; APPLIED 2026-10-12, see the end of this file)

Source: `entities.person_candidate`, `match_reason='ordinal_shift'`, `status='pending'` (commit 4ef0c01). Evidence and scan readings are in `docs/query_log.md` under 2026-10-12. 

| Pairs | RG's decision | Note |
|---|---|---|
| Иванова 4-я, Надежда (8bb688) with Надежда Михайловна (3a64bd) and with Надежда Сергѣевна (495eba) | **SPLIT 8bb688, then merge each half** (confirmed 2026-10-12) | 1901-02 entry is printed «Иванова 4-я, Надежда Михайловна (съ 1 сентября 1900 г.)» (scan, full zoom; raw dropped the patronymic) -> 3a64bd. 1907-08 entry (Сергѣевна, съ 1 августа 1907) -> 495eba; that row not re-read on the scan. |
| Graduate Ивановъ, Александръ (38a3db) with Александръ Николаевичъ (05efa7) and with Александръ Гавриловичъ (95b2cd) | **SPLIT 38a3db, then merge each half; Николаевичъ and Гавриловичъ are TWO MEN** (RG, 2026-10-12) | 1896 graduate -> 05efa7 (съ 1 мая 1896). 1906 graduate -> 95b2cd (съ 1 іюня 1906), who is absent from the 1906-07 and 1907-08 lists and takes the «4-й» slot in 1908-09, the year after Николаевичъ's last entry («26. Ивановъ 4-й, Александръ Николаевичъ (съ 1 мая 1896 г.)», 1907-08, scan). |
| The 30 plain graduate-to-company pairs (query_log 2026-10-12, section 1 of the review) | **MERGE all 30** (RG, 2026-10-12) | Эрлеръ Алексѣй merged with a note on his missing 1907-08 season: uncertain_person_identities.md #25. Барановичъ's same-volume double listing is explained (the 1909-10 volume lists the whole 1910 class in both). |
| Тихомировъ Василій (2 pairs: graduate 75d4f2 with 690831 and with 974a69) | **MERGE, all five records into one man** (RG, 2026-10-12), discrepancy noted | Also joins 58c4eb (Ивановичъ, 1893-94..1899-00) and 6d97a1 (Дмитріевичъ), which are outside the queue. Patronymic discrepancy written up in uncertain_person_identities.md #26. |

| Сергѣевъ Николай (graduate 5a9a14 with «1-й, Георгіевичъ» 53235d) | **MERGE with notes** (RG, 2026-10-12), all three records | Also joins 154c0f (Григорьевичъ), outside the queue. No second Сергѣевъ Николай in the corpus. uncertain_person_identities.md #27. |

| Павлова, Анна Матвѣевна (18b3fd) with «Павлова 2-я, Анна» (43c8c6, Moscow 1907-08) | **MERGE** (RG, 2026-10-12) | Moscow row reads «71. Павлова 2-я, Анна Матвѣевна (съ 1 іюня 1899 г.)», 1 ballet, 1 appearance (full zoom). Raw has «2-я» in first_name and no patronymic. |

| Graduate Ивановъ, Иванъ (7a10e6) with Ивановъ 5-й, Иванъ Николаевичъ (7dd0bc) | **MERGE** (RG, 2026-10-12) | Same start date 1 June 1899; in the artists' list from 1899-00. |

| «Ивановъ 1-й, Иванъ Григорьевичъ» 1908-09 (3aa7d7), queued against graduate 7a10e6 | **MERGE into Иванъ Николаевичъ (7dd0bc)** (RG, 2026-10-12) | The row's start date is his. The 1906-07 row with the 1886 date STAYS with Григорьевичъ (d5f838), as printed: uncertain_person_identities.md #28. |

| Чіарлоне 1-я, Виргинія (4e6cf9, Moscow 1890-96) with Чіарлоне, Виргинія Михайловна (974ba5, SP 1896-1905) | **MERGE** (RG, 2026-10-12) | Her 1895-96 Moscow row states the transfer: «Съ 1 іюня 1896 года переведена въ С.-Петербургскій оркестръ оперы и балета». Harp, съ 1 апрѣля 1886 г. throughout. |

All 42 queued pairs are now decided.

### Outside-queue records, scan-checked 2026-10-12 at RG's request -- **MERGE all seven** (RG, 2026-10-12: "these seem very clear"); applied 2026-10-12

| Record | Joins | What the scan prints | Extraction problem found |
|---|---|---|---|
| Бакинъ, Александръ Всеволодовичъ (0c2699, MSK 1908-09) | Бакинъ 3-й (021b0d) + graduate 97676f | «2. Бакинъ 2-й, Александръ Всеволодовичъ (съ 1895 г.). Оставилъ службу 10 ноября 1908 г.» (full zoom) | ordinals «1-й»/«2-й» dropped on both Бакинъ rows; the departure date is not in the data; the print gives the year only |
| Гончаровъ 2-й, Леонидъ Ивановичъ (ba3854, SP 1910-11) | Гончаровъ 2-й (2c7d73) + graduate b75eaf | «15. Гончаровъ 2-й, Леонидъ Ивановичъ (съ 1 іюня 1900 г.)» (full zoom). The print itself says 1900; the row below is Григорьевъ, съ 1 іюня 1900 г. | none; a print error, candidate for genuine_print_typos.md |
| Панова, Елизавета Евгеньевна (8fb4d1, MSK 1897-99) | Панова 4-я (088e87) + graduate 2a7cdf | 1896-97 «83. Панова 4-я, Елизавета Евгеньевна» (full zoom); 1897-98 «81. Панова 4-я, Елизавета Евгеньевна (съ 1 сентября 1896 г.)» (reduced size) | 1896-97 patronymic extracted as Евгеніевна; 1897-98 ordinal dropped |
| Федорова, Екатерина «Никитовна» (71546a, MSK 1904-05) | Ѳедорова 1-я, Екатерина Никифоровна (1d7a9b) + graduate f3629e | «94. Федорова 1-я, Екатерина Никифоровна (съ 1 сентября 1898 г.)» (full zoom; Ф, not Ѳ, in this volume) | patronymic misread as Никитовна, ordinal dropped; other rows of 1d7a9b carry Latin letters in the patronymic («Никifoровна») |
| Graduate Ильина, Елена (380540, 1893-94) | Ильина, Елена Ивановна (3a0568) | Graduates «3) Ильина, Елена», class assigned to the SP troupe съ 1-го іюня 1894; 1894-95 «40. Ильина 3-я, Елена Ивановна (съ 1 іюня 1894 г.)» (both reduced size) | 3a0568 carries no ordinal although the print has «3-я» |
| Graduate Иванова, Надежда (924313, Moscow 1899-00) | Иванова, Надежда Михайловна (3a64bd) | Graduates «5) Иванова, Надежда», Moscow school, spring 1900 (reduced size; the line stating the class's start date is not on this image). She is the only Иванова Надежда with a 1 Sept 1900 start. | no start date on the graduate row |
| Мартьяновъ, Александръ Александровичъ (222cec, SP 1893-94..1910-11, displayed as «Мартыновъ») | Мартьяновъ 2-й (e452c2) + graduate 94b516 | «Мартьяновъ» in every volume checked: 1893-94, 1894-95, 1903-04, 1908-09, 1909-10 at full zoom; 1898-99, 1900-01, 1902-03, 1904-05 (both rows), 1905-06, 1906-07, 1907-08 at reduced size (enough to rule out «Мартыновъ», not to tell ь from ъ) | surname extracted as Мартыновъ (7 rows), Мартъяновъ (5), Мартяновъ (1); the person's display name is the misread form |

Not chased (logged per the stay-on-goal rule): the raw-tier fixes in the last column; 1904-05 SP p008 prints «(Онъ же помощникъ режиссера балетной труппы съ 30 января 1904 г.)» on Мартьяновъ's artist row.

### Чіарлоне, Джанина / Джаннина (outside the queue; scan-checked 2026-10-12) -- **MERGE** (RG, 2026-10-12)

Two records: b7652f (Джанина: Moscow 1890-91..1894-95 and 1899-00..1905-06) and 671bc6 (Джаннина: Moscow 1895-96..1898-99). Harp, «съ 1 апрѣля 1886 г.» in every row, no season in both. Full-zoom readings: 1894-95 «104. Чіарлоне 2-я, Джанина»; 1895-96 «105. Чіарлоне 2-я, Джаннина»; 1896-97 «106. Чіарлоне, Джаннина»; 1897-98 «104. Чіарлоне, Джаннина»; 1898-99 «107. Чіарлоне, Джаннина»; 1899-00 «103. Чіарлоне, Джанина». The print itself alternates; the extraction is right. Recommendation: merge.

The same crop confirms Виргинія's transfer note on the scan (1895-96, no. 104): «Съ 1 іюня 1896 года переведена въ С.-Петербургскій оркестръ оперы и балета.»

## Applied 2026-10-12 (ordinal-shift review)

`docs/eval/person_merge_ordinal_shift_apply_2026-10-12.py` (dry run on a copy first, then `--write`). Backup `outputs/full_run/imperial_theaters.pre_ordinalshift_review_2026-10-12.duckdb`.

- 2 splits (one entry moved each: `balletartists_1907-08_MSK_p002__e015` 8bb688 -> 495eba; `graduates_1905-06_p000__e013` 38a3db -> 95b2cd), then 51 records absorbed into 41 survivors. Live persons 3116 -> 3065; research.person 3214 -> 3163.
- Queue: 42 pending `ordinal_shift` pairs -> 0 (40 `confirmed_manual`, 2 `rejected` as pairs: the other half of each split record). 5 `family_name_variant` pairs are still pending; they were not part of this review.
- Checks: 0 orphan links, 0 shift blocks, no survivor with two rows in one season + city + section; receipts total and event count identical to the backup; a full `build_entities.py` rebuild reproduces the same links (tested on the copy: 0 link differences; two display names flip on an ordinal tie, Эрлеръ Алексѣй and Панова Елизавета).
- Wikidata: no QID lost. Linked persons 177 -> 175 because three Тихомировъ records carried the same QID. Anna Pavlova's QID (Q151874) sat on the stray Moscow 1907-08 record and now reaches her main record through the merge.
- Rebuilt on production afterwards: `build_entities.py`, `build_research_model.py`, `match_review_mentions.py`, `build_reviews_duckdb.py`, `build_review_assertions.py`. NOT rebuilt: `research_dataset.sqlite` (build_datasette) and nothing published.
- **Side effect, not fixed:** review mentions resolved to one entity 20,723 -> 20,651 (86 lost, 14 gained, 9 followed a merge). Causes: a merged dancer now "covers" his or her graduating year, and carries ordinals from other seasons, so some bare surnames tie (Сергѣевъ 33, Николаева 11, Тихомировъ 7); 27 «Федорова» mentions in Moscow 1904-05 had been resolving to the mis-extracted ordinal-less record 71546a, which no longer exists. Two matcher changes were tried (ignore the Graduates year for season cover; treat a season listed without an ordinal as "no ordinal") and made resolution worse on production itself (20,468), so they were reverted.
- Raw tier, DONE 2026-10-12 (RG: fix these): `docs/eval/raw_fix_ordinal_shift_rows_2026-10-12.py`, 33 entries on 31 pages, every row read at full zoom; field edits only, so no entry id moved. Мартьяновъ's surname on 13 rows; Ѳедорова Екатерина's patronymic and ordinal on 11 rows (incl. the Latin-letter «Никifoровна»; her 1898-99 row is printed «2-я»); Панова 4-я on 3 rows; Бакинъ 1-й / 2-й and Александръ's «Оставилъ службу 10 ноября 1908 г.»; the three rows with the ordinal in first_name (Павлова 1-я and 2-я, Moscow 1907-08; Иванова 4-я, Moscow 1901-02); «Тихоміровъ 1-й» 1899-00. Rebuilt with `rebuild_after_raw_edit.sh`; backup `outputs/full_run_pre_promote_backup_2026-10-12_ordinalshift_rawfix/`. Diff against the backup: 33 person_entry rows and 1 service row differ, 0 link differences, receipts identical, 0 shift blocks.
- Wikidata, DONE: Сергѣевъ, Николай Григорьевичъ -> Q1762062 (`docs/eval/wikidata_decision_sergeev_2026-10-12.csv`, applied with `apply_wikidata_decisions.py`). Linked persons 175 -> 176.
- **Review-matcher follow-ups, DONE 2026-10-12 (RG: yes to both):**
  - `match_review_mentions.py` now uses the review's CITY, as a tie-break only: among candidates nothing else separates, the one standing in that city's lists that season (or, with an ordinal, the one bearer of it in that city). Two guards after a first try picked wrongly: in a ballet review the pick must be on the ballet roster (a bare «Степановъ» had gone to an orchestra player), and never across gender («Никитина» had gone to Никитинъ). Measured on production: 700 mentions gained, 0 lost, 0 repointed; resolved 20,598 -> 21,298.
  - The nine Мартыновъ-type review spellings, read at full zoom: eight are transcription misreads of «Мартьяновъ» (two broken across lines as «Мартья-/новъ») and are corrected through `docs/eval/review_text_corrections.csv`; one, `review_1901-02_SP_ballet_p039`, really prints «Мартыновъ» and is recorded as a print variant in `docs/eval/review_person_variants.csv`. All nine resolve to him again.
  - Final: 27,333 mentions, 21,307 resolved to one entity (78.0%); 17,093 person mentions join research.person (16,437 after the merges).
  - Seen, not done: the Petersburg lists of 1909-11 carry ordinal-less guest rows («Гельцеръ», «Балашова») that are separate person records from the Moscow dancers they evidently are; a bare «Павлова» in Petersburg still ties between Анна Матвѣевна and Варвара Павловна, which is a real ambiguity.

## The five pending `family_name_variant` pairs (looked at 2026-10-12)

None is an extraction error: each spelling is what the print has (scan readings in docs/query_log.md and the session summary).

| Pair | Status |
|---|---|
| Девильеръ / Давильеръ, Екатерина Львовна (1272e3 + c82bb1) | **MERGED** (RG, 2026-10-12), survivor 1272e3; note in uncertain_person_identities.md #29. Live persons 3065 -> 3064. Backup `outputs/full_run/imperial_theaters.pre_devilier_merge_2026-10-12.duckdb`. |
| Воронцовъ, Владиміръ (Moscow artist, съ 1 сентября 1891) / Боронцовъ, Владиміръ (SP graduate 1911) | **PARKED** (RG, 2026-10-12) until the 1911-12 scans arrive; the pair stays pending. Two different men either way: uncertain_person_identities.md #30. |
| Раманова, Марія (SP graduate 1903) / Бажанова, Марія (Moscow graduate 1911) | **REJECTED** (RG, 2026-10-12: "definitely different people"). Раманова herself **MERGED** into Романова, Марія Федоровна (0f0d0d -> 2b7b59, which keeps Wikidata Q4397230), `docs/eval/person_merge_romanova_2026-10-12.py`; no other candidate (the class of 14 matches the fourteen «съ 1 іюня 1903 г.» entries of 1903-04 one for one; no other Р-манова Марія in the corpus). Live persons 3062 -> 3061. Бажанова waits for the 1911-12 volume. Backup `outputs/full_run/imperial_theaters.pre_romanova_merge_2026-10-12.duckdb`. |
| Фонъ-Бооль / Фонъ Бооль, Николай Константиновичъ (2 pairs, 3 records: 420cb6, 054608, aa74c2) | **MERGED** (RG, 2026-10-12: "obviously keep both [dates], but it's the same person"), survivor 420cb6, `docs/eval/person_merge_fon_bool_2026-10-12.py`. Live persons 3064 -> 3062. Both printed leaving dates stay verbatim in raw: «1 декабря 1910 г.» (administration list) and «1 февраля 1910 г.» (1910-11 Moscow school list). Backup `outputs/full_run/imperial_theaters.pre_fonbool_merge_2026-10-12.duckdb`. |

Beside them, also pending with RG: merge the patronymic-less Moscow 1910-11 Воронцовъ row into Воронцовъ, Владиміръ Васильевичъ; DONE 2026-10-12: «Фонъ-Боолъ» corrected to «Фонъ-Бооль» on administration_1898-99_p003 and administration_1899-00_p003 (both full zoom; `docs/eval/raw_fix_fon_bool_2026-10-12.py`, backup `outputs/full_run_pre_promote_backup_2026-10-12_fonbool_rawfix/`; 2 entries differ, 0 links); the probable Вольшакова/Боронцовъ initial swap is in genuine_print_typos.md. The Moscow row «8. Воронцовъ, Владиміръ … 1891 г.» (balletartists_1910-11_MSK_p004) and «Боронцовъ, Владиміръ» were both re-read at full zoom at RG's request and stand as printed.
