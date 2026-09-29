# Confirmed disagreements: ballet productions lists vs. Repertoire tables

Started 2026-09-29 at RG's request. **Only confirmed cases**: both the list entry and the Repertoire
cell were read on their own scans, and each transcription matches what its scan prints, so the
yearbook really does say two different things. Cases still under investigation or waiting for a physical
check are kept apart at the bottom and are NOT part of the list. No cause is assumed. Where the
yearbook itself points one way (e.g. the list's own entry for another ballet agrees with the Repertoire),
that is recorded as *evidence*, not as a verdict. Dates are Old Style; list dates take their year from the
list's season (see `docs/schema.md`).

Sources: list page = `balletproductions_<season>_<city>_pNNN` (printed page); Repertoire page =
`repertoire_<season>_…` (printed page). Found by `pipeline/compare_productions_repertoire.py`
(issue #101), then checked on both scans in issues #106 and #107.

## A. Dates: the list and the Repertoire disagree about when a ballet was given

| # | Season, city | Ballet (list entry) | List prints | Repertoire prints | Evidence in the yearbook | Checked |
|---|---|---|---|---|---|---|
| A1 | 1895-96 Moscow | Катарина (Дочь разбойника), #4 (p. 40) | января 17 [1896] | 17 Jan, Большой: Эсмеральда, бал. (pair014, p. 15) | Per our (scan-verified) list transcription, the list's own Эсмеральда entry gives января 14, 24, with no 17. Катарина's other list dates (13 Dec, 28 Jan) match the Repertoire | #106 item 8 |
| A2 | 1895-96 Moscow | Пробужденіе Флоры, #11 (p. 41) | мая 2, 22 [1896] | 2 May, Большой: Паяцы + Даита. 3 May (Пятница): Пряничный домикъ + Пробужденіе Флоры (pair024, p. 25) | The list's Даита entry gives мая 2, which agrees with the Repertoire's 2 May | #107 item 6 |
| A3 | 1897-98 SP | Волшебная флейта, #1 (pp. 32–33) | октября 5, 25 [1897] | 25 Oct, Маріинскій: dash (dark) (pair008, p. 8) | Neighbouring days: 24 Oct Гензель и Гретель, 26 Oct Спящая красавица. **Paired (#111):** the Repertoire prints Пахита + Волшебная флейта on **15** Oct (pair006), a date the list doesn't give; the list's 3 dates = Всего 3 | #106 item 10; #111 item 1 |
| A4 | 1897-98 SP | Дочь микадо, #2 (pp. 32–33) | ноября 9, **24**, 16, 19 | Дочь микадо on 9, **14**, 16, 19 Nov; 24 Nov Маріинскій: Фра-Дьяволо (pair010, p. 11) | The list's "24" breaks its own ascending order; its 9 dates pair 1:1 with the Repertoire's 9 | #106 item 11 |
| A5 | 1897-98 SP | Дочь микадо, #2 (pp. 32–33) | декабря 14, **38** | Дочь микадо on 14 and **28** Dec (pair014, pp. 14–15, after the #107 column repair) | "38" is not a possible day; it pairs with the Repertoire's 28 | #106/#107 |
| A6 | 1897-98 SP | Коппелія, #6 (pp. 32–33) | ноября 3 [1897] | 2 Nov, Маріинскій: Коппелія, бал. + 2-е д. бал. Млада. 3 Nov: Опричникъ (pair008, p. 8) | The list's own Млада entry prints "ноября 2 (2-е д.)", which agrees with the Repertoire's 2 Nov double bill | #107 item 13 |
| A7 | 1898-99 SP | Очарованный лѣсъ, #11 (p. 49) | сентября 21, 27 [1898] | 21 Sep, Маріинскій: Фераморсъ. Очарованный лѣсъ on 27 Sep only (p002, p. 4) | **Paired (#111):** the Repertoire prints Капризы бабочки, Волшебная флейта, Очарованный лѣсъ on **2** Sep 1898 (p000, 1731 р. 85 к.), a date the list doesn't give; the list's own Капризы бабочки entry gives "сентября 2, 23" | #106 item 13; #111 item 9 |
| A8 | 1900-01 SP | Маркитантка, #9 (p. 46) | февраля 4, 11 [1901] | 11 Feb Маріинскій: morning Садко; evening Бенефисъ Кордебалета (4-я карт. бал. Камарго, 2-е д. бал. Фіамметта, 2-е д. бал. Щелкунчикъ). Маркитантка on 4 Feb only (p026, p. 28) | The list's own Камарго, Фіаметта and Щелкунчикъ entries all give 11 Feb, without Маркитантка | #106 item 16 |
| A9 | 1901-02 Moscow | Лебединое озеро, #9 (p. 54) | сентября 16, 21 [1901] | 21 Sep, Большой: Русланъ и Людмила, оп. Лебединое озеро on 16 Sep only (p003, p. 5) | **Paired (#112):** the Repertoire prints Лебединое озеро, бал. at the Большой on **21 Oct** 1901 (p009, p. 11, 2421 р. 58 к.), a date the list doesn't give; the list's 8 dates = its "Всего—8" and include no October date | #106 item 17; #112 |
| A10 | 1901-02 SP | Волшебная флейта, #3 (p. 46) | декабря 19, 28 [1901] | 19 Dec, Маріинскій: Сильвія, бал. only. Волшебная флейта on 28 Dec morning (p018, p. 20) | The list's own Сильвія entry also gives 19 Dec, so the list implies a double bill that the Repertoire doesn't print | #106 item 18 |
| A11 | 1903-04 SP | Волшебная флейта, #4 (p. 45) | ноября 30 [1903] | 30 Nov, Маріинскій: morning Фаустъ; evening Фея куколъ + 2-е д. бал. Фіаметта (p014, p. 16) | none | #106 item 21 |
| A12 | 1904-05 SP | На перепутьи, #17 (p. 139) | декабря 12, 17 [1904] | На перепутьи on 12 Dec evening only (Ширяевъ benefit); 17 Dec Маріинскій: Валкирія only (p018, p. 108) | **Paired (#111):** the Repertoire prints Пробужденіе флоры / На перепутьи / Фея куколъ at the **27** Dec утро (p020, 1883 р. 19 к.); the list's Пробужденіе флоры and Фея куколъ entries both give 27 Dec | #106 item 23; #111 item 3 |

## B. Works: the list names a ballet that the Repertoire cell doesn't name

| # | Season, city | Ballet (list entry) | List prints | Repertoire prints | Checked |
|---|---|---|---|---|---|
| B1 | 1904-05 SP | Дочь Фараона, #7 (p. 138) | февраля 13 [1905] | 13 Feb, Маріинскій evening: only the heading "Бенефисъ кордебалетныхъ артистовъ и артистокъ." and 8750 р. 70 к., with no work titles (p030, p. 120) | #106 item 24 |

## C. Titles: both sources name the same performance but spell the title differently

Each Repertoire spelling was confirmed on its scan in issue #105 (transcription matches the print), and the
list spelling was confirmed in the list verification (issue #101).

| # | Season, city, date | List prints | Repertoire prints (page) |
|---|---|---|---|
| C1 | 1899-00 Moscow, 5, 8 and 19 Dec 1899 | Волшебныя грёзы (#2, p. 55) | Волшебные грезы, 3 cells (p017 p. 19; p019 p. 21). The same Repertoire page also prints "Волшебныя грезы" on 28 Dec |
| C2 | 1899-00 Moscow, 23 Apr 1900 | Привалъ кавалеріи (#8, p. 55) | Привалъ кавалерія (p037, p. 39) |
| C3 | 1899-00 SP, 9 Feb 1900 | Маркобомба (#17, p. 46) | Маркабомба (p026, p. 28) |
| C4 | 1900-01 SP, 11 Feb 1901 | Фіаметта (#20, p. 47) | 2-е д. бал. Фіамметта (p026, p. 28) |
| C5 | 1902-03 SP, 4 Dec 1902 | Фіаметта (#27, p. 45) | 2-е д. бал. Фіамметта (p014, p. 16) |
| C6 | 1903-04 SP, 25 Jan 1904 | Фіаметта (#26, p. 46) | 2-е д. бал. Фіаметто (p024, p. 26) |
| C7 | 1904-05 SP, 1 Dec 1904 | Граціелла (#6, p. 138) | Граціела (p016, p. 106) |

## D. Performances the Repertoire prints but the list leaves out (list internally consistent: its printed dates = its "Всего")

| # | Season, city | Ballet (list entry) | Repertoire prints | List prints | Evidence in the yearbook | Checked |
|---|---|---|---|---|---|---|
| D1 | 1897-98 Moscow | Фея куколъ, #13 (p. 40) | 14 Jan 1898, Большой: Жизель + Фея куколъ, 517 р. 30 к. (pair016) | 10 dates, none in January; Всего—10 | none | #111 item 2 |
| D2 | 1898-99 Moscow | Привалъ кавалеріи, #9 (p. 58) | 25 Apr 1899, Большой: Фея куколъ / 2-е д. бал. Конекъ-Горбунокъ / Привалъ кавалеріи, 959 р. 15 к. | 9 dates, no 25 Apr; Всего—9 | The list's own Фея куколъ entry does give "апрѣля 25", and the two share a bill on most other Фея куколъ dates | #111 item 10 |
| D3 | 1900-01 SP | Фіаметта, #20 (p. 47) | 30 Dec 1900, Маріинскій evening: Русское Театральное Общество benefit incl. "2-е д. бал. Фіаметта.", no receipts | "1901 г.—февраля 11. Всего—1 разъ." | Charity/benefit bill | #111 item 14 |
| D4 | 1902-03 Moscow | Конекъ-горбунокъ, #5 (p. 51) | 8 Apr 1903, Большой: Иверская Община charity bill incl. "7-я и 11-я карт. бал. Конекъ-горбунокъ", no receipts (p031) | 12 dates to "апрѣля 13" + post-total "1-е дѣйствіе исполнено … апрѣля 27"; no 8 Apr | Charity bill | #111 item 5 |
| D5 | 1903-04 Moscow | Золотая рыбка, #4 (p. 52) | 30 Mar 1904, Большой: Иверская charity bill incl. "Золотая рыбка, бал.", no receipts (p031) | 8 dates, no 30 Mar; Всего—8 | Charity bill | #111 item 6 |
| D6 | 1903-04 SP | 2-е д. Лебединое озеро, #14 (p. 45) | 21 Feb 1904, Маріинскій: Red Cross benefit incl. "2-е д. бал. Лебединое озеро.", no receipts | "ноября 16 … января 18; февраля 4 (2-я картина 1-го дѣйствія). Всего—3 раза" | Charity bill | #111 item 15 |
| D7 | 1903-04 SP | Волшебная флейта, #4 (p. 45) | 3 Apr 1904, Маріинскій: Гребловская школа charity bill, item "2) Волшебная флейта, бал.", no receipts (p032) | "сентября 28; ноября 30. 1904 г.—февраля 7. Всего 3 раза" | Charity bill | #111 item 8 |
| D8 | 1903-04 SP | Фея куколъ, #25 (p. 46) | 10 Apr 1904, Маріинскій: sailors' families charity bill, item "5) Фея куколъ, бал.", no receipts (p032) | "1903 г.—ноября 30. Всего—1 разъ" | Charity bill | #111 item 7 |

**Observed pattern (not a conclusion):** D3–D8 are all charity or benefit bills with no receipts printed, and in each the list omits the date. A checker noticed the same for Сынъ Мандарина on the 8 Apr 1903 Иверская bill (not a ballet; not yet checked).

## E. Ballets the Repertoire prints that have no entry at all in that season's list

Each list's whole "Балетъ" section (every entry, title, excerpt note and post-total note) was read on its scan; the ballet appears nowhere in it. Each Repertoire cell was read on its own scan (#112).

| # | Season, city | Repertoire prints | List | Checked |
|---|---|---|---|---|
| E1 | 1902-03 SP | 14 Dec 1902, Маріинскій: "Спектакль по случаю 100-лѣтняго юбилея Пажескаго Его Императорскаго Величества корпуса. 1-е д. оп. Жизнь за Царя. 1-е д. бал. Дочь Микадо, бал.", no receipts (p016, p. 18) | pp. 44–45, entries 1–30: no Дочь Микадо, and no декабря 14 under any entry | #112 item 1 |
| E2 | 1903-04 SP | 24 Apr 1904, Маріинскій: "Спектакль въ пользу раненыхъ и больныхъ воиновъ дѣйствующей арміи." Мнимыя дріады, бал.-карт. / Голубая Георгина, бал. / Дивертиссементъ, no receipts (p036, p. 38) | pp. 44–46, entries 1–28: no Голубая Георгина, and no апрѣля 24 under any entry | #112 item 2 |
| E3 | 1903-04 SP | Same bill as E2: Мнимыя дріады, бал.-карт. | Same list: no Мнимыя дріады under any title, excerpt or note | #112 item 3 |
| E4 | 1904-05 SP | 29 Mar 1905, Маріинскій: "Спектакль въ пользу Отдѣла защиты дѣтей отъ жестокаго обращенія." Эсмеральда, бал., no receipts (p038, p. 128) | pp. 138–139, entries 1–30: no Эсмеральда, and no марта 29 | #112 item 4 |
| E5 | 1904-05 SP | 23 Apr 1905, Маріинскій: "Спектакль въ пользу Общества попеченія о Гребловской школѣ имени Н. В. Гоголя." „Письмо Татьяны", сц. изъ оп. Евгеній Онѣгинъ / Балетоманъ / Сонъ въ лѣтнюю ночь, бал. / Дивертиссементъ / Свадьба, сц., no receipts (p042, p. 132) | Same list: no Сонъ въ лѣтнюю ночь (nor Балетоманъ), and no апрѣля 23 | #112 item 5 |

**Observed pattern (not a conclusion):** all five are on jubilee or charity bills with no receipts printed, the same shape as D3–D8. Side note: the 1904-05 SP list does have Голубая георгина (#5, p. 138: февраля 20, 27 1905, no * premiere marker).

## F. Ballet divertissements: printed in the Repertoire, outside what the lists record (tracked)

**RG, 2026-09-29:** these are outside what the ballet lists record, so they are not disagreements, but they are
important to track. Each Repertoire cell prints "Балетный дивертиссементъ" (no genre; the research layer assigns
"бал.", #114). Each list was read in full on its own scan: no list mentions a divertissement anywhere, and none gives
these dates under any entry or post-total note (#114, 2nd addendum).

| # | Season, city | Repertoire prints | List | Checked |
|---|---|---|---|---|
| F1 | 1901-02 Moscow | 17 Oct 1901, Новый: Соломенная шляпка, ком.-вод. / Балетный дивертиссементъ, 557 р. 88 к. (p007, p. 9) | p. 54, entries 1–15: no divertissement, no октября 17 | #114 |
| F2 | 1901-02 Moscow | 9 Jan 1902, Новый: Соломенная шляпка, ком.-вод. / Балетный дивертиссементъ, 417 р. 89 к. (p021, p. 23) | Same list: no января 9 | #114 |
| F3 | 1901-02 Moscow | 16 Jan 1902, Новый: Воспитатель Флаксманъ, ком. / Балетный дивертиссементъ, 430 р. 68 к. (p023, p. 25) | Same list: no января 16 | #113 |
| F4 | 1901-02 Moscow | 20 Apr 1902, Большой: "Бенефисъ вторыхъ режиссеровъ и суфлеровъ." 3-е и 4-е д. оп. Гугеноты / Сцена 5-го д. траг. Макбетъ / 3-е д. ком. Горе отъ ума / Концертное отдѣленіе / Балетный дивертиссементъ, 3286 р. 36 к. (p035, p. 37). (the first word's е lacks its crossbar in the print: broken type, not a misprint; #114) | Same list: no апрѣля 20 | #114 |
| F5 | 1902-03 Moscow | 25 Jan 1903, Малый: "Въ пользу недостаточныхъ учащихся Драматическихъ Курсовъ при Императорскомъ Московскомъ Театральномъ Училищѣ." Женская логика, ком. / Балетный дивертиссементъ, no receipts (p023, p. 25) | p. 51, entries 1–10: no divertissement, no января 25 (section complete, see note below) | #114 |
| F6 | 1902-03 Moscow | 12 Apr 1903, Большой: "Въ пользу убѣжища для престарѣлыхъ артистовъ." Ревизоръ, ком. / Балетный дивертиссементъ, no receipts (p033, p. 35) | Same list: no апрѣля 12 | #114 |
| F7 | 1903-04 SP | 22 Feb 1904, Маріинскій: benefit of the Спб. Общество попеченія о душевно-больныхъ, part of the takings to the committee for strengthening the navy. 1) чтеніе, пляска 2) 2-е д. оп. Карменъ 3) 1-я карт. 4-го д. оп. Аида 4) Балетный дивертиссементъ 5) сцена изъ 4-го д. оп. Гугеноты, no receipts (p028, p. 30) | pp. 44–46, entries 1–28: no divertissement, no февраля 22 | #114 |
| F8 | 1903-04 SP | 17 Apr 1904, Маріинскій: Red Cross benefit for crippled soldiers and their families. 2-е и 3-е д. ком. Волки и овцы / Паяцы, оп. Леонковалло / Балетный дивертиссементъ / Птички-пѣвчія, оперетта, no receipts (p034, p. 36) | Same list: no апрѣля 17 | #113 |

**1902-03 Moscow completeness (RG's point, 2026-09-29):** the section ends mid-page on p. 51 with no closing
ornament, and our scan has only that page. But the Repertoire shows nothing missing. Every ballet-genre Moscow
performance that season is one of the list's 10 works or an excerpt of one; the only exception is the divertissement
(F5, F6). The season's genre-less Moscow rows hold no other ballet. The list is also alphabetical and ends at
"Эсмеральда". So no p. 52 check is needed. RG also confirms she scanned every page that
included ballet, so the ballet-list PDFs are complete by design. **Observed (not a
conclusion):** 5 of the 8 (F4–F8) are on benefit or charity bills; F1–F3 are ordinary Новый evenings pairing a
comedy with the divertissement. **Not in this table:** 3 more ballet divertissements fall in
seasons with no ballet list in our set (1905-06 ×2, 1908-09 ×1).

## Not (yet) on the list: waiting for a physical check or not a disagreement

- **Waiting for RG's physical check:** 1897-98 SP Пахита "мая 5 (3-е д.)" vs. a Repertoire line inside the
  binding fold (p012, p. 26, read from letter tops as "3-е д. бал. Пахита", not promoted); 1892-93 SP
  "Паяда и рыбакъ" (pair004, p. 4, 240 dpi; list "Наяда"); 1903-04 Moscow "Ваядерка" (p025, p. 27, low-res;
  list "Баядерка"); 1903-04 Moscow "Пригалъ кавалеріи" (p013, p. 15, possibly a broken sort; list "Привалъ").
- **Not a disagreement:** 1900-01 SP "Ученики Дюпрэ" = Repertoire "Les élèves de Dupré" (same work, Russian
  vs French title). The four list dates with a printed year that differs from the season (Пери, Дочь Микадо
  1899-00, Коппелія 1902-03, Тщетная 1902-03) all match the Repertoire once the date is taken from the
  season, so they aren't disagreements.
- **Checked, not a disagreement (#113):** the 2 "Балетный дивертиссементъ" leads (16 Jan 1902 Новый, 1901-02
  p023; 17 Apr 1904 Маріинскій, 1903-04 p034). Both scans print "Балетный дивертиссементъ." with no genre; the
  "бал." was a transcription addition, now removed. Neither list has an entry or a date for them.
- **Repertoire-side leads (as of #114):** 40 in `outputs/ballet_productions_pilot/compare/repertoire_not_in_lists.csv`:
  the 8 divertissements (section F), the 12 comedy-ballet (ком.-бал.) performances (Батюшкина дочка ×7, Мѣщанинъ во
  дворянствѣ ×5; RG's separate research need, drama performances with ballet or dancers), and the rest in A, D or E.
