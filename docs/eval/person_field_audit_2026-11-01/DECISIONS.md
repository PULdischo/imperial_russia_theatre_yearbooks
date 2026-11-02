# Person field audit — decision list (2026-11-02)

All readings "checked by Claude" (finding aids); evidence per item in `slices/*_results.csv`. Nothing applied yet.
Totals: flags 1,565 read (981 match print, 200 print slips, 155 misreads, 101 wrong field, 61 missing, 20 extra, 3 wrong links);
last listings 776 (ballet: 50 dropped + 26 stored-not-parsed; other lists 0 dropped); stored ends 1,565 (1,469 correct, 79 wrong
type, 10 wrong structure, 7 wrong date); pre-gap 106 (6 dropped, 6 stored-not-parsed).
Order: conventions first (each settles many rows), then mechanical fixes, then identity/links, then print conflicts.

## A. Conventions (RG rules once; many rows follow)
- A1 **Break inside a tenure** («съ X по Y и съ Z»): print never says why. Stored as blank / other / left service inconsistently (~60 rows).
- A2 **Appointments, promotions, transfers out, secondments, military service** («Назначенъ», «Переведенъ въ», «Прикомандированъ»,
  «командирована», «отбываетъ воинскую повинность») -> end_type `other`? Arrivals («Переведенъ изъ», «въ С.-Петербургѣ съ») never an end?
  (~50 rows typed blank/left service; Келеръ, Иващенко, Гейкблюмъ, Бестужевъ-Рюминъ, Адамовъ arrivals stored as ends.)
- A3 **Partial dates** (year only «† 1907 г.», month only «въ мартѣ 1902», season «зимою 1904») -> store partial undate? (~15 rows)
- A4 **Old/New Style double dates** («1/14 марта 1903») -> Old Style like the rest of the corpus? (Бейдлеръ, 3 rows)
- A5 **Double given names** (Лидтке «Готгильдъ Францъ», Больмъ «Адольфъ Эмиль», Ваксманъ «Альфредъ Луи», Пуни «Леонтина-Констанція»):
  all in first_name, patronymic empty?
- A6 **Print-slip years** (Корниловъ «1998», Степановъ «1802», Ѳедоровъ «по 1 іюня 1889», Михайловъ К. А. «1889»): raw stays verbatim;
  research-layer corrected date?
- A7 **ProductionTeam duty phrases** («Мужскіе костюмы всѣхъ труппъ») stored in subject_taught: which field?
- A8 **Graduates 1896-97** (12 rows) stored «left service» with no date: graduation + appointment -> no end?

## B. Mechanical fixes (raw rows, then rebuild; each list approved by RG)
- B1 Restore dropped leaving/death/transfer lines: ballet 1890-1905 (~56 in slice + ~40 seen on the same pages), Борегаръ (PT 1892-93).
- B2 Parse ends from lines already stored but not parsed (~40, incl. «Назначенъ … съ <date>» wording; 88-row upper bound by query).
- B3 Moscow Musicians «Имя Отчество» in first_name -> split (~141-160 rows, 7+ pages).
- B4 Graduates «Surname, Name.» in family_name -> split (~79 rows; whole of 1891-92 p000).
- B5 Wrong-column content: dates/notes in rank_or_title; instruments in rank/subject or missing (print misspelt); tallies copied into
  tenure notes (some with wrong numbers); invented note (Гельцеръ 1909-10); duplicated leaving notes (1910-11 MSK); «Все—10—» (1890-91 MSK).
- B6 Misreads (155 + ALSO notes): д->л (Ѳелоровна, Ланіиловна, Горлова, Герльтъ), к->н (Ахманова, Накорина, Куснова...), others; instruments
  (Тесситоре Гобой, Котрбанъ Вальдгорнъ).
- B7 Non-Russian characters in 11 names (Бочкина Arabic, қ, ү, ї, ў, ă, accents).
- B8 Wrong end kind: Недремская, Никитинъ 1-й († stored as left), Бѣлова (left stored as died), Ежовъ, Симоновъ, Ашитковъ;
  wrong dates: Дьякъ 1899->1900, Лабунская (day lost), Храписъ (comma-shifted), Аслинъ (concurrent post stored as end), Дума (secondment).
- B9 Pipeline: 1908-09 BalletArtists tallies (new format) produce no credit rows.

## C. Identity and links
- C1 Wikidata wrong: Кунстъ, Фричъ, Шмидтъ 1-й; doubtful: Шмидтъ 2-й.
- C2 Review credits: wrong links (Богданова debut, Павлова costumes [Бакстъ missing], О. Николаева, Вагнеръ 1849); non-credits stored as
  credits (1465, 1466, 1472); unresolved with clear person (А. Герберъ x3, Пономаревъ, М. Петипа x3, Н. Г. Легатъ x2); parser faults.
- C3 Merge / split candidates: Шиманъ (prod. list «Г. Шимана»), Золотаренко П. П. (= Петръ, † 1895?), Арендсъ Генрихъ/Андрей, Петипа Марія
  1910-11, Каменскій = Неменскій, Гебгардъ Іосифъ = Эдуардъ, Каффи Иванъ = Дмитрій, Ромашковъ Павелъ/Петръ, Мыльникова = Снѣжинская?,
  print-slip surnames Поповъ/Пановъ, Романовъ/Рахмановъ 2-й, Куришенская; guests Гельцеръ, Балашова, Кузнецовъ 2-й to link.
- C4 Deaths: ~10 catalogue deaths in the last listed season with no stored death (overlaps B1).

## D. Print conflicts (data faithful; RG decides which reading stands)
Константиновъ † 25 vs 27 Dec 1906; Тройниковъ, Цалисонъ gap ends; Ѳедорова 2-я left 1901 vs 1902 (and listed 1903-04); Кувакина;
Потаповъ 1909 vs 1910; Иванова 2-я († Feb 1907, listed 1907-08); Левинсонъ 1-я; Мыльникова; Голубинъ 1-й drift; Романова 1889/1899;
Егорова Марія Николаевна (left 1902, listed 1903-04); Дмитріева 1-я (left 1897, listed 1898-99); Броневскій-Боянусъ, Гущинъ.
