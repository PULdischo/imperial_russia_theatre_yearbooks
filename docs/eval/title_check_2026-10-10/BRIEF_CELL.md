# Blind reader brief: transcribe one whole Repertoire cell, line by line

Same material as BRIEF.md (Repertoire tables of the Ежегодникъ Императорскихъ театровъ, pre-reform orthography; the
earliest seasons are printed ROTATED, rotate with PIL if useful; many images are two-page spreads). Read BRIEF.md first
for the table layout and the letter-level rules (Cyrillic only, ь/ъ exact, ‹?› for an unreadable letter, join words split
at a line end). This brief changes only the TASK: instead of one title, you transcribe the WHOLE cell.

For each row of your chunk CSV (`item, image, printed_page, season, city, date_printed, month_printed, theater,
time_of_day, performance_order` — ignore the empty `performance_order`):
1. Find the DAY (`date_printed`, month from `month_printed` or the page heading) and the THEATER (`theater`; SP = St Petersburg,
   MSK = Moscow), and the утро/веч. half if `time_of_day` says so.
2. Transcribe EVERY printed line of that cell, top to bottom (or in reading order if the sheet is rotated), exactly as printed,
   including a line that is only a heading (e.g. «Бенефисъ г. Рыбакова.», «Спектакль въ пользу ...», «Концертъ ...»).
   Do NOT include the receipts figure («1234 р. 50 к.») or a neighbouring cell.
3. For each line say whether it ends in a GENRE abbreviation as printed («ком.», «др.», «оп.», «бал.», «вод.», «сц.», «ш.», «пьеса»…).
   Write the lines as `1: <text as printed> [<genre as printed, or ->]` joined by ` | `. A genre printed on the next line of the
   same entry (hyphenation or wrap) belongs to the same line.
4. Say in `layout` how each GENRE-LESS line is set: `heading` (printed like a heading: centred, set in different type, or spanning the
   cell / several theaters' cells), `ordinary` (set like the work lines), or `unclear`. Also say whether a heading spans several
   cells (a banner above two or more theaters) or sits inside this one cell only.

## What to write
Create ONLY the report file named in your instructions, a UTF-8 CSV with the header `item,lines,layout,note` (quote fields that
contain commas). One row per input row, same order. If you cannot find the cell write `NOT FOUND` in `lines` and say what you see.
Do not edit any other file. Do not run git. Do not start background tasks or spawn other agents. Do not try to look up how the cell
is stored in any database: the point is an independent reading of the scan.
