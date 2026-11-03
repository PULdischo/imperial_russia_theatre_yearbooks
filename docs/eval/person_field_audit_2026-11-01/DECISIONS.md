# Person field audit — decision list (2026-11-02)

All readings "checked by Claude" (finding aids); evidence per item in `slices/*_results.csv`. Nothing applied yet.
Totals: flags 1,565 read (981 match print, 200 print slips, 155 misreads, 101 wrong field, 61 missing, 20 extra, 3 wrong links);
last listings 776 (ballet: 50 dropped + 26 stored-not-parsed; other lists 0 dropped); stored ends 1,565 (1,469 correct, 79 wrong
type, 10 wrong structure, 7 wrong date); pre-gap 106 (6 dropped, 6 stored-not-parsed).
Order: conventions first (each settles many rows), then mechanical fixes, then identity/links, then print conflicts.

## A. Conventions (RG rules once; many rows follow)
- A1 **RULED 2026-11-02 (RG): blank unless printed** — a break gets a type only where some volume prints the reason with that same date (e.g. Волковъ «Оставилъ службу 1 января 1893 г.»); otherwise blank.
  Was: **Break inside a tenure** («съ X по Y и съ Z»): print never says why. Stored as blank / other / left service inconsistently (~60 rows).
- A2 **RULED 2026-11-02 (RG, in the forked side session «btw: explain the pros/cons of this»: "okay, let's do option 3")**:
  moving OUT of a post (appointment elsewhere, permanent «Переведенъ въ…», «Назначенъ…» to another post) ends the period, end_type `other`;
  ARRIVING in the listed post («Переведенъ изъ…»; Келеръ 1906-07, Иващенко, Гейкблюмъ, Бестужевъ-Рюминъ, Адамовъ) is never an end;
  a TEMPORARY ASSIGNMENT («откомандирована», «командирована», «прикомандированъ») never ends or splits the tenure — recorded as its own
  dated assignment beside the unbroken tenure. Why: Шидловская «Откомандирована въ С.-Петербургъ съ 1 сентября 1908 г. по 1 мая 1909 г.»,
  yet 1910-11 prints her tenure as «(съ 1 августа 1907 г.)» — the Directorate counted it unbroken. Cases: Шидловская, Дума (NB not listed
  after 1908-09), Рѣпина 1901-02, Андреевъ 1899-00, Петровъ 1898-99.
  A2b **RULED 2026-11-02 (RG, same side session: "okay i agree, go ahead")**: temporary assignments go in a SEPARATE table, not a new
  period type in person_entry_service (keeps tenure/left-service logic untouched). Rough shape: person_id, entry_id, start/end text+undate,
  destination, kind (seconded / attached), printed_line verbatim. ~5 rows; their stored secondment ends are removed from service.
  Was: **Appointments, promotions, transfers out, secondments, military service** («Назначенъ», «Переведенъ въ», «Прикомандированъ»,
  «командирована», «отбываетъ воинскую повинность») -> end_type `other`? Arrivals («Переведенъ изъ», «въ С.-Петербургѣ съ») never an end?
  (~50 rows typed blank/left service; Келеръ, Иващенко, Гейкблюмъ, Бестужевъ-Рюминъ, Адамовъ arrivals stored as ends.)
- A3 **RULED 2026-11-02 (RG): store with precision** — year / month / season as printed, with a precision marker; printed text verbatim; nothing invented.
  Was: **Partial dates** (year only «† 1907 г.», month only «въ мартѣ 1902», season «зимою 1904») -> store partial undate? (~15 rows)
- A4 **RULED 2026-11-02 (RG): "Keep as is in the raw layer, convert to O.S in the research layer."** Raw keeps the stored New-Style dates; research layer uses Old Style.
  Was: **Old/New Style double dates** («1/14 марта 1903») -> Old Style like the rest of the corpus? (Бейдлеръ, 3 rows)
- A5 **RULED 2026-11-02 (RG): both in first name** — second given name joins first_name (hyphen kept where printed), patronymic empty.
  Was: **Double given names** (Лидтке «Готгильдъ Францъ», Больмъ «Адольфъ Эмиль», Ваксманъ «Альфредъ Луи», Пуни «Леонтина-Констанція»):
  all in first_name, patronymic empty?
- A6 **RULED 2026-11-02 (RG): raw as printed, research layer corrected** — editorial correction marked with its evidence; misspelled months («вктября», «севтября», «юня») get their obvious date in the research layer.
  Was: **Print-slip years** (Корниловъ «1998», Степановъ «1802», Ѳедоровъ «по 1 іюня 1889», Михайловъ К. А. «1889»): raw stays verbatim;
  research-layer corrected date?
