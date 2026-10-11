# Detail read of single cells of a Repertoire page (blind)

You are reading scanned pages of the *Ежегодникъ Императорскихъ театровъ* Repertoire tables (one row per date, one column
per theater). For each (page, theater, date row) in your chunk CSV, report exactly what is printed in that ONE cell, split by
its ruled sub-cells (a cell can be one undivided block, or two or more stacked halves divided by a horizontal rule, often with
printed УТРО / ВЕЧЕРЪ labels that may sit only once at the edge of the row).

You are not told what any database says. Read what is printed. Do not infer.

## Images
`images` in your chunk row lists the crops of the page (`;`-separated, top to bottom, ~10% overlap; single pages have 2 bands,
spreads have 4 bands rotated so the text is upright, theaters across, date label at the RIGHT edge of each row). The date row
you need is named by `date_label` (day number, e.g. `17`; if the same day number occurs twice on the page, the chunk says which
month). Locate the row by the printed label, then read down that theater's column.

## What to report
One CSV row per sub-cell, top to bottom, to `docs/eval/title_check_2026-10-10/align/reports_detail/detail_NN.csv`:

`page_id,theater,date_label,subcell,label,receipts,lines,note`

* `subcell`: 1, 2, ... top to bottom (1 if the cell is one undivided block).
* `label`: `утро`, `вечеръ`, or empty if no label is printed for that block.
* `receipts`: the money figure exactly as printed (`3268 р. 30 к.`, `605 р. — к.`), empty if none is printed in that block.
* `lines`: EVERY printed line of that block in order, separated by ` | `, verbatim (occasion/banner lines, work titles with
  their genre abbreviations). Keep the old orthography (ъ ѣ і ѳ); if a letter is damaged, write the letter it was meant to be.
* `note`: only if odd (cut by the binding fold, figure clipped, rule faint, label missing, rule runs across other theaters but
  not clearly through this cell, ...).
If the cell is a dash or empty, one row with `lines` = `—`.

## Output
One file per chunk; one row per sub-cell for every cell in the chunk, in chunk order. Final reply: ONE short line
`chunk NN: C cells, S sub-cells, N unclear`. Do not paste the table.
