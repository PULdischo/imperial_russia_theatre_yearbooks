# Blind reader task: Graduates lists (school graduating classes), report-only

You are transcribing printed text from scans of the Imperial Theaters yearbooks (1890-1911, pre-1918 Russian orthography: ъ ѣ і ѳ must be kept exactly as printed; never modernise). **Read-only: do not edit any file in the repository.** Scratch files only under /tmp/grad_<yourname>/. Do not open the database, `outputs/full_run/`, or anything under docs/eval/ (this is a blind read: you must not see how these pages were transcribed before).

Project root: /Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main
Scans: `outputs/roster_images_full/images/<page_id>.png` (full-page images, 1700-2900 px wide). Use `uv run python` with PIL to crop and enlarge (3-4x, LANCZOS) -- always read letters from enlarged crops, never from the whole-page thumbnail.
Your bundle: a JSON list of page_ids (the file named in your instructions). Pages are consecutive pages of the "Graduates" source: each season's report of the Theater Schools' ballet department (graduating pupils and where they were posted), sometimes with enrolment statistics.

For EVERY page in your bundle, work through the page top to bottom (left column, then right column if two columns) and report **every printed block**, as one line each, in reading order:

- `HEADING | <text verbatim>` for any heading / school name / section title (e.g. "Московское Театральное Училище.", "Ученицы:", "Ученики:", "Балетное отдѣленіе").
- `ROW | <printed list number or "-"> | <surname exactly as printed, incl. any ordinal like 1-я> | <first name> | <patronymic or "-"> | <note verbatim, the whole sentence or fragment printed after the name, else "-">` for each pupil/graduate line (a person). If the name is printed "Фамилія, Имя." give surname and first name separately but keep every letter and punctuation of the note. If a line contains only a surname, put "-" for the first name. If a name is split over two lines (hyphenated), join it and say so in a `NOTE:`.
- `TEXT | <first 12 words verbatim> ... <last 6 words verbatim> | <what it is>` for any running prose or statistics paragraph (e.g. enrolment counts "Въ 1903—1904 учебномъ году ... состояло 58 ученицъ", a decree preamble, a church or school-count summary). For a table of counts, write one TEXT line per table row giving its label and numbers. These are NOT people: do not turn them into ROW lines.
- `NOTE: <anything unusual>` (damaged print, a line you cannot read, a column break mid-sentence, a number printed twice, a note that continues on the next page, etc.).

Also at the top of each page report `PAGE | <page_id> | printed page number (zoom on the folio) | school(s) named on the page | season, if printed`.

Rules: transcribe, do not interpret or correct. If a letter is doubtful say so in NOTE (e.g. "ѣ or е?"). Number of ROW lines on the page: end each page with `COUNT | rows=<n> | text-blocks=<m> | headings=<k>`. If a page is blank or near-blank, say so. Never guess a name you cannot read.
Final answer: the full report for all pages of your bundle, in order, nothing else.
