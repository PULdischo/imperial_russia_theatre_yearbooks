# Confirmed disagreements: opera and drama production lists vs. Repertoire tables

Started 2026-11-12 (RG: "go ahead and do it"; checklist D5), on the model of
`docs/eval/ballet_list_repertoire_disagreements.md`. **Only confirmed cases**: the list entry was read on its scan by Claude
(the helper's transcription checked entry by entry), and the Repertoire cell was read twice (the full sweep and the blind
column reads, `docs/eval/scan_audit/1911-12_scan_reads.csv` / `outputs/repertoire_1911-12/column_reads/`), so the yearbook
really says two different things. No cause is assumed; where the yearbook points one way, it is recorded as *evidence*.
Dates are Old Style.

The opera and drama lists are a cross-check source, not loaded into the database (RG: opera lists archive only; 2026-11-12:
"use the production lists for opera and drama as needed for crosschecking things").

Sources: `pdf/Spiski_OperaProductions/ForUpload_1911-12_Spisok_OperaProductions{SP,Moscow}.pdf`,
`pdf/Spiski_DramaProductions/ForUpload_1911-12_Spisok_{Drama,FrenchDrama}Productions*.pdf` (printed pp. 59-68).
Transcription (finding aid, one row per entry with every date): `docs/eval/scan_audit/1911-12_opera_drama_lists.csv`.
Comparison: `docs/eval/scan_audit/compare_opera_drama_lists_1911-12.py`.

## 1911-12

158 entries (SP Русская драма 34, Русская опера 30, Французская драма 37; Moscow Русская драма 34, Русская опера 23). Each
entry's dates equal its printed «Всего», except Moscow opera #7 «Жизнь за Царя» (11 dates, «Всего—10»: the act 2 on
20 Jan is printed after the total's other dates; «Русланъ и Людмила» #19 counts its 20 Jan act). **138 entries agree with
the Repertoire date for date.** The German guest troupe and the Moscow Art Theatre visit have no list.

### A. Dates: a list date and a Repertoire date differ for the same work (the counts agree)

| # | City | Work (list entry) | List prints | Repertoire prints | Evidence |
|---|---|---|---|---|---|
| A1 | SP | Капитанская дочка, opera #12 (p. 61); Князь Игорь, opera #14 (p. 62) | Капитанская дочка «сентября 1»; Князь Игорь «августа 31» | Маріинскій 31 Aug: Капитанская дочка; 1 Sep: Князь Игорь (p. 2, both 4376 р. 90 к.) | The two operas' first dates are exchanged |
| A2 | SP | Самъ у себя подъ стражей, Russian drama #22 (p. 60) | сентября 15 | Михайловскій 16 Sep (p. 4, 523 р. 15 к.); 15 Sep: dash | |
| A3 | SP | Самъ у себя подъ стражей, #22 | ноября 27 | Александринскій 27 **Dec** morning (p. 26, 428 р. 35 к.); 27 Nov: Коварство и любовь / Женитьба Бѣлугина | Same day, next month |
| A4 | SP | Эмилія Галотти, Russian drama #34 (p. 61) | ноября 14 | Михайловскій 15 Nov (p. 16, 240 р. 65 к.); 14 Nov: Le barbier de Séville (morning), dash (evening) | |
| A5 | SP | Морякъ скиталецъ, opera #17 (p. 62) | декабря 6 | Маріинскій 16 Dec (p. 24, 4376 р. 90 к.); 6 Dec: Раймонда (morning), Жизнь за Царя (evening) | |
| A6 | Moscow | Гроза, Russian drama #11 (p. 66) | сентября 16, 23, 30 | Малый **16, 23, 30 Oct** morning, «Спектакль для учащейся молодежи» (pp. 11, 13, 15); 16, 23, 30 Sep: Горе отъ ума, Безприданница, Жуликъ | Same days, next month; the list prints no October date for Гроза |

### B. A list date with no performance of that work in the Repertoire

