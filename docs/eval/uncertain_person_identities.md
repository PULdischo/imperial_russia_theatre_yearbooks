# Uncertain person identities -- merges and non-merges to revisit with outside research

RG's standing list (started 2026-10-05). Every person-identity decision where the yearbooks alone do not settle whether two records are **one man or two** goes here, whichever way it was decided, so it can be picked up later for external research (directories, archives, biographies). Clear-cut decisions do not belong here; they are in `docs/eval/person_merge_candidates_batch.md` and `docs/eval/known_issues.md` (issue #134).

**How to use an entry.** *Status* says how the database currently treats the case: MERGED (one person), SPLIT (two persons), or OPEN (not decided). *Where to look* gives the person-id prefixes and entry ids to find the printed lines (`raw.person_entry`, scans in `outputs/roster_images_full/images/<page_id>.png`; a timeline script is `docs/eval/homonym_sweep_2026-10-05/timeline.py <id prefix>`). *Would resolve it* names the kind of outside source that could settle it. For Petersburg residents, the "Весь Петербургъ" directory lookup (1894-1917) is the reusable tool (see memory note on it).

To add an entry: copy the template at the bottom.

---

## 1. Зандинъ Михаилъ -- patronymic Ивановичъ or Павловичъ?

- **Status:** MERGED (RG, 2026-10-05) into one person (831b71...). Display patronymic is a 2-2 tie between the printings and can flip on a rebuild.
- **What is uncertain:** the same decorator is printed "Ивановичъ" in 1906-07 and 1907-08 (Помощники декораторовъ) and "Павловичъ" in 1908-09 and 1909-10 (Исп. об. главнаго Декоратора). All four lines were read at 4-5x.
- **For one man:** same first name; start date "съ 1 мая 1907" printed in 3 of 4 volumes (the fourth prints 1887, an apparent typo); a clear promotion path; no season overlap.
- **For two men / against:** only the patronymic differs, but it differs in a way a printer's slip would explain either way; no outside source checked.
- **Where to look:** `productionteam_1906-07_p000__e009`, `productionteam_1907-08_p000__e007`, `productionteam_1908-09_p000__e004`, `productionteam_1909-10_p000__e003`.
- **Would resolve it:** a theatre-artist biography/dictionary (Mikhail Zandin, decorator at the Mariinsky); Весь Петербургъ entries for 1907-1910.

## 2. Лебедевъ Иванъ (ProductionTeam, Бутафоръ) -- patronymic Васильевичъ or Афанасьевичъ?

- **Status:** MERGED (RG, 2026-10-05): the 1907-08 row (Васильевичъ) with the 1908-10 rows (Афанасьевичъ), person ea76e8...; display patronymic is a tie and can flip.
- **For one man:** identical start date "съ 3 іюня 1889" (the 1908-09 row prints "1 іюня 1899", an apparent typo), same Маріинскій театръ Бутафоръ post, no season overlap.
- **Against:** the patronymic differs; common name.
- **Where to look:** `productionteam_1907-08_p001__e021`, `productionteam_1908-09_p001__e002`, `productionteam_1909-10_p001__e002`.
- **Would resolve it:** Весь Петербургъ (prop-makers of the Mariinsky workshops); staff registers.
- **Note:** this person was previously glued to a Moscow flautist and a Petersburg clarinetist (also Лебедевъ Иванъ); that was split as a clear error (person 1dd355).

## 3. Николаевъ Иванъ Николаевичъ -- Moscow ballet artist or the machinist? (possibly two men)

