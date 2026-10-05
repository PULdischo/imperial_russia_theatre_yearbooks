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

## 5. Ѳедорова Марія Дмитріевна (ballet, Petersburg) -- one woman re-listed, or two?

- **Status:** OPEN -- not decided; currently one person (2475a6...), 1890-91 to 1907-08.
- **What is uncertain:** the 1904-05 volume (no. 114) prints "Федорова **1-я**, Марія Дмитріевна (съ 1 іюня 1885 г.)" with a separate line "Оставила службу 1 іюня 1905 г."; yet "Ѳедорова ... Марія Дмитріевна" is listed again in 1905-06, 1906-07 and 1907-08 with start "съ 12 мая 1885" (the same start date as in 1890-1903). The ordinal changes between volumes (1-я in 1896-97, 3-я in 1894-95), and the 1904-05 start date reads "1 іюня" where other years read "12 мая" (1903-04: "2 мая").
- **For one woman:** same first name and patronymic, the same ballet list, 1885 start every year; the 1904-05 line may be a printer's slip, or she left and was re-engaged.
- **For two:** the printed leaving note in 1904-05 contradicts later listings under the same start date; ordinals "1-я"/"3-я" can mark two different women.
- **Where to look:** `balletartists_1904-05_SP_p005__e003` (no. 114) and the 1905-06 to 1907-08 entries of person 2475a6...
- **Would resolve it:** ballet personnel lists 1905-1908; the ballet-school graduate lists; biographical sources on Petersburg ballet dancers named Федорова.

## 6. Марквардтъ Августъ (Moscow Musicians) -- two persons, same man or two men?

- **Status:** OPEN -- not examined in detail; two live persons: 230477... (22 entries, 1890-91 to 1905-06; starts 1882-09-19 / 1884-08-15) and 8acb78... (8 entries, 1894-95 to 1902-03; start 1882-09-19), both Moscow Musicians, both cornet/trumpet, with overlapping seasons.
- **What is uncertain:** a split of one man's entries over two records, or two men of the same name in the Moscow orchestra.
- **Would resolve it:** the entries' printed instrument lines season by season; Moscow orchestra rosters.

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

- **Status:** MERGED (RG, 2026-10-05, "merge and add to the uncertain list"): two live persons joined into 527973... (21 entries, 1890-91 to 1909-10).
- **What is uncertain:** a **Воспитатель** (tutor; "съ 1 сентября 1891 г."; rank кол. асс. 1898-1905, надв. сов. 1906-08; 19 entries, 1890-91 to 1907-08) and a teacher in **Учителя приготовительныхъ классовъ** ("съ 15 ноября 1907 г."; 1908-09 and 1909-10) share one name and patronymic.
- **For one man:** same school, name and patronymic; the tutor line ends exactly where the teacher line begins; he is never in both lists in one season.
- **For two men / against:** the start dates differ and no volume prints a transfer; the 1907-08 volume still lists him as tutor although the teacher post is dated 15 Nov 1907; Петровъ Иванъ is a very common name.
- **Where to look:** `theaterschoolstaff_1907-08_p000__e020` (last tutor line), `theaterschoolstaff_1908-09_p002__e003`, `theaterschoolstaff_1909-10_p002__e006`.
- **Would resolve it:** Весь Петербургъ 1908-1910 (a school tutor or teacher named Петровъ Иванъ Степановичъ); a school staff register.

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
