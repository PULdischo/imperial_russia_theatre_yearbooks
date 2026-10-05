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

## 7. Шнейдеръ Карлъ Ѳедоровичъ (Petersburg Musicians) -- two persons, overlapping 1908-10

- **Status:** OPEN -- not examined in detail; two live persons: 019ed1... (9 entries, 1902-03 to 1909-10, start 1902-09-01) and ce6489... (2 entries, 1908-09 to 1909-10, start 1907-09-01), both SP Musicians. The larger person's stored instrument lines read trombone (1902-03 to 1907-08) and then percussion (1907-08 to 1909-10); the smaller person's instrument was not examined.
- **What is uncertain:** one man with a start-date variant and a change of instrument, or two musicians (father/son or namesakes) in the orchestra at once.
- **Would resolve it:** the printed instrument lines for 1908-10; Petersburg orchestra rosters.

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