- **Status:** MERGED (split applied 2026-10-05, then reverted at RG's request because the evidence was thin): person 3f4bfd... holds both.
- **For one man:** the start dates are only a year apart ("съ 16 августа 1899" in the ProductionTeam list, "съ 1 августа 1900" in the ballet list); dual listings of one man in two lists are common; the ballet side is a single entry.
- **For two men:** same season (1909-10) and city (Moscow) but different kinds of job (assistant to the machinists-mechanics vs a ballet-company entry, no. 29); different start dates; very common name.
- **Where to look:** `productionteam_1908-09_p003__e006`, `productionteam_1909-10_p003__e006`, `balletartists_1909-10_MSK_p000__e009`. (A different, earlier ProductionTeam "Николаевъ Иванъ", младшій помощникъ at the Bolshoi since 15 апрѣля 1904, 1905-08, is a separate person e4abb5... and probably a third man.)
- **Would resolve it:** the ballet entry's roles (the stats line on the scan; a machinist would not dance), Moscow theatre staff lists 1909-1910; Весь Москва directory if available.

## 4. Логиновъ Сергѣй Андреевичъ -- one trumpeter or two? (possibly two men)

- **Status:** MERGED (RG, 2026-10-05): one person (4240d1...), Petersburg 1904-06 and Moscow 1905-10.
- **For one man:** he appears in no Petersburg list before 1904-05 (the trumpet roster there is steady at 9-11 players for 1890-1904); his Petersburg run (1904-05, 1905-06) ends exactly as the Moscow run (1905-06 to 1909-10) begins; the Moscow start date "съ 1 сентября 1904" equals his first Petersburg season.
- **For two men:** the Petersburg entries print "съ 1 сентября 1894" in both volumes (digits read at 8-12x on the scan, clear); in 1905-06 he is listed in both cities with different instrument lines (Труба / Вторая труба) and no transfer note.
- **Where to look:** `musicians_1904-05_SP_p002__e013`, `musicians_1905-06_SP_p002__e035`, `musicians_1905-06_MSK_p002__e029`, `musicians_1906-07_MSK_p002__e014`, and later Moscow years. The printed "1894" is recorded in `docs/eval/genuine_print_typos.md`.
- **Would resolve it:** a Moscow Bolshoi orchestra roster 1905; a record of a transfer from the Petersburg to the Moscow orchestra; Весь Петербургъ 1905.

## 5. Ѳедорова Марія Дмитріевна (ballet, Petersburg) -- printed leaving note in 1904-05, listed again 1905-08

- **Status:** MERGED, OPEN for research (RG, 2026-10-05: "keep merged, leave it OPEN"): one person (2475a6...), 1890-91 to 1907-08, 19 entries.
- **What is uncertain:** the 1904-05 volume prints, under no. 114, "Федорова 1-я, Марія Дмитріевна (съ **1 іюня** 1885 г.) ... Оставила службу **1 іюня 1905** г." (zoomed 2x on the scan: both clear). Yet "Ѳедорова, Марія Дмитріевна (съ **12 мая** 1885 г.)" is listed again in 1905-06 (no. 119), 1906-07 (no. 102) and 1907-08 (no. 125), with the same start date as 17 other volumes. The ordinal changes across volumes (3-я 1890-95, 1-я 1896-97 and later). The 1904-05 start date (1 іюня) and the 1903-04 one (2 мая) are variants of the usual 12 мая.
- **For one woman:** same name, patronymic, list and start date (12 мая 1885) in the later volumes; a return would be printed with a break, as for Цалисонъ on the same page ("по 1 января 1900 г. и съ 1 сентября 1902 г."); the same note "Оставила службу 1 іюня 1905 г." is printed under no. 125 Щедрина (start 12 мая 1885, absent after 1904-05), so the 1904-05 note may have been attached to the wrong woman.
- **For two women / against:** the note is printed clearly under no. 114; the 1904-05 line carries its own statistics (8 ballets, 18 times); nothing printed explains a return.
- **Where to look:** `balletartists_1904-05_SP_p005__e003` (no. 114) and `__e014` (no. 125 Щедрина); later lines of person 2475a6... (1905-06 p005 e008, 1906-07 p005 e006, 1907-08 p006 e001). The stored `service_periods` of the 1904-05 line keeps the printed "left service 1 июня 1905".
- **Would resolve it:** ballet personnel lists 1905-1908; the 1905 retirement list of the Petersburg ballet; biographical sources on Petersburg ballet dancers named Федорова.

## 6. Марквардтъ Августъ (Moscow Musicians) -- RESOLVED, kept for reference

- **Status:** MERGED (RG, 2026-10-05; not uncertain): one person (230477...), 30 entries, 1890-91 to 1905-06. The two records held complementary seasons of one orchestra line, plus the bandmaster line ("Капельмейстеръ военной музыки", since 15 августа 1884); the orchestra line itself prints "(онъ же и капельмейстеръ военной музыки)" (since 19 сентября 1882, left 1 іюля 1903 per 1902-03; 1904-05 repeats the leaving note).

## 7. Шнейдеръ Карлъ Ѳедоровичъ (Petersburg Musicians, trombone) -- the 1902-08 and 1908-10 lines: one man?

- **Status:** MERGED (RG, 2026-10-05, "merge, but add to the uncertain list"): one person (019ed1...), 8 entries, 1902-03 to 1909-10. (The earlier worry, a second "Шнейдеръ" overlapping in 1908-10, was in fact the percussionist Шредеръ's lines being attached to him -- see entry 12.)
- **What is uncertain:** the trombonist prints "Шнейдеръ, Карлъ Ѳедоровичъ (съ 1 сентября **1902**)" in the Mikhailovsky orchestra list 1902-03 to 1907-08 (1907-08 is the last year of the "Бывшій оркестръ Михайловскаго театра") and "(съ 1 сентября **1907**)" in the combined Petersburg orchestras list in 1908-09 and 1909-10, with no transfer note.
- **For one man:** same name, patronymic and instrument; one trombone line per season, no overlap; the new start date fits a transfer into the combined orchestra in 1907 (the percussionist's 1906 transfer from the same orchestra is printed as "Переведенъ изъ Михайловскаго театра съ 1 сентября 1906").
- **For two men / against:** the start date changes 1902 -> 1907 with no printed transfer; two trombonists named Карлъ Ѳедоровичъ Шнейдеръ would be an odd coincidence, but the second could be a new hire.
- **Where to look:** `musicians_1907-08_SP_p004__e035` (no. 19, last Mikhailovsky line), `musicians_1908-09_SP_p004__e008` (no. 118), `musicians_1909-10_SP_p004__e014` (no. 120).
- **Would resolve it:** a Mariinsky orchestra roster 1907-1910; Весь Петербургъ; the 1907 order merging the Mikhailovsky orchestra into the Mariinsky one.

---

## 8. Волконскій князь Григорій Дмитріевичъ -- one man in two unrelated posts, or two princes Волконскіе?

- **Status:** MERGED (RG, 2026-10-05, "fine for now, label as uncertain"): five live persons joined into 68fa76... (20 entries, 1890-91 to 1901-02).
- **What is uncertain:** the same name, rank and patronymic appears in two very different jobs: **Начальникъ искусственнаго освѣщенія** (head of artificial lighting; ProductionTeam, "съ 1 сентября 1887 г.", 1890-91 to 1897-98, "Оставилъ службу 1 сентября 1898 г.") and **teacher of Географія in the ballet department of the Petersburg school** (TheaterSchoolStaff, "Преподаватели / а) Балетное отдѣленіе", "съ 1 сентября 1888 г.", 1890-91 to 1901-02, "Оставилъ службу 1 сентября 1901 г.").
- **For one man:** identical name, patronymic and title (кн. / князь) in both lists every year; start dates one year apart; exactly one line per list per year; no conflict or overlap; the person was split into five records only by the old "князь/кн." name scramble.
- **For two men / against:** a lighting engineer teaching school geography is an unusual combination; the two posts end three years apart; no source says one prince held both.
- **Where to look:** ProductionTeam lines `productionteam_1890-91_p003__e010` ... `productionteam_1897-98_p002__e028`; school lines `theaterschoolstaff_1890-91_p004__e011` ... `theaterschoolstaff_1901-02_p003__e019` (list numbers 3-5).
- **Would resolve it:** a biography of the prince (Григорій Дмитріевичъ Волконскій, Imperial Theatres lighting department / Theater School); Весь Петербургъ 1894-1901 entries under Волконскій for his occupation and address.

## 9. Петровъ Иванъ Степановичъ (TheaterSchoolStaff) -- the tutor and the preparatory-class teacher: one man or two?

- **Status:** MERGED (RG, 2026-10-05, "merge and add to the uncertain list"): two live persons joined into 527973... (20 entries, 1890-91 to 1909-10).
- **What is uncertain:** a **Воспитатель** (tutor; "съ 1 сентября 1891 г."; rank кол. асс. 1898-1905, надв. сов. 1906-08; 18 entries, 1890-91 to 1907-08) and a teacher in **Учителя приготовительныхъ классовъ** ("съ 15 ноября 1907 г."; 1908-09 and 1909-10) share one name and patronymic.
- **For one man:** same school, name and patronymic; the tutor line ends exactly where the teacher line begins; he is never in both lists in one season.
- **For two men / against:** the start dates differ and no volume prints a transfer; the 1907-08 volume still lists him as tutor although the teacher post is dated 15 Nov 1907; Петровъ Иванъ is a very common name.
- **Where to look:** `theaterschoolstaff_1907-08_p000__e020` (last tutor line), `theaterschoolstaff_1908-09_p002__e003`, `theaterschoolstaff_1909-10_p002__e006`.
- **Would resolve it:** Весь Петербургъ 1908-1910 (a school tutor or teacher named Петровъ Иванъ Степановичъ); a school staff register.

## 10. Жукова Вѣра Васильевна -- the ballet artist "Жукова 1-я" and the later dance teacher: one woman or two?

- **Status:** SPLIT (RG, 2026-10-05, "teachers merged; dancer separate, labelled uncertain"): the dancer is person c03d21... (1 entry, 1890-91); the dance teacher is 3e22b9... (9 entries, 1901-02 to 1909-10, merged from two records).
- **What is uncertain:** "Жукова 1-я, Вѣра Васильевна" is a Petersburg ballet artist in the 1890-91 volume ("съ 22 іюля 1869 г.", "Оставила службу 1 марта 1891 года"). From 1901-02 a "Жукова, Вѣра Васильевна" teaches Танцы (from 1908-09 Классическіе танцы) in the Petersburg ballet department, "съ 1 сентября 1901 г.".
- **For one woman:** identical name and patronymic; a retired dancer becoming a dance teacher ten years later is a normal path.
- **For two women / against:** a ten-year gap; no volume prints a link between the two; the teacher's printed start date gives no earlier service; the "1-я" ordinal marks a surname shared by several dancers.
- **Where to look:** `balletartists_1890-91_SP_p001__e023`; `theaterschoolstaff_1901-02_p001__e028` and later lines of person 3e22b9...
- **Would resolve it:** a ballet-artists dictionary or the Mariinsky dancers' lists 1869-1891 for Жукова В. В.; Весь Петербургъ 1901-1910 (teacher at the Theater School).

## 11. Рыхлякова 1-я Варвара Трофимовна -- the ballet artist and the 1909-10 school-teacher line: one woman?

- **Status:** MERGED (RG, 2026-10-05, "merge, but add to the uncertain list"): the single TheaterSchoolStaff entry (1909-10, former record 5d6d24...) joined to the ballet artist 87c046... (21 entries, 1890-91 to 1909-10).
- **What is uncertain:** `theaterschoolstaff_1909-10_p001__e024` lists "Рыхлякова, Варвара Трофимовна" among the Petersburg school's ballet-department teachers ("съ 1 ноября 1907 г."), with no subject printed (scan-checked 2026-10-05, p. 146, no. 18: the line ends after the date; the 23 other teachers on that list all print a subject); the ballet artist Рыхлякова 1-я of the same name and patronymic is in the Petersburg troupe that season (start "съ 1 іюня 1890", printed "1 сентября 1890" in 1904-05 and 1908-10).
- **For one woman:** same name, patronymic, city and season; rare surname; dual dancer/teacher listings are common (Преображенская Ольга has both in 1900-01).
- **For two women / against:** no other volume lists her as a teacher; the teaching start (1907) is unrelated to her company start; the printed line gives no subject, so the post is not identified.
- **Where to look:** `theaterschoolstaff_1909-10_p001__e024` (scan-checked: no subject printed); `balletartists_1909-10_SP_p004__e008`.
- **Would resolve it:** Весь Петербургъ 1908-1910; a ballet-school staff list for 1907-08 and 1908-09 (the entry begins "1 ноября 1907", yet the 1907-08 and 1908-09 volumes list no such teacher).

## 12. Шредеръ Карлъ (percussion) 1907-10 -- the patronymic and start date change to the trombonist's

- **Status:** MOVED (RG, 2026-10-05, "most likely"): the three lines of 1907-08, 1908-09 and 1909-10 (`musicians_1907-08_SP_p003__e019`, `musicians_1908-09_SP_p004__e011`, `musicians_1909-10_SP_p004__e016`) were taken off the trombonist Шнейдеръ (019ed1...) and attached to the percussionist **Шредеръ Карлъ Августовичъ** (cd67fa...; 1903-04 to 1909-10, 7 entries).
- **What is uncertain:** the percussionist prints "Шредеръ, Карлъ **Августовичъ** (съ 1 декабря **1894**)" every season to 1906-07 (1906-07 adds "Переведенъ изъ Михайловскаго театра съ 1 сентября 1906"). From 1907-08 the same chair, in the same alphabetical position (between Штейнсъ and Шуманъ), prints "Шредеръ, Карлъ **Ѳедоровичъ** (съ 1 сентября **1902**)", exactly the patronymic and start date of the trombonist **Шнейдеръ, Карлъ Ѳедоровичъ** (Mikhailovsky orchestra, since 1 Sept 1902; Mariinsky list from 1908-09 with "съ 1 сентября 1907"). All eleven lines were blind-read on the scans and confirmed as stored (`docs/eval/schneider_check_2026-10-05/`).
- **For one percussionist:** continuous chair and list position; a trombone line and a percussion line print in the same list in 1908-10 (118 / 121 and 120 / 122), so the percussion lines cannot belong to the trombonist; the changed patronymic and date look like a yearbook slip that borrowed the trombonist's details when the Mikhailovsky orchestra was merged in 1907-08.
- **For a different man:** a new percussionist Шредеръ Ѳедоровичъ (hired 1902 per the print) taking the chair from 1907, with Августовичъ gone exactly then; the print is taken at face value.
- **Where to look:** the three entries above; `musicians_1906-07_SP_p003__e025` (last Августовичъ line); the trombonist's lines `musicians_1907-08_SP_p004__e035`, `musicians_1908-09_SP_p004__e008`, `musicians_1909-10_SP_p004__e014`.
- **Would resolve it:** a Mariinsky orchestra roster 1907-1910 (Весь Петербургъ; staff lists of the Directorate) naming the percussionist (Шредеръ К. А. or К. Ѳ.).

## 13. Цыбинъ Владіміръ Николаевичъ (Musicians, flute) -- Moscow 1897-1908, Petersburg 1907-10: one man?

- **Status:** MERGED (RG, 2026-10-05, "merge, and add to the uncertain list"): one person (58db32...), 10 entries, 1900-01 to 1909-10.
- **What is uncertain:** a flautist "Цыбинъ, Владіміръ Николаевичъ (съ 1 апрѣля 1897 г.)" is in the Moscow orchestra list 1900-01 to 1907-08; from 1908-09 a flautist of the same name and patronymic is in the Petersburg orchestras list with "(съ 1 сентября 1907 г.)". No transfer note is printed in either city.
- **For one man:** identical name, patronymic and instrument; rare surname; consecutive seasons; a move to the Petersburg orchestra would explain the new start date.
- **For two men / against:** the 1907-08 Moscow volume still lists him although the Petersburg start date is 1 Sept 1907; no printed transfer; the start date resets 1897 -> 1907 (the same pattern as entry 4, Логиновъ, in the opposite direction).
- **Where to look:** `musicians_1907-08_MSK_p003__e001` (last Moscow line), `musicians_1908-09_SP_p003__e035` (first Petersburg line), `musicians_1909-10_SP_p004__e006`.
- **Would resolve it:** the Moscow and Petersburg orchestra rosters for 1907; Весь Петербургъ 1908-1910 (a flautist Цыбинъ at the Mariinsky or the Mikhailovsky).

## 14. Завѣтновскій (Petersburg Musicians, second violin) -- who is the "Викторъ" of 1908-10?

- **Status:** OPEN, parked (RG, 2026-10-05; RG ruled out "three separate men"). Currently three live persons: 1c7f9e... (Викторъ, 1901-02 and 1902-03), 2658b3... (Николай, 1904-05 to 1907-08), 33ecbf... (Викторъ, 1908-09 and 1909-10). Nothing merged.
- **What is uncertain:** 1c7f9e is "Завѣтновскій, Викторъ Александровичъ, Вторая скрипка (съ 1 сентября 1901 г.)", left 1 сентября 1902. 2658b3 is "Николай Александровичъ (съ 15 октября 1904 г.)", first then second violin. 33ecbf (1908-09 no. 43, 1909-10 no. 44, both read on the scans) is "Викторъ Александровичъ (съ **15 октября 1904** г.). Вторая скрипка." -- Николай's start date and instrument with Виктор's first name.
- **Option A (merge into the Николай, 2658b3):** identical start date and instrument; list position continues 39, 43, 44; no Николай after 1907-08; the first name would be a print slip or change. **Option B (merge into the 1901-02 Викторъ, 1c7f9e):** the first name matches; but the 1904 start date, the absence in 1904-08 and Николай's identical date speak against a rehire. **Option C (three men):** ruled out by RG as an implausible coincidence of start dates.
- **Where to look:** `musicians_1908-09_SP_p002__e002` (no. 43), `musicians_1909-10_SP_p002__e008` (no. 44), `musicians_1907-08_SP_p001__e019` (Николай, no. 39), `musicians_1901-02_SP_p005__e022`, `musicians_1902-03_SP_p005__e032`.
- **Would resolve it:** Petersburg orchestra rosters 1904-1910 (Весь Петербургъ; the Directorate's staff lists) naming the violinists Завѣтновскій; the 1904 hiring order.

## 15. Новикова Екатерина (Moscow Graduates 1899-00) -- is she the dancer Екатерина Дмитріевна?

- **Status:** MERGED (RG, 2026-10-05, "probably, but mark uncertain"): the 1899-00 graduate line (former record 4c598c...) attached to the Moscow dancer **Новикова Екатерина Дмитріевна** (41f0d4...; 11 entries, 1899-00 to 1909-10).
- **What is uncertain:** `graduates_1899-00_p001__e008` (Moscow school, ballet pupils, no. 8) prints "Новикова, Екатерина" with no troupe note and no patronymic. The Moscow dancer Екатерина Дмитріевна is first listed in 1900-01 with "съ 1 сентября 1900 г." -- the date the 1899-00 class would join -- but no printed note links them.
- **For:** same first name and surname; Moscow school; the dancer's start date is the 1 Sept after the graduation; she appears the year after, and no other Новикова Екатерина joins in 1900.
- **Against:** no troupe note and no patronymic on the graduate line; Новикова Екатерина Александровна (d321f3) is in the same troupe, but she joined in 1892 and has her own graduate line (1891-92, attached with RG's yes).
- **Where to look:** `graduates_1899-00_p001__e008`; `balletartists_1900-01_MSK_p003__e021` (Екатерина Дмитріевна's first line).
- **Would resolve it:** the Moscow school's 1900 graduation list with the troupe engagements; a Moscow ballet personnel list for 1900-01.

## 16. Трубецкой, князь И. Ю. (ballet lists + reviews) -- is he Иван Юрьевич Трубецкой (1841-1915), and why does the Petipa Society say "Nikita"?

- **Status:** OPEN (RG, 2026-10-10, "not sure" on the creators review page). The creator stays as printed (`trubetskoy`, no Wikidata link).
- **What is uncertain:** whether the composer-librettist "князь И. Ю. Трубецкой" is the Wikidata person Ivan Yuryevich Trubetskoy, [Q107119063](https://www.wikidata.org/wiki/Q107119063) (born Paris 29 Dec 1841, died 9 June 1915). That item is a genealogy record with no occupation and no Wikipedia article.
- **For:** the yearbook prints "И. Ю." twelve times, for two works: Кипрская статуя (Moscow ballet lists 1890-91..1897-98; reviews 1890-91, 1891-92) and the opera Мелузина (Moscow, 10 Jan 1895, text by Ш. Нюитеръ; 1894-95 opera review). Name, patronymic and dates of the Wikidata person fit.
- **Against / conflict:** the Petipa Society page [Pygmalion, or The Statue of Cyprus](https://petipasociety.com/pygmalion-or-the-statue-of-cyprus/) (premiere 11 Dec 1883 O.S., Petersburg) credits music and libretto to "Prince **Nikita** Trubetskoi", with no patronymic, dates or sources. Nothing on Wikidata ties Q107119063 to music. IMSLP has no Trubetskoy composer category (checked 2026-10-10), and a web search found no source either way.
- **RG's suggestion (2026-10-10):** "Nikita" could be a nickname (or a name he published under), in which case the two sources would not conflict. Check whether any source gives "Nikita" as a familiar or pen name of Ivan Yuryevich.
- **Where to look:** `raw.production_entry` rows for Кипрская статуя; `review_1890-91_MSK_ballet_p000__b007`, `review_1891-92_MSK_ballet_p000__b005`, `review_1894-95_MSK_opera_p000__b003`, `review_1894-95_MSK_opera_p004__b006`.
- **Would resolve it:** a reference giving the composer of Пигмаліонъ / Кипрская статуя or of Мелузина with a full first name and patronymic or life dates (a music encyclopedia; the libretto or score title page of *Mélusine*); Nadine Meisner, *Marius Petipa, The Emperor's Ballet Master* (2019), which the Petipa Society cites, to see what she prints for the first name.

## 17. Стенбокъ-Ферморъ, графъ И. В. (ballet lists + reviews) -- is the librettist of Эвника the Duma member Иван Васильевич (1859-1916)?

- **Status:** OPEN (RG, 2026-10-10, "not sure": "we may be able to find corroborating information elsewhere"). The creator stays as printed (`stenbock_fermor`, no Wikidata link).
- **What is uncertain:** whether "графъ И. В. Стенбокъ-Ферморъ", co-author of the libretto of Евника / Эвника (SP 1908-09..1910-11), is Count Ivan Vasilyevich Stenbock-Fermor, [Q4441633](https://www.wikidata.org/wiki/Q4441633) (1859-1916).
- **For:** title, surname and both initials match. He was a Petersburg court figure in these years (chamberlain 1909, member of the Third Duma from 1907, later State Council; first chairman of the Imperial All-Russian Aero Club, 1908). The 1906-07 review prints the same libretto as by "⁂" ("Программа балета соч. ⁂, музыка А. В. Щербачева"), which fits a titled official not signing at first; the 1908-09 review names "гр. Стенбокъ-Ферморомъ и г. Щербачевымъ" (after Sienkiewicz's Quo vadis?).
- **Against:** his Russian Wikipedia article says nothing about ballet, theatre or writing; the match is on name and title alone. His son was also Иван (born 1887), but would be И. И., so the printed patronymic points to the father. The family tree has not been checked for another count with the initials И. В.
- **Where to look:** `raw.production_entry` rows for Евника / Эвника; `review_1906-07_SP_ballet_p007__b004`; `review_1908-09_SP_ballet_p004__b004`.
- **Would resolve it:** the printed libretto or programme of Эвника (1907 or 1909); a Fokine source (his memoirs or a biography) naming the librettist in full; press notices of the 1907 charity performance.

## 18. Моренго / Маренго (ballet lists + review) -- is the co-composer of Приключенія Флика и Флока Romualdo Marenco?

- **Status:** OPEN (RG, 2026-10-10, "not sure"). The creator stays as printed (`morengo`, no Wikidata link).
- **What is uncertain:** who "Моренго" is. The Moscow lists 1890-91..1893-94 print "музыка Гершеля, Моренго и Адама"; the 1890-91 Moscow review prints "музыка написана Гершелемъ и Маренго". No first name or initial anywhere. Neither spelling has been zoomed on the scans yet.
- **For Romualdo Marenco** ([Q1052446](https://www.wikidata.org/wiki/Q1052446), Italian ballet composer, 1841-1907): the surname fits the review's spelling; the Moscow version was Mendes's own staging with three composers, so interpolated numbers by an Italian ballet composer would be ordinary practice.
- **Against:** no source links Marenco to this ballet. The original (Berlin 1858, Paul Taglioni) is Hertel's score, and an Italian libretto of 1871 (Duke University Libraries) credits Hertel alone. VIAF lists Marenco among names associated with Paul Taglioni's works, with no title or role.
- **Where to look:** `raw.production_entry` rows for Приключенія Флика и Флока; `review_1890-91_MSK_ballet_p002__b001`.
- **Would resolve it:** the 1891 Moscow libretto or poster; a study of Mendes's Moscow stagings; an Italian libretto of *Flik e Flok* that names added music.

## 19. Аржини (ballet lists) -- is the co-composer of Индія the same man as Даль-Аржине (Costantino Dall'Argine)?

- **Status:** OPEN, kept SEPARATE (RG, 2026-10-10: "we may be able to corroborate later"). `argini` stays his own creator with no Wikidata link; `dallargine` is accepted as Costantino Dall'Argine, [Q16552227](https://www.wikidata.org/wiki/Q16552227) (1842-1877).
- **What is uncertain:** the Moscow lists for Индія (1890-91, 1891-92; "соч. І. Мендеса, музыка гг. Аржини и Венанси") give no initial or first name. The reviews mention Индія often but never name its composers.
- **For one man:** the composer of Брама is printed four ways (Даль-Аржине, К. Даль'Арджинэ, К. Даль-Арджине, Константина Даль'Арджино), so the spelling is unstable and "Аржини" is one vowel from "Аржине"; both ballets were staged in Moscow by Mendes from the Italian repertoire; the co-composer Венанси looks Italian too.
- **Against:** no printing of Индія has "Даль-"; Dall'Argine died in 1877, so Индія would have to reuse older music or rework an older Italian ballet, which has not been identified; a web search for the Moscow Индія found nothing.
- **Where to look:** `raw.production_entry` rows for Индія and Брама; `review_1895-96_MSK_ballet_p002__b006`, `review_1896-97_MSK_ballet_p003__b006`.
- **Would resolve it:** the 1890 Moscow libretto or poster of Индія; a study of Mendes's Moscow repertoire; an Italian source for a ballet on this subject with music by Dall'Argine and Venanzi. See also #20 (Венанси).

## 20. Венанси (ballet lists) -- is the co-composer of Индія Angelo Venanzi?

- **Status:** OPEN (RG, 2026-10-10, "not sure"). `venanzi` stays as printed, with no Wikidata link. Decide together with #19 (Аржини).
- **What is uncertain:** everything but the surname. The Moscow lists for Индія (1890-91, 1891-92) print "музыка гг. Аржини и Венанси", with no initial. The name appears nowhere in the review text.
- **For Angelo Venanzi** ([Q102287046](https://www.wikidata.org/wiki/Q102287046)): the surname fits; the item calls him a composer and orchestra conductor and carries a Ricordi historical-archive person id, i.e. the Italian theatre-music milieu Mendes drew on.
- **Against:** the item has no dates, place or works, so it cannot even be shown that he was active before 1890; a web search for him as a ballet composer found nothing.
- **Where to look:** `raw.production_entry` rows for Индія (`balletproductions_1890-91_MSK_*`, `1891-92_MSK_*`).
- **Would resolve it:** the Ricordi archive record itself (dates, works); the 1890 Moscow libretto or poster of Индія; an Italian libretto of the ballet Mendes reworked.

## 21. Шиманъ / Щимана (Moscow ballet lists) -- the orchestra violinist Михаилъ Викторовичъ, or (in 1900-01) А. Ю. Симонъ?

- **Status:** OPEN; a PROPOSED roster link only (RG, 2026-10-10: "as long as we follow up on this later and don't assume it's correct"). `schiemann` stays its own creator; `production_creators.csv` records the roster person 6dbf9f as proposed, which the pipeline does not act on.
- **What is uncertain:** who the second composer of Хрустальный башмачекъ / Волшебный башмачекъ is. Lists: "музыка Мюльендорфера и Шимана" (1890-91); "музыка Г. Мюльендорфера и Г. Шимана" (1892-93..1896-97); "музыка Мюльдорфера, музыка 4-го д. Щимана" (1900-01; the Щ is scan-confirmed). The 1899-00, 1901-02 and 1902-03 lists name only Мюльдорферъ.
- **For the roster violinist** (Шиманъ, Михаилъ Викторовичъ, Moscow opera and ballet orchestra, from 10 марта 1882, "† 7 декабря 1900 г."): same surname and theatre; the credits run exactly over his years of service and stop after his death; the Г. before both names is the honorific (Мюльендорферъ is Wilhelm Carl Mühldorfer), so the earlier objection "different initial" does not hold; house musicians supplying ballet numbers is a pattern (Фридманъ, Э. Келеръ, М. Келеръ).
- **Against / alternative:** nothing in the yearbook says the violinist composed. For 1900-01 the season review prints "музыка Мюльдорфера и А. Симона"; Симонъ was head of the Moscow orchestras from 1 Sept 1898 and wrote ballet music there, so the list's "Щимана" may be a garbled Симона, or the reviewer may have substituted the better-known name.
- **Where to look:** `raw.production_entry` rows for the two titles; `review_1900-01_MSK_ballet_p001__b003`; `musicians_1900-01_MSK_p003` (no. 106). The roster also has a second, unmerged record "Шиманъ, Михаилъ" (941091, 1890-91, no patronymic printed).
- **Would resolve it:** the Moscow posters or librettos of 1890 and 1899-1900; a history of the Bolshoi ballet repertoire naming the composers of the added music; an obituary of М. В. Шиманъ (December 1900).

## 22. Золотаренко, П. П. (Moscow ballet lists + reviews) -- Петръ Петровичъ the ballet capellmeister, or Павелъ Петровичъ the violinist?

- **Status:** OPEN; a PROPOSED roster link to Петръ Петровичъ (07ab6b) only (RG, 2026-10-10; she answered "Not sure" on 2026-10-05). `zolotarenko_pp` stays its own creator; the pipeline does not act on a proposed link.
- **What is uncertain:** which of two Moscow musicians with the initials П. П. composed for the ballet. Lists (Кольцо любви, 1892-93, 1893-94): "музыка частью П. П. Золотаренко, частью заимствована". Reviews: 1892-93 the same, with the borrowed composers named (Мендельсонъ, Тома, Пуньо, Берліозъ, Делибъ); 1893-94 credits him with a «Польскій танецъ» and a «Лезгинка» in a divertissement. No first name is ever printed.
- **For Петръ Петровичъ** (Капельмейстеръ of the ballet orchestra, "Второй капельмейстеръ балета" in 1893-94; from 6 марта 1873; on the roster 1890-91..1893-94): compiling a ballet score and writing dances to order is a ballet capellmeister's work; his credits fall in his last two seasons and none appears after he leaves the roster.
- **For Павелъ Петровичъ** (violin, opera orchestra, later first violin; from 19 сентября 1882; on the roster to 1907-08): same initials and theatre; orchestra players did write ballet numbers. Against: fourteen more years of service with no further credit.
- **Where to look:** `raw.production_entry` rows for Кольцо любви; `review_1892-93_MSK_ballet_p002__b001`, `review_1893-94_MSK_ballet_p008__b002`; `musicians_189x_MSK` capellmeister entries.
- **Would resolve it:** the 1892 Moscow poster or libretto of Кольцо любви; any printed music by a Золотаренко with a first name; a Bolshoi orchestra history.

## Related, decided (not uncertain), for reference

Ивановъ Иванъ Ивановичъ (Moscow trombonist vs Maly Theatre assistant machinist: SPLIT, because the musician "left service" in 1898 while the machinist continues to 1901-02); Никитинъ Алексѣй Никитичъ, Морозовъ Сергѣй, Тарасовъ Николай Григорьевичъ, Лебедевъ 1dd355 (SPLIT); Петипа, Чекетти, Ширяевъ Александръ, Голяховскій Петръ (MERGED; print variants of the patronymic/surname noted in `genuine_print_typos.md`). The 94 unmerged duplicate pairs from the 2026-10-05 sweep are a separate pending batch: `docs/eval/homonym_sweep_2026-10-05/duplicate_person_pairs.md`.

## Template

```
## N. <Family name, first name> (<list>) -- <the question in one line>
- **Status:** MERGED / SPLIT / OPEN (who decided, when; person-id prefixes)
- **What is uncertain:**
- **For one man:**
- **For two men / against:**
- **Where to look:** entry ids, page ids, scan notes
- **Would resolve it:** the kind of outside source
```
