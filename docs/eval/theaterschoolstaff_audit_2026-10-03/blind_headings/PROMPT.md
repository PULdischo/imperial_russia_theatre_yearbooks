# TheaterSchoolStaff -- BLIND re-read of title blocks and school headings -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". These are scans of the yearbook staff list "Списокъ личнаго состава преподавателей и служащихъ ... Театральныхъ Училищъ" (staff of the Petersburg and the Moscow Imperial Theater Schools), 1890-91..1909-10. Pre-reform orthography: report letters EXACTLY as printed (ъ ѣ і ѳ), never modernize, keep punctuation. Run python only as `uv run python3` from the project directory.

## What is being measured
For each page assigned to you, find the printed HEADINGS that name the list or a school, and say where the Petersburg school's list ends and the Moscow school's list begins. You are deliberately NOT given anything stored about these pages and must NOT open outputs/full_run/raw/*, the database, or any docs about them: read the scan only. (The only other source you may use is the scan image file itself.)

## Procedure, per page
Scan: `outputs/roster_images_full/images/<page_id>.png`. Open it, then **zoom with PIL**: crop the full width in horizontal strips (about 4 per page at 2x) and, for every heading you find, a 3-4x crop of the heading itself; save crops under /tmp/tt/crops/<your id>/ and Read them. Layout is two columns; the heading may be centred across both or sit in one column.
Headings to look for (transcribe exactly, letter-spaced words read without the spaces, line breaks marked " / "):
 (a) the LIST TITLE block (e.g. a large title beginning "СПИСОКЪ" with lines under it) -- normally only on a season's first page;
 (b) a SCHOOL heading: a line naming a Theater School ("... Театральное Училище" with or without "Императорское", "С.-Петербургское", "Московское"), usually centred and larger than section headings such as "Почетные члены конференціи", "Преподаватели", "а) Балетное отдѣленіе", "Классныя дамы". Section headings are NOT school headings -- do not report them.
For each school heading say exactly which two printed entries it sits between: the entry just BEFORE it and the entry just AFTER it (family name + printed list number, or "none (top of page)" / "none (end of page)").
Also say, for the FIRST and the LAST printed entry on the page: which school's list it belongs to if that is determinable from this page alone (the school heading printed above it on this page), otherwise "CONTINUATION (heading on an earlier page)".

## Rules
REPORT ONLY. Do not edit or create any project file. Crops ONLY under /tmp/tt/crops/<your id>/. Write your results ALSO to /tmp/tt/results/<your id>.txt as you go (one block per page, written immediately after finishing that page).

## REPORT FORMAT, one block per page, exactly:
```
PAGE <page_id>
TITLE_BLOCK: "<exact text, lines separated by ' / '>"   (or: NONE)
SCHOOL_HEADING: "<exact text>" | BEFORE: <family name, list no. | none (top of page)> | AFTER: <family name, list no. | none (end of page)> | COLUMN: left/right/both   (one line per heading; or: SCHOOL_HEADING: NONE)
FIRST_ENTRY: <family name, list no.> | BELONGS TO: <school named by a heading above it on this page | CONTINUATION>
LAST_ENTRY: <family name, list no.> | BELONGS TO: <school named by a heading above it on this page | CONTINUATION>
CROPS: <number of crops made>
NOTE: <anything odd: damaged/illegible headings, a heading you are unsure of, running heads/page numbers that look like headings>
```
Mark UNCERTAIN inside a quoted text where letters are illegible. Do not guess a heading from other pages or seasons: if the page shows none, write NONE.
