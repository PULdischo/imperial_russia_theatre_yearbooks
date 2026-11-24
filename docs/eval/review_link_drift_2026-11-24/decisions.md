# Review link drift, 2026-11-24 — RG's decisions

A matcher rerun on the current database changes 38 person links in `research.review_mention` beyond the 15 approved
unlinks of 2026-11-12 (people added with 1911-12; see `docs/query_log.md`, 2026-11-12). Evidence for each mention:
`evidence.txt` (numbered 1-38). Decisions go into `docs/eval/review_mention_links.csv` (or the person-merge batch) and
are applied in one rebuild once all are decided. Scan reads are by Claude, as finding aids.

| # | Mention | Decision | Basis |
|---|---|---|---|
| 23-24 | «г-жи Павловой», SP 1910-11 (pp. 135, 136) | Павлова 2-я, Анна Матвѣевна (RG 2026-11-24) | two-year leave, American tour, Никія; not on the printed 1910-11 roster (leave) |
| 25-26 (+3 same-season mentions not among the 38) | «Павловой» / «Павлова», SP 1912-13 (pp. 140-142) | Павлова 2-я, Анна Матвѣевна (RG 2026-11-24) | «балерины: … г-жа Павлова (10 спектаклей)» = Донъ-Кихотъ 5 + Дочь фараона 4 + Баядерка 1; no 1912-13 roster in the data |
| 35 | «О. А. Спесивцева», SP 1912-13 graduate (p. 143) | unlinked (RG 2026-11-24) | initials О. А., spring-1913 graduate; Зинаида graduated 1911; no record (rosters end 1911-12) |
| 1 | «восп-ца Александрова», SP 1899-00 (p. 96) | unlinked (RG 2026-11-24) | a pupil; not Лидія (Moscow, grad. 1910-11); likely but unproven Александра Матвѣевна (grad. 1903-04) |
| 16-22 | «в-ца Клемецкая», SP 1903-04 – 1905-06 (pp. 119, 121, 121, 136, 137) | Клемецкая, Евгенія Вацлавовна (RG 2026-11-24) | pupil; the only Клемецкая in the data (grad. 1909-10, troupe 1 June 1910); no namesake |
| 4-5 | «в-къ Владиміровъ», SP 1905-06 (pp. 136, 137) | Владиміровъ, Петръ Николаевичъ (RG 2026-11-24) | male pupil; the only male Владиміровъ in the data (grad. 1910-11, troupe 15 June 1911) |
| 12-15 | «в-ца Кирхгеймъ», SP 1905-06 (pp. 136, 137) | Кирхгеймъ, Луція (RG 2026-11-24); Луція / Маргарита Фердинандовна added to the merge batch | the only Кирхгеймъ graduate of the school (1911); Маргарита appears only from 1911-12 |
| 8-11 | «Карлова», SP 1903-04 – 1904-05 pupil (pp. 119, 121, 121) | Карлова, Софья Федоровна (RG 2026-11-24); Софья / Софія added to the merge batch | the only Карлова in the data (grad. 1909-10), split by spelling |
| 28-31 | «в-ца Подраменцова», SP 1903-04 – 1905-06 (pp. 119, 121, 136) | unlinked (RG 2026-11-24) | sisters Евгенія (grad. 1909) and Лидія (grad. 1912) both possible; Евгенія likelier |
| 2-3 | «г. Арендса», Moscow 1908-09 and 1910-11 (p. 97) | Арендсъ, Андрей Федоровичъ (RG 2026-11-24) | капельмейстеръ балета «съ 25 сентября 1883»; the 1911-12 «Генрихъ Евгеній» duplicate is already in merge batch Group C |
| 32-33 | «г. Померанцевъ» conducting, Moscow 1910-11 (pp. 96, 97) | Померанцевъ, Юрій Николаевичъ (RG 2026-11-24); «Ю. Н.» / Юрій Николаевичъ added to the merge batch | капельмейстеръ балета from 1 Apr 1910; «впервые передъ пюпитромъ» |
| 7 (+ «съ г-жей Егоровой», same page) | «г-жа Егорова (4 спектакля)», SP 1912-13 (p. 141) | Егорова, Любовь Александровна 0eea687d (RG 2026-11-24); 0eea687d / 28cd3752 (1911-12) added to the merge batch | the only SP Егорова 1909-12; Ольга Андреевна is Moscow; the 4 performances = «Конекъ-горбунокъ» 21 Feb, 21/24/28 Apr |
| 27 | «мандолинѣ—г. Парисъ», SP 1905-06 (p. 132) | unlinked (RG 2026-11-24) | Джиниславъ (trombone) left 1 Apr 1900; no Парисъ in the 1905-06 orchestra; Викторъ is 1911-12 drama hairdressing staff |
| 34 | «режиссеромъ Н. С. Сергѣевымъ», SP 1906-07 (p. 157) | Сергѣевъ, Николай Григорьевичъ 154c0f60 (RG 2026-11-24); 1911-12 «1-й, Николай Георгіевичъ» 50b3fbe3 added to the merge batch | «Н. С.» printed (slip); the only SP ballet режиссеръ; same season prints «Н. Г. Сергѣевымъ» |
| 6 | «воспитанники: … Голейзовскій», SP 1908-09 (p. 121) | Галейзовскій, Кассіанъ Карловичъ 4f9e2bf4 (RG 2026-11-24); graduate «Гамлійзовскій, Кассіанъ» bdae8b91 added to the merge batch | the one Кассіанъ of the class; Moscow from 1 Aug 1909; rebuild lost it because Надежда is printed «Голейзовская» in 1911-12 |
| 36 | «произведеній Фокина «Павильонъ Армиды»», SP 1910-11 (p. 138) | Фокинъ, Михаилъ Михайловичъ 5cef3dd5 (RG 2026-11-24) | masculine genitive, the choreographer; corrects production's link to Вѣра Петровна |
| 37-38 | «гг. Н. Легатъ, Фокинъ» SP 1905-06 (p. 135); «Pas de trois … г. Фокинъ» SP 1907-08 (p. 94) | Фокинъ, Михаилъ Михайловичъ 5cef3dd5 (RG 2026-11-24) | the only male Фокинъ in the SP ballet; keeps production's link |