- A7 **RULED 2026-11-02 (RG): own 'duties' field** — all ~91 printed responsibility phrases (7 in subject_taught, 84 in tenure notes) move verbatim to a new duties field; tenure note keeps dates. Musicians «Ударные инструменты» x2 -> instrument (fix list).
  Was: **ProductionTeam duty phrases** («Мужскіе костюмы всѣхъ труппъ») stored in subject_taught: which field?
- A8 **SETTLED by A2 (2026-11-02):** note reads «съ 1-го сентября 1897 года, въ Московскую балетную труппу.» = arrival in the troupe, never an end -> drop the 12 dateless 'left service' ends.
  Was: **Graduates 1896-97** (12 rows) stored «left service» with no date: graduation + appointment -> no end?

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

## Applied to production (2026-11-02)
- B1 restored ends: 129 (2fe5d52). B3/B4/A5 name fields: 262 (4e608fe). B6/B7 name misreads + stray characters: 95 high (4071d3f;
  Бочкина 1890-91 rejoined her record). B5 wrong-field contents: 67 high (911c09f). B8 end kinds/dates by A1/A2/A8 + readings: 202 (e63cad6).
## Still open
- BUILT 2026-11-02 (6648807): research.service_period (A3 partial dates, A4 O.S., A6 corrections CSV), research.person_assignment (A2b, 16),
  costumers' area of work = person_appearance.title (A7; a separate duties column would have duplicated title, dropped). Ѳедоровъ «1 іюня 1889»
  (1899-00 musicians) RULED 2026-11-02 (RG): 1 June 1899, added to the A6 corrections.
- Pipeline bugs FIXED 2026-11-03 (RG "Yes, parser bugs"): (1) parse_and_validate._repair_musicians_rank_or_title appended a
  service line from rank_or_title to a note that already held it -- 3 notes doubled (1910-11 MSK musicians Фридрихъ, Цозель, Юмрихъ);
  now skips a part the note already contains. (2) build_duckdb read the parsed CSVs with a sniffed format; person_entry_service.csv
  has one quoted value (Храписъ 1910-11 «съ 1 іюня, 1908 г.»), so the sniffer chose no quoting and shifted that row one column.
  Quote/escape now stated; checked all 5 tables, no other row read differently. Raw diff v. backup: exactly 3 notes + 1 service row.
  Side effect: the shifted row had split Храписъ Георгій into two people; now one (4143fc41, 1908-09..1910-11, start 1 June 1908),
  eb5c1063 superseded by the builder; no file referenced it. research.person 2,620 -> 2,619, live 2,522 -> 2,521.
- Held medium rows DONE 2026-11-02 (RG "Apply all 10"): 15 field edits on 10 entries, B5_B6_held_applied_2026-11-02.csv; Борхманъ «Алольфовичъ» already ruled a print typo (genuine_print_typos.md, 2026-10-07); Эйхенвальдъ «Надежла» stored «Надежда» (RG: worn д; fix_eichenwald_1897-98.csv).
- Undated transfers DONE 2026-11-02 (RG "Yes, borrow dates"): B9_undated_transfers.csv sets end_type other on Ветцель 1902-03,
  Липинъ 1903-04, Кякштъ 1903-04, Боборыкинъ 1900-01, and adds an undated period (other) to Боборыкинъ's 1901-02 Moscow reprint.
  Research layer takes the date another printing gives: Козловъ MSK 1902-03 -> 1 Sept 1901 (1900-01 MSK), Ветцель -> 1 Sept 1902,
  Липинъ -> 1 Sept 1903 (receiving list, same volume); Боборыкинъ, Кякштъ stay undated. Кякштъ tenure note: one Moscow season
  1903-04 (Moscow review: debut «г-на и г-жи Кякштъ»), back in the SP lists 1904-09 with the same start.
  «Освобожденъ отъ обязанностей» RULED 2026-11-02 (RG "Keep as post end", "as long as we can see that they left certain roles but
  stayed on"): no change. Each line sits in the post's own entry (Аслинъ «Репетиторъ балета» ends 1 Nov 1905; Ширяевъ «Второй
  балетмейстеръ» ends 1 Mar 1905), end_type other (A2); the man's «Артисты» entries carry on (Аслинъ listed to 1910-11, Ширяевъ to
  1907-08). Visible by joining research.service_period (end_type other) to later research.person_appearance rows in the same list
  and city: 171 of 210 other-ends are followed by a later listing. Not research.person_assignment (A2b is for temporary postings).
  Хмелевскій RULED 2026-11-02 (RG "Yes, other, undated"; row 6 of B9_undated_transfers.csv): «Назначенъ и. д. машиниста-механика Новаго театра,» (1900-01, no date in print; scan
  docs/eval/scan_audit/1900-01_productionteam_p128_khmelevsky_new_theatre.png). Logged, not acted on: his new-post entry the same
  page prints «съ 29 марта 1879 г.» (clear 29; all other volumes 27).
