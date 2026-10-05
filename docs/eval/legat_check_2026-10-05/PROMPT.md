# Blind reader task: the surname "Легатъ" on ballet-artist / graduate pages (report-only)

You are checking printed text in scans of the Imperial Theaters yearbooks (1890-1910, pre-1918 Russian orthography). **Read-only: do not edit any file in the repository.** Write scratch files only under /tmp/legat_<yourname>/.

Project root: /Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main
Scans: `outputs/roster_images_full/images/<page_id>.png` (full-page images, ~2300-2800 px wide).
Your bundle: the JSON file named in your instructions — a list of `{page_id, list_number, first_name_hint, season}`. For each item, find the printed entry that carries that list number (the number printed before the surname, e.g. "63." — graduates lists use a different numbering like "2)"; if `list_number` is null the entry sits in a section without numbers, locate it by the first name) and whose first name matches the hint. The surname is Легат-something.

For EACH item:
1. Open the page image (the Read tool shows images; PIL is available through `uv run python`). First view the whole page at reduced size to locate the entry, then crop that line from the full-resolution image and enlarge it 3-4x (LANCZOS) and look at the crop. Two columns per page; list numbers run down the left column then the right.
2. Transcribe the printed heading line of the entry exactly: surname (with any ordinal like "1-й", "2-я", "3-й"), first name, patronymic, as printed, letter by letter. Letter-spaced printing is common: "Л е г а т ъ" is the same word.
3. Report especially the LAST letter of the surname: is it the hard sign ъ (a tall letter with a horizontal serif at the top-left and a bowl at the bottom right) or the soft sign ь (no left-top serif; just a bowl)? Judge it by comparing with other ъ / ь letters on the same page (e.g. find a word that ends in ъ such as a patronymic or "Всего" lines, and a word with ь) rather than from memory. Say how sure you are.
4. If you cannot find the entry, say so — do not guess.

Output format, one line per item, nothing else per item except an optional note:
`<page_id> | list_number | first_name_hint | PRINTED_HEADING | LAST_LETTER = ъ / ь / unclear | confidence high/medium/low | note`
Work through the whole bundle; report every item. Do not look at the database or at the raw JSON transcriptions of these pages (this is a blind read).
