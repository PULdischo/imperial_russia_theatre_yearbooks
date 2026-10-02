# Independent verification of disputed readings (Musicians roster scans) -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook ("Spiski", Roster) pages. Run python only as `uv run python3` from the project directory (plain python3 lacks PIL).

## Situation
A machine extractor produced stored values for names/instruments; a first human-style reviewer disputed some. For each ITEM in your batch file you get two options, **A** and **B** (random order). One may be the extractor's reading, the other the reviewer's -- **either, both or neither may be right**. Your job is to read the actual scan and decide. Do not assume the "correction" is right; earlier reviewers have been wrong on a few items.

## Procedure, per ITEM
1. Open the scan (path given per page). Locate the entry using its list number and the stored row (neighbouring surnames help). In 1890s volumes surnames are bold.
2. **Zoom**: crop a strip around the entry with PIL (about 6-8 entries tall, full column width), resize 3x LANCZOS, save in /tmp/audit5/crops/<your batch number>/ and Read it. Normal-resolution reading is NOT reliable for ъ/ь, д/л, ц/щ, ш/щ, и/і, ѣ/е, ѳ/в. Zoom tighter (5-6x) on the specific word when the two options differ in one letter.
3. FIRST transcribe what you see for that word/field, letter by letter, BEFORE choosing. Preserve pre-reform letters (ъ ѣ і ѳ) exactly; never modernize.
4. Then choose: A, B, NEITHER (give your own exact reading), or CANNOT-TELL (say what you can see).
For "free-form" items there are no options: report verbatim what is printed for the whole entry (surname + any ordinal suffix, first name, patronymic, instrument as relevant) and compare to the stored row yourself.

## Rules
- REPORT ONLY. Do not edit/create/delete project files. Crops go only in /tmp/audit5/crops/<batch>/. DB read-only. Do not call spawn_task.
- Write the machine-readable results also to /tmp/audit5/results/batch<N>.txt (the only file you may write besides crops).
- Be honest about confidence: DIRECT = letters clearly resolved at zoom; UNCERTAIN = damaged/ambiguous (say what you see).

## REPORT FORMAT -- one line per ITEM, exactly:
ITEM <item id exactly as given> | READ: "<your verbatim reading of the field>" | CHOICE: A|B|NEITHER|CANNOT-TELL | confidence: DIRECT|UNCERTAIN | short note
(for free-form items: CHOICE: FREEFORM and READ: the verbatim printed whole-entry reading)
Every ITEM in the batch must have a line. End with a line `DONE <N> items`.
