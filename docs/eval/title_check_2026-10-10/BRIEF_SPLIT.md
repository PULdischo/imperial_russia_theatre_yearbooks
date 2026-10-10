# Blind reader brief: is this cell printed split into утро / вечеръ?

Same material and layout as BRIEF.md / BRIEF_CELL.md (Repertoire tables; early sheets rotated; read BRIEF.md first for the table
layout and the letter rules). For each row of your chunk CSV (`item, image, printed_page, season, city, date_printed,
month_printed, theater, time_of_day, performance_order` — ignore the last two) find the DAY and the THEATER and look ONLY at that
one cell. A split cell is printed as two stacked (or side-by-side) sub-cells, labelled «утро» and «веч.»/«вечеръ» (sometimes the label
is a small rotated word at the cell edge); an ordinary cell is a single undivided block. Report in a UTF-8 CSV with the header
`item,split,morning_first_line,evening_first_line,note`:
- `split`: `yes` (two labelled halves), `no` (one undivided cell), `dash` (the whole cell is a dash «—»: nothing played), or `notfound`;
- for `yes`: the first printed line (title only, as printed; letters exact, Cyrillic only) of EACH half, or `-` if that half is a dash;
- for `no`: put the first printed line of the cell in `evening_first_line` and leave the other empty;
- in `note`: anything unusual (a banner above, a half whose label you are unsure of).
Do not transcribe the other lines of the cell. Do not edit any other file, run git, start background tasks or look anything up in a
database; the point is an independent look at the scan. One row per input row, same order.
