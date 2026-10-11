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

## Season statistics (`raw.season_stat_dated_note`)

- 1909-10, note 4: «11 января 1909 г.—50-ти лѣтіе музык. дѣятельности Ц. А. Кюи»; the Repertoire has the
  performance on 11 January 1910. Not checked on the scan.

## Linking

- No catalogue row is linked to a `research.person` record. The catalogue's own `see_also` column
  matches people only by surname and initials.
- The catalogue is a set of CSV files under `docs/jubilees_obituaries/`; it is not in the database.

## Scanning

- `unscanned_worth_getting.md` lists the unscanned jubilee and obituary pages, the closing issues of
  1910-1914 that should carry «Некрологи» and «Юбилеи» sections, and the supplements (deferred).
