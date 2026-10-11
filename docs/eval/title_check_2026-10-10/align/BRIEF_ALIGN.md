# Column-structure read of a Repertoire page (blind)

You are reading scanned pages of the *Ежегодникъ Императорскихъ театровъ* Repertoire tables. Each page is a table: one row per
calendar date (date label printed in the left margin, or on the right edge of a rotated spread), one column per theater.
You are asked ONLY for the **structure** of each cell, not its contents: for every theater column and every date row, how many
separately ruled sub-cells does that theater's cell hold on that date?

You are not told what any database says. Do not try to guess it. Read what is printed.

## The images you get
Your chunk CSV lists, per page, one or more JPEG crops (`images` column, `;`-separated, in reading order top to bottom).
Crops are bands of one page and overlap by ~10%: a date row at the edge of a band can appear in two crops, report it once.
* **Single page** (`..._pNNN`): 2 bands, text upright. Columns are the theaters of one city (Мариинскій / Александринскій /
  Михайловскій for St Petersburg; Большой / Малый / Новый for Moscow); the city header is printed above them.
* **Spread** (`..._pairNNN`): 4 bands of a two-page spread that has been rotated so the text is upright. Columns left to right
  are the theaters (here five: Мариинскій, Александринскій, Михайловскій, Большой, Малый) and the date label is printed
  vertically at the RIGHT edge of each row, with the month/year header above or beside it. Some theaters (Moscow) sit on the
  other printed page; use each column's printed header.

## What to report
One CSV row per (theater column, date row), in page order, theater by theater:

`page_id,theater,date_label,subcells,kind,note`

* `theater`: the column header as printed, short form (Мариинскій, Александринскій, Михайловскій, Большой, Малый, Новый).
* `date_label`: the row's printed label, e.g. `19 Воскрес.` (copy it as printed).
* `subcells`: how many separately ruled sub-cells that theater's cell has on that row:
  `1` = one undivided cell; `2` = divided into two stacked halves by a horizontal rule; `3` = three; `0` = a dash / empty
  cell with no performance.
* `kind`: one of
  * `single` – one undivided cell holding a performance;
  * `split_labelled` – two (or more) stacked halves with printed УТРО / ВЕЧ(ЕРЪ) labels (the labels may be printed only once at
    the edge of the row, beside the first theater's cell, while the rule runs across all theaters: that still counts as
    `split_labelled`, say so in `note`);
  * `split_unlabelled` – stacked halves divided by a rule, with no УТРО/ВЕЧ label anywhere on that row;
  * `dash` – the cell is a short rule «——» or empty (no performance);
  * `banner_only` – the cell prints only an occasion line (e.g. «Спектакль въ память Вольфганга Гёте.») and no work title, genre
    or figure;
  * `other` – anything else (say what in `note`).
* `note`: empty unless something is odd (a cut-off cell at the fold, a damaged rule, a half you could not make out).

A banner printed across the whole row above several theaters («Безплатные спектакли для воспитанниковъ …») is not a cell: do not
report it as a row, but if it sits directly above a row, put `banner above` in that row's `note`.
Count sub-cells by the **rules**, not by the number of works: one undivided cell can hold two or three works (a double bill),
and that is still `1`.

## Deep pages
If the `deep_theater` column of your chunk row is non-empty, you must ALSO report, for that theater only, on every row of the
page: the receipts figure exactly as printed (`3268 р. 30 к.`, `— к.`, or empty if none) and the first printed line of the cell
(an occasion line counts as the first line; give the first work title after it as `first_work`). For those rows use the columns
`page_id,theater,date_label,subcells,kind,note,receipts,first_line,first_work`. For all other rows leave the three extra
columns empty. Read those figures at full care: they decide whether a stored session is a duplicate of its neighbour.

## Method
Read the whole band before you write anything. Do not rotate or zoom unless a rule or label is genuinely unclear (the crops are
already upright and sharp enough for structure). If you do zoom, work from the file named in the chunk row. Write every row; do
not skip rows because they look ordinary.

## Output
For each chunk write ONE file `docs/eval/title_check_2026-10-10/align/reports/align_NN.csv` (NN = your chunk number) with the
header above (use the 9-column header throughout if any page in your chunk is deep) and one row per cell, all your pages in the
order of the chunk CSV. Your final reply must be ONE short line: `chunk NN: P pages, R rows, N pages with something unclear`.
Do not paste the table into your reply.
