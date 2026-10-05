# TheaterSchoolStaff -- BLIND re-read of SECTION structure (which printed section every entry sits under) -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Scans of the yearbook staff list of the Petersburg and Moscow Imperial Theater Schools, 1890-91..1909-10. Pre-reform orthography: report letters EXACTLY as printed (ъ ѣ і ѳ), never modernize. Run python only as `uv run python3` from the project directory.

## What is being measured
For each page assigned to you, record every SECTION heading printed on the page (e.g. "Почетные члены конференціи:", "Инспекторъ.", "Причтъ церкви Училища:", "Священникъ.", "Врачъ при Училищѣ", "Воспитатели:", "Классныя дамы:", "Классная дама при драматическихъ курсахъ", "Преподаватели:", "а) Балетное отдѣленіе.", "Учителя приготовительныхъ классовъ:", "Учительницы ...", "Учителя 1-го класса:", "б) Драматическіе курсы.", "Старшія классныя дамы:", ...) and, under each, the entries (family name + printed list number) that follow it. SCHOOL headings (a line naming a Theater School, "... Театральное Училище") and the big list title are NOT sections -- do not report them as sections, but DO note where one interrupts the flow. Your job is to say, for EVERY entry on the page, which section heading it sits under -- including entries at the top of a column that continue a section whose heading is on an EARLIER page or earlier column (mark those CONTINUED, and name the section only if the page itself makes it clear, otherwise just "CONTINUED").
You are deliberately NOT given anything stored about these pages. Do NOT open outputs/full_run/raw/*, the database, or docs about them: read the scan only.

## Procedure, per page
Scan: `outputs/roster_images_full/images/<page_id>.png`. Open it and **zoom with PIL**: crop each COLUMN in 3-4 vertical strips at about 2x (a page is two columns: read the LEFT column top to bottom, then the RIGHT column top to bottom; a few pages are single-column); crop headings at 3x if small. Save crops under /tmp/ss/crops/<your id>/ and Read them. Section headings are usually centred over a column, smaller and plainer than a school heading; some are in italics or letter-spaced. Sub-lists restart numbering at 1 ("Учителя 1-го класса" 1,2; "Учительницы" 1,2; "б) Драматическіе курсы" 1..14) -- a numbering restart usually marks a new section. Numbers and family names must be exact; letter-spaced surnames are read without the spaces; unnumbered entries (director, priest, doctor...) are written "unnumbered".

## Rules
REPORT ONLY. Do not edit or create any project file. Crops ONLY under /tmp/ss/crops/<your id>/. Write your results ALSO to /tmp/ss/results/<your id>.txt as you go, one block per page, immediately after finishing that page.

## REPORT FORMAT, one block per page, exactly:
```
PAGE <page_id>
COLUMN left
SECTION "<heading text exactly as printed>"            (or: SECTION CONTINUED  -- if the column starts with entries whose heading is on an earlier page/column)
  <list no. | unnumbered> <family name>
  <list no. | unnumbered> <family name>
SECTION "<next heading>"
  ...
COLUMN right
SECTION ...
  ...
SCHOOL_HEADING_ON_PAGE: "<text>" after <family name, list no.>   (or: NONE)
CROPS: <number>
NOTE: <oddities: illegible headings, entries that straddle columns or pages, show-through that looks like a heading, an entry whose section you cannot tell>
```
List EVERY entry on the page, in print order. If a heading is illegible write "UNCERTAIN" inside the quotes. Do not guess a heading from other pages or seasons.
