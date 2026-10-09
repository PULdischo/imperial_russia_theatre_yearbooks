# RGIA дело page triage — instructions for the reading agents

Used by the per-дело triage step (see docs/rgia/README.md). Split the PDF's pages
across ~4 agents of ~30 pages each; each writes its own part file, then merge
into docs/rgia/dela/<DELO>.jsonl (one line per PDF page, sorted, no duplicates,
each line also carrying "delo": "<DELO>").

You are triaging an archival file page by page for a historian. The file is RGIA Fond 497, opis 18, delo <DELO>, «<TITLE from docs/rgia_request_log.csv>» (Directorate of Imperial Theatres; read the dates yourself). The pages are photos of a computer monitor showing scans, so quality varies. Pre-1918 orthography; Cyrillic cursive and typed documents.

The historian's chapter is the history of the Ежегодник: how it was produced, distributed, sold, subscribed to, who got free copies (newspapers, officials), print runs, prices, booksellers, finances, reception. She reads cursive slowly and wants to know which pages are worth her time.

Images directory: outputs/rgia_dela/<DELO>/pages/ (relative to the repo root)
For PDF page N (1-based), the original photo is oNNN.<ext> (jpeg/jpg/png) with NNN = N-1 zero-padded to 3 digits, and a contrast-enhanced greyscale version is eNNN.jpg. Use the Read tool to view images. The enhanced version is quickest for getting the gist of typed text and dark ink; the ORIGINAL is better for faint pencil, coloured inks/pencil and red ruling (the enhancement drops colour and softens faint strokes). Read names and numbers from a zoomed crop of the original. If text is small, crop/zoom with python (cd "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main" && uv run python -c "..." ; cv2 is available) and save crops in your scratchpad dir.

For EACH page in your range, append one JSON object per line to your output file, with keys:
- page (int, PDF page number)
- folio (string: any лист number written on the page, e.g. "27", or "")
- doc_type (short: "letter", "draft letter", "list/register", "receipt", "table/ledger", "printed form", "blank/cover", "duplicate view of another page", ...)
- script ("typed", "handwritten", "mixed", "printed")
- date (as written, original orthography, or "" — never guess)
- from_to (sender -> recipient if a letter, else "")
- gist (1-2 sentences in English, concrete: newspapers, institutions, quantities, prices if legible)
- key_names (list of people/institutions read with reasonable confidence; mark doubtful readings with "?")
- legibility ("good", "partial", "poor") — how well YOU could read it
- relevance ("high", "medium", "low") for the history of the Ежегодник's production/distribution/sale/reception
- why (short reason for the rating)

Rules: Do not invent readings; if you cannot read something, say so. Keep pre-reform spelling verbatim (ъ, ѣ, і). "Continuation of p.N" is fine. Note when two photos show the same page (overlap/duplicate). Be efficient: one look at the enhanced image, zoom only where needed. Process every page in your range — none skipped. Final reply: count of pages written plus one or two lines of notable finds.

## UPDATE from the historian (applies to every page, including ones you've already written)
Her priorities:
1. ANYTHING relating to ballet, ballet composers (e.g. Чайковскій, Глазуновъ, Дриго, Минкусъ, Корещенко, etc.), ballet music, ballet productions or dancers — highest priority, even if the page is otherwise routine.
2. The EDITORIAL HISTORY of the Yearbooks: who edited/compiled it, contents decisions, contributors, articles, proofs, illustrations, printing, print runs, editorial correspondence.
3. Sales/subscriptions/distribution (this file's main topic) — still useful, but below 1 and 2.
Add two keys to every JSON line: "ballet" (true/false — does the page mention ballet, a ballet work, composer, dancer, or ballet music?) and "editorial" (true/false — does it bear on how the Yearbook was edited/compiled/produced?). Rate relevance "high" if either is true. When done with your range, go back and REWRITE any lines you wrote before this update so they also carry these two keys and the adjusted relevance (rewrite the whole file cleanly — one line per page, no duplicates).

## Editorial sub-tags (added 2026-10-09)
Alongside "editorial", add four booleans to every line. "editorial" is true exactly when at least one of them is:
- "ed_contributors": who wrote for or contributed text to the Yearbook: named authors/contributors (сотрудники), copies given to contributors, payments or thanks to them.
- "ed_illustrations": the Yearbook's illustrations: photographs (of productions, scenery, groups), photographers, artists/художники, illustration lists, clichés/plates.
- "ed_print_finance": print runs and money: copies printed or acquired, stock counts and storage, printing-house (типографія) dealings, costs, revenue, shortfalls, prices. Routine subscriber or distribution tallies count only if they give print-run, stock or money figures.
- "ed_editors": the editors and the editorial office: Молчановъ, Петровъ, Дризенъ, the Редакція acting, decisions about contents, copies allotted to the editor or редакція.
A page may carry several or none. Distribution of copies with none of the above is none of these.
