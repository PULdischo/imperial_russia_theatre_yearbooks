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

## Decisions (review session 2026-10-05, one candidate at a time; merges are APPLIED TOGETHER after all seven are decided)

| # | Candidate | RG's decision | Open note |
|---|---|---|---|
| 1 | Зандинъ Михаилъ (a9d821 + 831b71) | **MERGE** | RG: note for later investigation -- which patronymic is right (Ивановичъ 1906-08 vs Павловичъ 1908-10)? Decide the canonical patronymic when applying; both spellings stay verbatim in raw. |
| 2 | Лебедевъ Иванъ (PT 1907-08 Васильевичъ + ea76e8 Афанасьевичъ) | **MERGE the two ProductionTeam rows**, after splitting person 1dd355 into three men (done 2026-10-05, see below) | RG: note the patronymic issue for later (Васильевичъ vs Афанасьевичъ on identical post and start date 3 іюня 1889). |

**Split applied 2026-10-05 (factual fix, not a merge; backup outputs/full_run_pre_promote_backup_2026-10-05_split_lebedev):** person 1dd355 "Лебедевъ, Иванъ Константиновичъ" had absorbed, through a chain of confirmed `family_name_variant` merges flagged `unique_name_in_corpus` (the log still shows them), three different men: the Moscow flautist Иванъ Григорьевичъ (MSK Musicians 1890-91..1896-97, "съ 26 сентября 1885", left 1 апрѣля 1897; 10 entries incl. the "см. оперный оркестръ" ballet-orchestra lines) -> new person 7ca78604; the ProductionTeam Бутафоръ Иванъ Васильевичъ (1907-08, "съ 3 іюня 1889") -> new person 1134bfb0 (to be merged into ea76e8 with the batch); the Petersburg clarinetist Иванъ Константиновичъ (SP Musicians 1890-91..1900-01, "съ 1 сентября 1868", left 1 сентября 1900; 11 entries) stays on 1dd355. Live persons 3255 -> 3257, tombstones 2313 unchanged, orphans 0, shift blocks 0.
**Follow-up this exposed (not done):** the same chain-merge pattern (name-variant merges marked `unique_name_in_corpus` joining men with different printed patronymics, overlapping seasons or different cities) may have wrongly merged other homonyms. A patronymic-conflict count over live persons gives 245 hits, but most are spelling variants/glued fields; real-looking ones to check first: Исаенко Григорій Григорьевичъ (0825c5: Васильевичъ/Григорьевичъ), Петровъ Иванъ Степановичъ (527973: Степановичъ/Ивановичъ), Алексѣевъ Александръ (49b93c). A proper sweep needs patronymic normalisation (ѳ/ф, і/и, glued first-name+patronymic) first.
