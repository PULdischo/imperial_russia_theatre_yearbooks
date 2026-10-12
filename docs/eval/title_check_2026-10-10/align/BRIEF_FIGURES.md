# Figures read of a St Petersburg Repertoire page (blind, digit by digit)

You are reading scanned pages of the *Ежегодникъ Императорскихъ театровъ* Repertoire tables: one row per date, three theater
columns (Мариинскій / Александринскій / Михайловскій), each cell holding the programme and, at its foot, the receipts figure
(`3601 р. 30 к.`, `1210 р. 29 к.`, `605 р. — к.`). A cell can be divided into two stacked halves (утро / вечеръ), each with its own
figure. You are NOT told what any database holds. Read what is printed.

The figures will be compared digit for digit with a dataset, so every digit matters, including the kopecks and fractions
(`82½ к.`). Read each figure slowly; if a digit is damaged, give the digit you judge intended and say so in `note`.

## Images
The crops in your chunk row are two high-resolution bands (top / bottom, ~10% overlap) of ONE page; text is upright. Date labels
are in the left margin; a month name (`Апрѣль.`, `Декабрь.`) may appear above a row. A date row at the edge of a band can appear in
both: report it once.

## What to report
One CSV row for every figure on the page, theater by theater, in page order:

`page_id,theater,date_label,subcell,label,receipts,first_line,note`

* `theater`: Мариинскій, Александринскій or Михайловскій (from the column header).
* `date_label`: the row's printed label (`19 Воскрес.`).
* `subcell`: 1, 2 ... top to bottom within the cell (1 if undivided); `label`: `утро`/`вечеръ` if printed, else empty.
* `receipts`: the figure exactly as printed: `3268 р. 30 к.`, `605 р. — к.`, `1660 р.` (if no kopeck part is printed, say so by
  writing only what is printed). EMPTY if that block prints no figure at all (a dash cell, a charity/occasion block with no figure).
* `first_line`: the first 18 characters of the first line of that block (a banner line counts), verbatim: it lets rows be matched.
* `note`: only if odd (figure clipped by the fold, digit damaged, figure smudged, block with no figure and why).
Report dash cells (a short rule, no programme) as one row with `receipts` empty and `first_line` `—`.

## Output
`docs/eval/title_check_2026-10-10/align/reports_figures/figures_NN.csv` (NN = your chunk number), one row per figure block for all
your pages in chunk order. Final reply: ONE line `chunk NN: P pages, R rows, N figures unclear`. Do not paste the table.
