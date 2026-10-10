# Blind reader brief: is a receipts figure printed under this cell?

Same material as BRIEF.md / BRIEF_CELL.md (read BRIEF.md first for the table layout and the letter/digit rules; early sheets are
rotated, rotate them with PIL). Each row of your chunk CSV names ONE cell: a DAY (`date_printed`, month from `month_printed` or the page
heading), a THEATER, and, if `time_of_day` is `morning` or `evening`, the утро or вечеръ HALF of a split cell (`unspecified` = an undivided
cell). Find it and answer ONE question: **is a receipts figure («N р. N к.», or «N р. — к.») printed under that cell/half, and if so what
exactly?** Each cell has its own figure directly under its lines; a figure that sits under a neighbouring theater's cell or under the other
half is NOT this cell's.
Report in a UTF-8 CSV with header `item,half_read,receipts,lines,note`:
- `half_read`: `morning`, `evening`, `undivided` or `notfound`;
- `receipts`: the figure exactly as printed (digits zoomed 4x or more; ‹?› for a digit you cannot read; `—` for «— к.» etc.), or the exact
  words `NO RECEIPTS FIGURE PRINTED` if there is none (then describe in `note` what stands where it would: blank, a dash, a note);
- `lines`: every printed line of the cell/half, with its genre abbreviation as printed (` | `-separated); say `dash` if the whole cell/half is «—»;
- `note`: anything unusual (a heading, a figure that clearly belongs to another cell, a split you did not expect).
One row per input row, same order. Do not edit any other file, run git, start background tasks, or look anything up in a database; the point
is an independent reading of the scan. Run commands from the working directory given in your instructions.
