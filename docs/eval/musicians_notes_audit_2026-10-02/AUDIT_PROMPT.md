# Musicians notes audit (REPORT ONLY) -- every entry, no suspects

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook ("Spiski", Roster) pages, VLM-extracted into DuckDB. Run python only as `uv run python3` from the project directory (plain python3 lacks PIL/duckdb).

## The task
On Musicians pages, short printed notes after a musician's tenure/instrument were sometimes DROPPED by the extractor, attached to the NEIGHBOURING person, or altered. Typical notes: "Оставилъ службу 1 мая 1892 г." / "Оставила службу ..." (left service), "† 15 августа 1892 г." (death), "Переведенъ ... съ ... г." / "Съ ... переведена въ ..." (transfer), "Съ ... назначенъ капельмейстеромъ ..." (appointment), "но продолжаетъ участвовать въ оркестрѣ на поспектакльной платѣ", "Участвуетъ въ оркестрѣ ...", "(онъ же и ...)", "Солистъ Двора Его Императорскаго Величества", contract spans ("по ... г. и съ ... г."). These change a person's identity record, so **accuracy is everything**. A first batch of 30 pages found ~40 dropped/misattached notes; you are auditing the REMAINING pages with no hints -- find every printed note and check it against what is stored.

## For EACH assigned page
1. Read the bundle `/tmp/audit2/<page_id>.txt` (every stored row: e-number, list no., name, instrument, rank_or_title, tenure_note_text, credit_summary_text, stored service end date/type). Read the scan `outputs/roster_images_full/images/<page_id>.png`.
2. Go through the page **entry by entry**, reading the trailing text of EVERY entry (the tenure parenthesis, instrument, and any indented line printed below it before the next numbered entry). Zoom with PIL (crop a column strip, resize 2.5-3x LANCZOS, save under YOUR OWN crops folder, then Read it). Normal-resolution reads are NOT reliable (о/ю, ь/ъ, н/и, 1/і, 3/8, 5/6, digits in dates). Read every digit of every date you report at zoom.
3. For every printed note, decide: is its text (and date) present in the stored row's tenure_note_text / rank_or_title / credit_summary_text / service end? Is it attached to the RIGHT person (a note is printed indented under, or inline after, the entry it belongs to -- check column/page tops and bottoms where it can be separated from its owner)? Also report notes stored but NOT printed, and wrong dates/digits.
4. Notes that are already correctly captured need no line -- but do count them (see PAGE SUMMARY).

## Rules
- Never modernize orthography. Copy printed text EXACTLY: pre-reform letters ъ ѣ і ѳ must be kept (e.g. months "іюня", "іюля", "апрѣля"; "Библіотекой"; "завѣдывающимъ"). Check the dotted "і" in months іюня/іюля carefully -- one earlier agent wrote "июля" where the print has "іюля". If unsure of a letter, say UNCERTAIN.
- Do not guess. Mark UNCERTAIN where legibility is poor.
- Stored-format conventions (not errors): a leading "(" may be missing; the instrument word may sit inside tenure_note_text; a final period may be added/absent; a note may live in rank_or_title (e.g. "Солистъ Двора...") -- that counts as captured; a note that is in tenure_note_text but whose service end is empty is worth reporting as "END MISSING".
- Report name/instrument misreads you notice only as one short line in OTHER FINDINGS (they are a separate batch; do not hunt for them).
- REPORT ONLY. Do NOT edit/create/delete any project file. Crops go ONLY in /tmp/audit2/crops/<your group number>/ (create it; other agents share /tmp/audit2/crops, so never use generic filenames in the shared folder). DB access read-only. Do NOT call spawn_task or start background work.

## REPORT FORMAT (end your final message with exactly this machine-readable section)
```
PAGE SUMMARY
<page_id> | printed notes found: N | already correctly captured: M | discrepancies: K
DISCREPANCIES
<page_id> | eNNN | <family name> | PRINTED NOTE: "<verbatim>" | STORED: "<what is stored for the note, or NONE>" | VERDICT: DROPPED / MISATTACHED(to eMMM) / WRONG-DATE / END-MISSING / NOT-PRINTED / TEXT-DIFFERS | confidence: DIRECT(zoomed) / UNCERTAIN | one-line basis
OTHER FINDINGS
- one short line each
```
Every assigned page must appear in PAGE SUMMARY. List DISCREPANCIES only for entries that need a change.

## Results file (the ONE file you may write besides crops)
In addition to giving the REPORT in your final message, write the same machine-readable section (PAGE SUMMARY / DISCREPANCIES / OTHER FINDINGS) verbatim to `/tmp/audit2/results/group<N>.txt` (N = your group number). This is the only project-adjacent file you may create.
