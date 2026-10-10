# Blind reader brief: BalletArtists credit summary lines

You are reading ONE kind of thing off scanned pages of the Ежегодникъ Императорскихъ театровъ (1890-1910,
pre-reform Russian orthography: ъ, ѣ, і, ѳ, ѵ). Each BalletArtists entry is a dancer or artist: a printed
list number, a name, a service date in parentheses, and then, indented underneath, a small italic/roman
summary of how often they appeared, for example:

    «Въ 7 балетахъ—21; въ 1 оперѣ—1. Всего—22 раза.  Въ томъ числѣ: Баядерка (кшатрій—2); Корсаръ (Зюльма—1).»

It can run over several lines, and is sometimes followed by a note («Оставилъ службу …», «† …»).

## Your task
For each row of your chunk CSV (`entry_id, image, list_number, name`):
1. Open the page image (`image`). Pages have two columns; entries are numbered.
2. Find the entry with that list number and name. (The name is given only to help you find it; it may be
   slightly misspelled.)
3. Transcribe the credit summary exactly as PRINTED, from the first word («Въ …» or the first role name) to the
   end of the «Всего—N разъ.» sentence, plus any «Въ томъ числѣ: …» list that follows, plus a «Кромѣ того, …»
   sentence if present. Do NOT include the name line or a service/departure note on its own.

## Rules (important)
- Read each NUMBER with great care: zoom in. 3/8, 5/6, 1/7, 0/6, 4/9 are the usual confusions. Do not make
  the numbers add up; transcribe what is printed, even if it does not add up.
- Pre-reform orthography exactly as printed. Never modernise, never normalise a spelling. If a word is
  spelled two ways on the page, keep each as printed.
- Type every letter in CYRILLIC unless the print itself is Latin (a French/Italian title may be printed in
  Latin letters; say so in the note if it is). Never use a Latin look-alike letter for a Cyrillic one.
- A character you cannot read: write ‹?› in its place and say why in the note. Never guess to fill a gap.
- If the entry has NO credit summary printed, say `NONE PRINTED`.
- If you cannot find the entry on the image, say `NOT FOUND` and what you see instead.
- Line breaks and hyphenation: join a word split across lines (hyphen at the line end) into one word, and put
  `[line break inside word]` in the note.

## What to write
Create ONLY the report file named in your instructions, a UTF-8 CSV with the header
`entry_id,printed_summary,note` (quote fields that contain commas). One row per input row, same order.
Do not edit any other file. Do not run git. Do not start background tasks or spawn other agents. Do not try
to look up how the entry is stored in any database; the point is an independent reading of the scan.
