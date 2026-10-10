# Blind reader brief: read a whole Repertoire cell INCLUDING its receipts, half by half

Same material as BRIEF.md / BRIEF_CELL.md (read both first: table layout, letter rules, ь/ъ exact, Cyrillic only, ‹?› for an unreadable
letter or digit, never guess). For each row of your chunk CSV find the DAY and THEATER and read that ONE cell completely. The cell may be
split into two stacked halves, «утро» and «вечеръ»; read each half separately. For EACH half give:
- every printed line, top to bottom, with the genre abbreviation exactly as printed (or `-` if the line has none) — a heading line without a
  genre (benefit / charity notice) is reported as such;
- the RECEIPTS figure printed under that half exactly as printed («1234 р. 56 к.»; digits zoomed 4x or more; ‹?› for any digit you cannot read);
- if the half is a dash «—» or empty, say so.
Digits matter most here: zoom on every receipts figure and say which digits are certain. Report in a UTF-8 CSV with header
`item,morning,evening,note`: `morning`/`evening` hold `<line> [<genre>] | <line> [<genre>] || receipts: <figure>`; for an undivided cell put
everything in `evening` and write `UNDIVIDED` in the note. Do not edit any other file, run git, start background tasks, or look anything up in
any database; one row per input row, same order. Run commands from the working directory given in your instructions.
