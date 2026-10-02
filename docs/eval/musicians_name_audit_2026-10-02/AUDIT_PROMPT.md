# Musicians NAME-FIELD audit (REPORT ONLY) -- every entry, independent reading

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook ("Spiski", Roster) pages, VLM-extracted into DuckDB. Run python only as `uv run python3` from the project directory (plain python3 lacks PIL/duckdb).

## The task
The extractor sometimes misread letters in surnames, first names, patronymics and instrument words (ъ/ь, о/е, н/и, д/л, ц/щ, к/х, ѣ/е, і/и, ѳ/о ...), dropped ordinal suffixes ("1-й", "2-я") or put them in the wrong field, inserted stray spaces, or wrote letters from other alphabets into Cyrillic words. Names decide who is the same person across 20 years of volumes, so **accuracy is everything**. Audit EVERY entry on your pages against the scan, independently -- earlier reviews were partial and may be wrong or incomplete, and you are given no hints.

## For EACH assigned page
1. Read the bundle `/tmp/audit4/<page_id>.txt` (every stored row: eNNN, list no., FAMILY, first, patronymic, instrument, rank_or_title, AUTO-FLAGS). Read the scan `outputs/roster_images_full/images/<page_id>.png`.
2. Go through the page **entry by entry**. Zoom with PIL (crop a column strip of ~8-10 entries, resize 2.5-3x LANCZOS, save in YOUR OWN crops folder, Read it). Normal-resolution reads are NOT reliable for letters. In the 1890s volumes surnames are printed in bold.
3. For each entry compare, letter by letter: surname (incl. any ordinal suffix 1-й/2-й/3-й/1-я/2-я printed after it), first name, patronymic, instrument word(s), list number. Report every difference, including single letters. Also report every AUTO-FLAG you can confirm or refute.

## ALSO: DATE-CHECK entries
Some bundles end with `# DATE-CHECK` lines: entries whose stored tenure START date disagrees with the same person's other entries. For each, read the printed start date "(съ 1 сентября 1882 г.)" at zoom and report it VERBATIM (every digit, the month word exactly as printed -- pre-reform "іюня/іюля/апрѣля" keep their і/ѣ; if the entry has no printed start date say NONE). This tells us whether the stored date is a misread or the two entries are genuinely different people.

## Rules
- Pre-reform orthography must be preserved exactly (ъ ѣ і ѳ). Never "correct" a printed form to modern usage. Compare against what is PRINTED. Surname spellings genuinely vary between years and even within a page; report only what differs from this page's print.
- Names are often printed with line-end hyphenation (e.g. "Людвиго-/вичъ"): the stored value must NOT contain the hyphen. Report a stored hyphen/space that is a line-break artifact.
- A genuine printing error in the original (e.g. a letter swapped, a number repeated): report the PRINTED text verbatim and mark PRINT-TYPO?.
- Ordinal suffix: if the print has "Ромашковъ 1-й" and stored family is just "Ромашковъ" (or the ordinal is in the first-name field), report it.
- Instrument: report the exact printed word (e.g. "Віолончель" with dotted і vs "Виолончель"), including soft/hard sign endings (Вальдгорнъ).
- Do not guess: if a letter is not legible at zoom, mark UNCERTAIN and say what you can see. Entries that match need no line.
- REPORT ONLY. Do NOT edit/create/delete any project file. Crops go ONLY in /tmp/audit4/crops/<your group number>/ (create it). DB read-only. Do NOT call spawn_task or start background work.
- Also write your final section to /tmp/audit4/results/group<N>.txt (the only file you may write besides crops).

## REPORT FORMAT (end your final message with exactly this machine-readable section)
```
PAGE SUMMARY
<page_id> | entries read: N | entries with a discrepancy: K
DISCREPANCIES
<page_id> | eNNN | FIELD (family|first|patronymic|instrument|list|ordinal|space) | STORED: "<stored>" | PRINTED: "<verbatim printed>" | confidence: DIRECT(zoomed) / UNCERTAIN | optional note (PRINT-TYPO?, line-break artifact, ...)
DATE-CHECK RESULTS
<page_id> | eNNN | STORED start: "<stored>" | PRINTED start: "<verbatim>" | MATCH / DIFFERS | confidence: DIRECT(zoomed) / UNCERTAIN
OTHER FINDINGS
- one short line each (anything surprising: duplicated rows, a row printed but missing from the bundle, etc.)
```
Every assigned page must appear in PAGE SUMMARY. Use e-numbers exactly as in the bundle.