Tangent noted (not chased): the two 1893-94 «Парисъ» mentions (p001__b003, p002__b003) are the character Paris, typed as person mentions; unlinked, harmless.

Expected in the rebuild diff, not drift: one RG-approved text correction (2026-11-24, applied by the jubilees session to
outputs/reviews/merged_full/review_block.csv): «успѣшаго» -> «усопшаго» in review_1893-94_SP_opera_p039__b004.

Outside the 38 (written here so one session writes review_mention_links.csv): «Яковлевъ 2-й», SP 1891-92 (review_1891-92_SP_ballet_p017__b002) relinked from Яковлевъ, Николай Николаевичъ (a985e058) to Яковлевъ, Владиміръ (931f4063), the 1892 graduate who died 9 Aug 1892 -- RG 2026-11-24, via the jubilees/obituaries session. Expected in the rebuild diff.
Tangent noted (not chased): review_1907-08_SP_ballet_p002__b006 transcribes «g. Фокинъ» with a Latin g; the print has Cyrillic «г.» (p. 94). Candidate for review_text_corrections.csv.

## Applied 2026-11-24

All 38 ruled. Rebuild on a copy diffed against production: only the ruled changes, the 15 approved 12 Nov unlinks, «Яковлевъ 2-й»,
the «усопшаго» text fix, two new unlinked mentions and method labels. Follow-on rulings (RG): credit override for «Н. С.
Сергѣевымъ» (review_credit_overrides.csv); 8 new roster-credit performer links in review_assertion, 6 accepted, 2 held
(review_assertion_overrides.csv, action `unlink_performer`, new in build_review_assertions.py). Production backed up
(imperial_theaters.pre_review_drift_2026-11-24.duckdb) and replaced. Query log 2026-11-24. SQLite republish: Andy.

Tangent noted (not chased): credits disagreeing with a scan-verified mention link, already in production: Головина 1904-05
(credit Головинъ А. Я. / mention Марія Ивановна), Васильева 1905-06, Герберомъ 1894-95.
