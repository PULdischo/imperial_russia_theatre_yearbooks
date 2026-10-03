# TheaterSchoolStaff -- STRICT TABLES for your season (follow-up to your audit)

You already audited your season's pages and know exactly what is wrong. Now restate your findings as three MACHINE-READABLE tables. The ONLY files you may write are the three below (REPORT ONLY otherwise: no project files). Tab-separated, UTF-8, NO header, one record per line, text exactly as printed/stored (Cyrillic, ъ ѣ і ѳ), no extra spaces at line ends, tabs never inside a field. Write them with a small python script (open(..., 'w', encoding='utf-8')) into /tmp/tss/strict/ :

  /tmp/tss/strict/<season>_struct.tsv    /tmp/tss/strict/<season>_fix.tsv    /tmp/tss/strict/<season>_missing.tsv

## 1. <season>_struct.tsv -- ONE LINE FOR EVERY STORED ROW of every page of your season (all pages, all rows, stored eNNN order)
page_id <TAB> eNNN <TAB> SCHOOL <TAB> L2 <TAB> L3 <TAB> L4 <TAB> KIND <TAB> NOTE
- SCHOOL = SPB or MSK: the school this PERSON belongs to by the print (a whole page can be MSK although stored as St Petersburg, or a column-top block can belong to the previous page's school).
- L2, L3, L4 = the printed headings governing the row BELOW the school heading, top to bottom, VERBATIM as printed in that season, without the trailing "." or ":" and without letter-spacing: e.g. L2="Почетные члены конференціи"; L2="Причтъ церкви Училища" L3="Священникъ"; L2="Преподаватели" L3="а) Балетное отдѣленіе"; L2="Преподаватели" L3="б) Драматическіе курсы"; L2="Преподаватели" L3="а) Балетное отдѣленіе" L4="Учителя приготовительныхъ классовъ" (only if the print nests it so; if unsure, use your best reading and put UNCERTAIN in NOTE). Headings inherited from a previous page/column still govern: give them. Use the PRINTED spelling (Инспектрисса / Инспектриса, Причтъ, Классныя ... as printed in YOUR season).
- Do not include the list title or the school name in L2-L4.
- KIND = PERSON, or NONPERSON for a stored row that is not a person (a sub-heading "Священникъ"/"Дьяконъ", a note "Оставилъ службу", "† 1902 г." ...); for NONPERSON put the stored row's surname text in NOTE as "stored: <text>" and give SCHOOL/L2.. of its position.
- NOTE optional (UNCERTAIN: reason).

## 2. <season>_fix.tsv -- ONE LINE PER FIELD CORRECTION
page_id <TAB> eNNN <TAB> FIELD <TAB> STORED_EXACT <TAB> CORRECT_EXACT <TAB> CONF
- FIELD in {family_name, first_name, patronymic, list_number, rank_or_title, subject_taught, tenure_note_text}.
- STORED_EXACT = copy EXACTLY the stored value from /tmp/tss/<page_id>.txt (the column for that field; empty string if empty). CORRECT_EXACT = what the field must hold per the print (empty if it must be empty).
- A row with several wrong fields -> several lines. Blocks you reported as "e009-e035 shift" MUST be expanded to the exact lines for EACH row (e.g. rank_or_title "Танцы" -> "" and subject_taught "" -> "Танцы"; if the tenure text also carries the subject, a tenure_note_text line too). Likewise first-name/patronymic splits (first_name line + patronymic line), "князь"/"кн." rank splits (rank_or_title, first_name, patronymic lines), ordinals ("Легатъ" -> "Легатъ 1-й").
- CONVENTIONS: subject_taught = the printed subject (no trailing period). rank_or_title = only real ranks/titles (ст. сов., кол. асс., князь, въ званіи камергера ...). Parenthetical POST NOTES -- "(священникъ церкви Училища)", "(дьяконъ церкви Училища)", "(инспекторъ Училища)", "(надзиратель)", "(Управляющій Московской Конторой ...)", transfer notes -- go to tenure_note_text in print order BEFORE/AFTER the date exactly as printed, e.g. tenure_note_text "(священникъ церкви Училища) (съ 20 февраля 1893 г.)" or "(священникъ церкви Училища)" when no date is printed; the subject sentence never stays in tenure_note_text; leaving/† notes stay in tenure_note_text. Dates that are NOT printed (invented) -> CORRECT empty. Line-break hyphens and Latin lookalike letters -> fixed. Honorary-member rows with a date that is not printed -> empty.
- Print variants are NOT errors and must NOT be listed (Всеволожской, Михаиловичъ vs Михайловичъ, колл./кол. асс., Каменевъ x3 ...). Genuine PRINT TYPOS (printed wrongly, e.g. Потѣхннъ, "1." for "г.", Махаилъ): do NOT list them as fixes; list them with CONF = PRINT_TYPO and CORRECT_EXACT = the PRINTED (typo) text, so I can log them without changing storage.
- Cosmetic only (missing outer parentheses, trailing periods, spacing around parentheses): do NOT list.
- CONF = DIRECT or UNCERTAIN.

## 3. <season>_missing.tsv -- ONE LINE PER MISSING PRINTED PERSON
page_id <TAB> SEQ <TAB> SCHOOL <TAB> L2 <TAB> L3 <TAB> L4 <TAB> list_number <TAB> family_name <TAB> first_name <TAB> patronymic <TAB> rank_or_title <TAB> subject_taught <TAB> tenure_note_text <TAB> START_DATE_TEXT <TAB> END_DATE_TEXT <TAB> END_TYPE <TAB> CONF
- SEQ = 1..n in print order within the page. All printed letter-exact. tenure_note_text and START_DATE_TEXT follow the style of the stored sibling rows (look at a stored row of the same list: e.g. tenure_note_text "(съ 1 сентября 1888 г.)" or "съ 1 сентября 1888 г." and START_DATE_TEXT "съ 1 сентября 1888 г."; for an interrupted tenure "(съ A по B и съ C)" give the whole text in tenure_note_text and the first start in START_DATE_TEXT). END_TYPE = "" unless a leaving/death note is printed ("left service"/"died" -> use the words left service / died). subject_taught WITHOUT trailing period.
- Include a person whose row is missing because a sub-heading was read as the surname (list the real person here; mark the stored row NONPERSON in struct).
- If nothing is missing, write an empty file.

When done, final message: the number of lines in each of the three files and how many UNCERTAIN/PRINT_TYPO lines (one short paragraph, nothing else).
