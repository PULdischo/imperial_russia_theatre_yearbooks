# Blind reader brief: the printed title of one performance (Repertoire tables)

You are reading ONE thing off a scanned page of the Ежегодникъ Императорскихъ театровъ (1890-1910, pre-reform
Russian orthography: ъ, ѣ, і, ѳ, ѵ): the title of a single performance in a Repertoire table. The tables list, for each
DAY, what was played at each THEATER (a cell can hold several works, one under another, with a genre abbreviation
after each title: «ком.», «др.», «оп.», «бал.», «вод.», «ст.»…). Some cells are split «утро / веч.» (morning / evening).
The sheets of the earliest seasons are printed ROTATED (landscape): the date columns run across, the theaters down;
rotate the image with PIL (`Image.rotate(90, expand=True)`) if that helps. Many are two-page spreads on one image.

## Your task
For each row of your chunk CSV (`item, image, printed_page, season, city, date_printed, month_printed, theater,
time_of_day, performance_order`):
1. Open `image` (large: crop and ZOOM; do not read the whole sheet at once). `printed_page` is the printed page number
   (it appears at the foot of the page, «— 10 —»); on a spread it is one of the two.
2. Find the DAY (`date_printed`, with `month_printed` or the month heading at the top of the page) and the THEATER
   (`theater`; `city` is SP = St Petersburg, MSK = Moscow), and `time_of_day` if the cell is split.
3. In that cell, find the work number `performance_order` (1 = first listed, counting in reading order within the cell).
4. Report that work's title exactly as PRINTED, and the whole cell for context.

## Rules (important)
- LETTER-LEVEL accuracy matters here: the question we are asking is whether a word ends in the soft sign «ь» or the
  hard sign «ъ» (and similar single-letter differences). Zoom until each final letter is unmistakable. If a final
  letter is genuinely not distinguishable, write ‹?› for it and say why in the note. NEVER guess to fill a gap.
- Pre-reform orthography exactly as printed. Never modernise, never normalise, never "correct" a spelling. If you think
  it is a misprint, transcribe it as printed and say so in the note.
- Type every letter in CYRILLIC unless the print itself is Latin (French titles are printed in Latin letters; keep them).
  Never use a Latin look-alike letter in a Cyrillic word.
- Join a word split across lines (hyphen at line end) into one word and write `[line break inside word]` in the note.
- If you cannot find the day / theater / cell, or the cell has fewer works than `performance_order`, write `NOT FOUND`
  and say what you see instead. Do not substitute a neighbouring work.
- Do not include the genre abbreviation in `printed_title`; put it in `printed_genre` (as printed, e.g. «ком.»).

## What to write
Create ONLY the report file named in your instructions, a UTF-8 CSV with the header
`item,printed_title,printed_genre,cell_contents,note` (quote fields that contain commas). `cell_contents` = every work
line in the cell as printed, joined with ` | `. One row per input row, same order. Do not edit any other file. Do not
run git. Do not start background tasks or spawn other agents. Do not try to look up how the performance is stored in
any database: the point is an independent reading of the scan.
