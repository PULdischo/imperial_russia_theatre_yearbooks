# Blind reader brief: the printed name line of a roster entry

Same material as BRIEF.md (scanned Ежегодникъ pages, pre-reform orthography), but you are reading a roster ENTRY: a
printed list number, a name («Фамилія, Имя Отчество»), a service date in parentheses, and sometimes a small summary
underneath. For each row of your chunk CSV (`entry_id, image, list_number`), find that entry on `image` by its list number
and transcribe the NAME LINE exactly as printed, letter by letter: family name (with any ordinal «1-я/2-я/3-я»), first
name, patronymic, and the service/date text in parentheses. LETTER-LEVEL accuracy matters: in particular whether the family
name ends in «ь» or «ъ», and whether it carries a printed ordinal. Zoom until each final letter is unmistakable; write ‹?›
for a letter you cannot tell, with a note; never guess. No modernising, no normalising; Cyrillic letters only.
Report also the two entries immediately above and below (list number + family name as printed), for context.
Write ONLY the report file named in your instructions, a UTF-8 CSV `entry_id,printed_name_line,printed_service_text,neighbours,note`.
Do not edit any other file, run git, start background tasks, or look the entry up in any database.
