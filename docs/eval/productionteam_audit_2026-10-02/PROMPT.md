# ProductionTeam (backstage/technical staff) full-page audit -- REPORT ONLY, every entry, independent reading

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook ("Spiski", staff list) pages, VLM-extracted. Run python only as `uv run python3` from the project directory (plain python3 lacks PIL/duckdb). The ProductionTeam lists cover decorators and their assistants (Отдѣлъ декораціонный), machinists, lighting, props (бутафоры), wardrobe/costumers, wigmakers, sculptors, for the St Petersburg and Moscow theatres. Names decide who is the same person across 20 years of volumes, so **accuracy is everything**. Earlier reviews were partial; you get no hints about what is wrong.

## For EACH assigned page
1. Read the bundle `/tmp/audit7/<page_id>.txt`: every stored row (eNNN, list no., FAMILY, first, patronymic, rank_or_title, tenure_note_text, service periods, AUTO-FLAGS), the section blocks, and a row -> section (institution // heading_path) list. Read the scan `outputs/roster_images_full/images/<page_id>.png`.
2. Go **entry by entry**. Zoom with PIL (crop a column strip of ~6-8 entries, resize 2.5-3x LANCZOS, save in YOUR OWN crops folder, Read it). Normal-resolution reads are NOT reliable for letters. Surnames are usually bold.
3. For each entry compare, letter by letter: surname (incl. any ordinal suffix 1-й/2-й/1-я/2-я printed after it), first name, patronymic, list number, the WHOLE printed text after the name (tenure date "(съ 1 сентября 1882 г.)", any specialty such as "Женскіе парики", "Оставилъ службу ...", "†", "Переведенъ ...", "(онъ же и ...)" aliases), and rank/title words printed with the name (e.g. "профессоръ", "академикъ"). Report every difference, including single letters and every digit of every date (month words keep pre-reform spelling: іюня/іюля/апрѣля).
4. **Section structure**: for each entry check which printed section heading it really falls under (e.g. "Отдѣлъ декораціонный / Декораторы" vs "Помощники декораторовъ", theater name, city МОСКВА/С.-ПЕТЕРБУРГЪ). Report rows stored under the wrong section, headings whose stored text is wrong or contains a person's name/entry text, a list number leaked into the heading (".../ 1."), and entries with no heading when one is printed.
5. **Missing/extra rows**: report any printed entry that has no stored row (verbatim text, and after which eNNN) and any stored row that is not printed on this page or duplicates another.

## ALSO: DATE-CHECK entries
Bundles may end with `# DATE-CHECK` lines (a person whose start date differs from their other entries). Read that entry's printed start date VERBATIM at zoom and report MATCH/DIFFERS (a printed difference is also a finding if genuinely printed).

## Rules
- Pre-reform orthography must be preserved exactly (ъ ѣ і ѳ). Never "correct" to modern usage. Compare against what is PRINTED. Surname spellings genuinely vary between years; report only what differs from THIS page's print.
- Line-end hyphenation ("Людвиго-/вичъ") must not survive in a stored value: report a stored hyphen/space that is a line-break artifact. Letter-spaced printing ("М а ш и н и с т ъ") of HEADINGS is typography: ignore the spacing, check the words.
- Genuine printing errors in the original (swapped letter, repeated number): report the PRINTED text verbatim, mark PRINT-TYPO?.
- Many rows store specialty words ("Женскіе парики") inside tenure_note_text and leave rank_or_title empty: that is a known storage pattern, do NOT list it; DO check the words.
- If a letter/digit is not legible at zoom mark UNCERTAIN and say what you can see. Entries that match need no line.
- REPORT ONLY. Do NOT edit/create/delete any project file. Crops go ONLY in /tmp/audit7/crops/<your group number>/ (create it). DB read-only. Do NOT call spawn_task or start background work.
- Also write your final section to /tmp/audit7/results/group<N>.txt (the only file you may write besides crops).

## REPORT FORMAT (end your final message with exactly this machine-readable section)
```
PAGE SUMMARY
<page_id> | entries read: N | printed entries with no stored row: M | entries with a discrepancy: K
DISCREPANCIES
<page_id> | eNNN | FIELD (family|first|patronymic|ordinal|title|tenure|date|list|space) | STORED: "<stored>" | PRINTED: "<verbatim printed>" | confidence: DIRECT(zoomed) / UNCERTAIN | optional note (PRINT-TYPO?, line-break artifact, ...)
SECTION PROBLEMS
<page_id> | eNNN (or range) | STORED section: "<stored>" | PRINTED section: "<verbatim>" | note
MISSING OR EXTRA ROWS
<page_id> | MISSING after eNNN: "<verbatim printed entry>"   or   <page_id> | EXTRA eNNN: "<why>"
DATE-CHECK RESULTS
<page_id> | eNNN | STORED start: "<stored>" | PRINTED start: "<verbatim>" | MATCH / DIFFERS | confidence
OTHER FINDINGS
- one short line each (anything surprising)
```
Every assigned page must appear in PAGE SUMMARY. Use e-numbers exactly as in the bundle.