- Held for RG (was): 7 medium misreads (B6), 10 medium wrong-field rows (B5), 9 undated ends (B1), «Освобожденъ отъ обязанностей» (Аслинъ, Ширяевъ),
  1908-09 BalletArtists tallies DONE 2026-11-03 (RG "Add them"): most were fixed 2026-10-30 (known_issues, italic «Всего» sentence);
  two pages (SP p000, MSK p007) came back with no credits on any entry, 8 dancers with a printed tally. raw_fix_1908-09_missing_credits.py
  built 26 rows from the 2026-10-30 scan-checked text (roles sum to the printed total for all 8). Diff v. backup: only raw/analysis
  person_entry_credit +26, other 57 tables identical (credit rows feed no research table). Logged, not in scope: 6 1892-93 decorators
  with «Всего—N декорацій» and no credit rows (productionteam_1892-93_p000).
- Будаевъ DONE 2026-11-03 (RG "Fix both"; B10_rank_field_fixes_2026-11-03.csv + B10_service_period_add.csv): 1908-09 rank_or_title
  held «Первая скрипка. (Переведенъ …)», already in instrument + tenure note -> emptied. Corpus search for rank fields with dates/notes/
  instruments found one more: Михайловъ Георгій, Administration 1909-10 p.143 no.3, rank -> «пот. поч. гражд.», tenure note
  «(по найму съ 7 января 1885 г.)», service start 7 Jan 1885 added (that season had none). Будаевъ's violin part alternates
  Первая/Вторая in print after his 1902 promotion (1904-05 Mar., 1905-06, 1907-08 «Вторая», scan-read by Claude): left as printed.
- C identity/links and D print conflicts: not started.

## D. Print conflicts -- RULED 2026-11-02 (RG): "contemporaneous wins"
When later volumes reprint a past date differently, the research layer uses the printing from the time of the event; raw stays as
printed (21 corrections in pipeline/research_corrections/service_period_date_corrections.csv: Цалисонъ 1900, Голубинъ 1-й 1894 /
16 Sept 1897, Тройниковъ 1 Dec 1896 / 16 Feb 1897, Гиллертъ іюля 1875/1879; Гиллертъ's start slip also in person_start_date_slips.csv).
Then RG 2026-11-02: Потаповъ -> 12 Dec 1909 (rule applies: 1910-11 reprints 1909-10 leavers unchanged, only his date changed);
Кувакина (23 Aug vs 1 Sept 1904) and Константиновъ († 25 vs 27 Dec 1906, same volume) -> leave both printings, conflict noted here;
Ѳедорова 2-я Лидія -> KEEP the 19 Oct reading «two periods (possibly continuous)» (on the roster 17 of 18 volumes, absent 1904-05;
8 SP review mentions of «Ѳедорова 2-я» 1903-07 added as corroboration; those mentions are still unlinked in the review layer).
Still to put to RG: and the listed-after-leaving cases (Иванова 2-я, Левинсонъ 1-я, Егорова М. Н.,
Дмитріева 1-я, Броневскій-Боянусъ, Гущинъ, Смирнова).

- Scan-check batch 2026-11-03 (RG "do the ones that require a scan check"; scans read by Claude, crops in docs/eval/scan_audit/):
  Больмъ FIXED (RG "Fix Больмъ"; B11_bolm_spellings_2026-11-03.csv): print reads «Больмъ, Адольфъ(-)Эмиль» in 1903-04 p.74, 1905-06 p.20,
  1909-10 p.96; stored «Болъмъ» x2, «Болмъ», «Адолльфъ», «Эмилъ» (1909-10 split as first «Адольфъ» + patronymic «-Эмилъ») were misreads;
  6 field edits. Production rebuilt once by the research-layer session from raw after a write collision (2026-11-03 10:58; damaged file
  kept as outputs/full_run/imperial_theaters.corrupted_clash_2026-11-03.duckdb); checked: 8 entries -> 3a1cd225, metrics unchanged.
  1908-09 Куришенская Вильгельмовна / Поповъ / Романовъ: printed as stored, print slips, linked to the right people (genuine_print_typos.md).
  Егорова 1899-00 no.34 / 1900-01 p.73 no.33: print «Егорова 2-я, Марія Николаевна (съ 7 іюня 1882)» as stored; #54 stays RG's call.
  Ѳедорова: 1906-07 «Ѳедорова 2-я» x4 (roster 2-я = Лидія) and «Ѳедорова 1-я» x1 unlinked; lists 1904-05/1906-07 spell «Федорова».
  1904-05 review p.118 «Ѳедорова 2-я, 1-я» are in a quoted 1875 cast of «Голубая Георгина»: 9 of 21 mentions in that passage linked to
  later people (e.g. «Готье» role -> Готье Теофиль, «Л. Ивановъ» -> Иванова Лариса, «Ѳедорова 1-я» -> Марія Дмитріевна). For RG next.
