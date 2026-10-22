# Handed to the main thread

Things found while building the jubilee/obituary catalogue that belong to other layers of the
project. None has been changed here. Each was seen on a scan unless marked otherwise.

## Review transcription (`raw.review_block`)

| Page, block | Stored text | The page prints |
|---|---|---|
| `review_1900-01_MSK_opera_p007` #3 | «¼ года» | «44 года» (Кламротъ's years as concertmaster) |
| `review_1900-01_MSK_opera_p019` #2 | «25-го января» | «23-го января» (Крутикова's farewell; the Repertoire agrees) |
| `review_1895-96_SP_ballet_p027` #7 | «Н. П. Пуни» | «Н. Ц. Пуни» |
| `review_1910-11_SP_opera_p009` #3 | «14 февраля 1910 г.» | not checked on the scan; the Repertoire has the benefit on 14 Feb 1911 |
| `review_1902-03_SP_ballet_p019` #3 | «М. Петина» | not checked; Петипа elsewhere on the page |
| `review_1893-94_SP_opera_p039` #4 | «успѣшаго» | not checked; presumably «усопшаго» |
| `review_1901-02_SP_ballet_p023` #2 | «2-го января 1903 года» inside the 1901-02 review | not checked |

The 1900-01 Moscow reviews are set in a typeface whose 3 resembles a 5 and whose 4 was once read
as ¼; other digits stored from those pages may deserve a look.

## Rosters (`raw.person_entry`)

- `balletartists_1894-95` (SP): the stored family name is «Доровеевъ»; the obituary and the review print
  Дороѳеевъ (Іосифъ Александровичъ, † 28 ноября 1894 г.). Roster scan not checked.
- `balletartists_1890-91_SP_p000`: Ахмакова's first name is stored as «Калерія»; every later season has
  «Клавдія». Roster scan not checked.
- `balletartists_1906-07_SP_p000` and `musicians_1906-07_SP_p000` print different death dates for the
  répétiteur П. А. Константиновъ: † 25 декабря 1906 г. and † 27 декабря 1906 г. Both read on the scans;
  a conflict in the print, nothing to fix.
- Roster print conflicts with obituaries, both sides read on the scans, nothing to fix: Соловьевъ И. Е.
  († 4 октября 1890 in `musicians_1890-91_SP_p005`, obituary 9 октября); Мейеръ I.-Ф. († 28 марта 1893 in
  `musicians_1892-93_SP_p002`, obituary 25-го марта); Всеволожской И. А. († 28 октября 1909 in
  `theaterschoolstaff_1909-10_p000`, obituary † 29 октября).
- For 25 orchestra players the stored `heading_path` is only «Музыканты», so the orchestra cannot be
  read from the row; `build/roster_orchestra_lookup.csv` has the orchestra for those 25, worked out
  from the list headings and numbering.

- Three ballet-roster rows lack the ordinal the page prints (read on the scans): «Ячменева 1-я» and
  «Брыкинъ 1-й» (`balletartists_1900-01_MSK_p005`, `_p006`), «Александровъ 2-й» (`balletartists_1904-05_SP_p006`).
- М. И. Петипа's service start is printed «14 мая 1847» in the 1909-10 SP ballet roster and «24 мая 1847 г.»
  in the 1906-07 one (the second seen at overview scale only).
- М. Ѳ. Козловъ's service start is printed «съ 16 декабря 1869 г.» in `musicians_1902-03_MSK_p000` and
  «съ 1 сентября 1869 г.» in `musicians_1904-05_MSK_p000` (the 6 is weakly inked there).
- `balletartists_1900-01_MSK`: the printed numbering jumps from 127 (Шебергъ) to 158 (Штихлингъ) in one column.
- Deaths reprinted in a later volume's list, as printed: Ковалевскій († 8 іюня 1899) in 1899-00 and 1900-01;
  Барановъ († 30 сентября 1899) and Краюшкинъ († 20 ноября 1898) in 1900-01; Козловъ († 5 ноября 1902) in
  1902-03 and 1904-05.

## Theatre School reports (scans)

- `1893-94_TheaterSchoolReport.pdf` has three pages covering the ballet departments only; pages 2-3 are
  partial-page crops with no folio.
- `1904-05_TheaterSchoolReport.pdf` page 2 is a partial crop (Moscow ballet only); `1906-07` has the
  St Petersburg school only.
- `1899-00` p. 6, `1902-03` p. 4 and `1905-06` p. 4 of these files are the opening page of the
  Theatre-Literary Committee list, not school-report pages.
- 1894-95 (printed p. 378): Moscow drama placements are dated «съ 1-го сентября 1894 года» for the
  spring-1895 graduates, probably a slip for 1895.
- 1910-11 (printed p. 153), ballet side: the pupil Монаховъ, Евг. left at his own request; the graduate
  Безкоровайная was not placed in the troupe because she was ill.

## Season statistics (`raw.season_stat_dated_note`)

- 1909-10, note 4: «11 января 1909 г.—50-ти лѣтіе музык. дѣятельности Ц. А. Кюи»; the Repertoire has the
  performance on 11 January 1910. Not checked on the scan.

## Linking

- 2026-10-22: every person entry is now linked to a `research.person` record or marked as having none
  (`jubilees_obituaries_person_links.csv`; see the README). The catalogue is still a set of CSV files under
  `docs/jubilees_obituaries/`; it is not in the database.

Found while linking (2026-10-22, from the database and the catalogue; no scans read):

- **Review-mention links (`entities.review_mention`) that are wrong:**
  - `review_1891-92_SP_ballet_p011__b007`: «въ бенефисъ г. Іогансона, назначенный ему за 50-ти-лѣтнюю
    артистическую дѣятельность». This is a man (г.), Христіанъ Петровичъ, but the mention is linked to
    Іогансонъ, Анна Христіановна.
  - `review_1891-92_SP_ballet_p017__b002`: «Яковлевъ 2-й († 9 августа 1892 г.)», a new graduate who died
    before any roster listed him. The mention is linked to Яковлевъ, Николай Николаевичъ, who is listed
    until 1901-02.
- **Possible duplicate person records** (for the merge batch; not decided):
  - Трефилова, Вѣра Ивановна (1893-94–1909-10) and Трефилова, Вѣра Александровна (1901-02 only).
  - Петипа 1-я, Марія Маріусовна (1890-91–1908-09) and Петипа, Марія Маріусовна (1910-11 only).
  - Боборыкинъ, Петръ Дмитріевичъ: two records with the same name (1890-91–1909-10; 1910-11).
  - Дровинъ, Антонъ Фердинандовичъ (1891-92–1892-93) and Дровинъ, Карлъ Фердинандовичъ (1890-91 only). The
    obituary names him «Антонъ-Карлъ».
  - Золотаренко, Петръ Петровичъ (Musicians) and the production-list credit Золотаренко, П. П.
- **Roster names that differ from the obituary:** Корсакъ, Вѣра Александровна (obituary Алексѣевна); Бекке,
  Евгеній Андреевичъ (obituary Генриховичъ); Бенда, Маттіанъ (obituary Маттіасъ). CHECKED 2026-10-22 by
  another session: all 16 roster rows were scan-read by Claude and match the print (Бенда is printed Маттіанъ
  1890-91..1893-94 and Маттіасъ in 1894-95). So these are conflicts in the print, with nothing to fix
  (`docs/query_log.md`, same date).

## Scanning

- `unscanned_worth_getting.md` lists the unscanned jubilee and obituary pages, the closing issues of
  1910-1914 that should carry «Некрологи» and «Юбилеи» sections, and the supplements (deferred).