| # | City | Work (list entry) | List prints | Repertoire prints that day |
|---|---|---|---|---|
| B1 | SP | Воители въ Гельгеландѣ, Russian drama #1 (p. 59) | января 25, 27 [1912] | Михайловскій: dash both days; Александринскій: Кухня вѣдьмы (25), На всякаго мудреца довольно простоты (27) |
| B2 | SP | Трагедія о Гамлетѣ, принцѣ датскомъ, #28 (p. 60) | октября 31; ноября 9 | Михайловскій: dash both days; Александринскій: Прохожіе both days |
| B3 | SP | Самъ у себя подъ стражей, #22 (p. 60) | ноября 11 | Михайловскій: dash; Александринскій: Свадьба Кречинскаго |
| B4 | SP | Тартюфъ, #27 (p. 60) | ноября 25 | Михайловскій: dash; Александринскій: Прохожіе |
| B5 | SP | Побѣжденный Римъ, #17 (p. 60) | декабря 16 | Михайловскій: dash; Александринскій: Кухня вѣдьмы |
| B6 | SP | Эмилія Галотти, #34 (p. 61) | ноября 4 | Михайловскій: dash; Александринскій: Прохожіе |
| B7 | SP | Les bleus de l'amour, French #4 (p. 64); Les roses de Bellaggio, French #26 (p. 65) | ноября 15, 17 (with 12, 13) | Михайловскій 15 Nov: Эмилія Галотти; 17 Nov: dash. The double bill is printed 12 and 13 Nov only |
| B8 | Moscow | Псковитянка, opera #15 (p. 68) | декабря 22 | Большой: dash; Малый: Израиль + Школа мужей |

*Observation, not a conclusion:* B1-B6 and B7's 17 Nov all fall on days the Repertoire prints a dash for the Михайловскій.
The season totals (p. 56) print fewer SP Russian drama events than the Repertoire (ledger row 1911-12-10: Repertoire +11),
so they do not point to performances missing from the Repertoire.

### C. A Repertoire performance with no such date in the list

| # | City | Repertoire prints | List entry |
|---|---|---|---|
| C1 | SP | Александринскій 26 Mar 1912: Исторія одного увлеченія (p. 46) | #9 (p. 59): «апрѣля 9, 16. Всего—2» |
| C2 | SP | Михайловскій 16 Jan 1912: Завтракъ у предводителя + Тяжелые дни (p. 30) | #12 and #30 (p. 60): neither gives 16 Jan; the pair is otherwise printed together at the Александринскій on 5 Dec, 17 Feb and 11 Mar, all in both lists |
| C3 | SP | Михайловскій 31 Jan 1912: La petite chocolatière + Un jour de fête, 1314 р. 50 к. (p. 34) | French #30 and #15: «января 28, 29, 30. Всего—3» each |
| C4 | Moscow | Большой 9 Apr 1912: Евгеній Онѣгинъ, 1071 р. 65 к. (p. 49) | opera #6 (p. 68): no April date but 28 |
| C5 | Moscow | Большой 28 Sep 1911: Риголетто + 5-е д. бал. «Конекъ-горбунокъ» (p. 7) | opera #16 (p. 68): «сентября 30; декабря 3. Всего—2» |
| C6 | Moscow | Большой 26 Nov 1911, Островскій jubilee: 2-е д. of Послѣдняя жертва, Правда—хорошо, а счастье—лучше, Невольницы (p. 21) | None of the three plays has an entry in the Moscow list |
| C7 | SP | Маріинскій 1 May 1912, «Экстраординарный спектакль въ пользу Дѣтскаго Дома Трудолюбія бѣднымъ»: Маскотта (Красное Солнышко), оперетта (p. 54) | No entry in the SP opera list |

### D. Titles printed differently (same work)

| City | List | Repertoire |
|---|---|---|
| Moscow | «Безчестіе (Der Helfer)», Феликсъ Филиппи (#3, p. 66) | «Безчестье» (all 11) |
| Moscow | «Герцогиня Падуанская» (#8, p. 66) | «Паддуанская» on every printing (and the typos «Гарцогиня», «Герцогина», «Паддуанскяя») |
| SP | «Морякъ скиталецъ» (#17, p. 62) | «Морякъ-скиталецъ» on 8 printings, «Морякъ скиталецъ» on 13 Nov |
| SP | «L'éperon» (French #10) | «L'épéron» / «L'épèron» |
| SP | «Le gout du vice» (#13), «L'oncle Rémy» (#24) | «Le goût du vice», «L'oncle Remy» |

Nothing here changes the database. Open for RG: whether any of A-C should be followed up (the 1911-12 Season Reviews,
when scanned, may date some of them).
