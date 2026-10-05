# Blind reader task: Petersburg orchestra lines for Карлъ Шредеръ / Шнейдеръ (report-only)

You are checking printed text in scans of the Imperial Theaters yearbooks (pre-1918 Russian orthography). **Read-only: do not edit any file in the repository.** Scratch files only under /tmp/schn_<yourname>/.

Project root: /Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main
Scans: `outputs/roster_images_full/images/<page_id>.png` (full-page images, ~2300-2800 px wide; use `uv run python` with PIL to crop and enlarge 3-4x).

Items (page_id, printed list number; both are Musicians lists of the Petersburg orchestras; the name is a Карлъ with a surname like Шредеръ or Шнейдеръ):
1. musicians_1905-06_SP_p006 — no. 44 and no. 45
2. musicians_1906-07_SP_p003 — no. 122
3. musicians_1906-07_SP_p006 — no. 33
4. musicians_1907-08_SP_p003 — no. 117
5. musicians_1907-08_SP_p004 — no. 19
6. musicians_1908-09_SP_p004 — nos. 118 and 121
7. musicians_1909-10_SP_p004 — nos. 120 and 122
For each, view the whole page first to locate the entry (two columns; numbers run down the left column then the right), then crop at full resolution and enlarge. Transcribe the ENTIRE printed entry verbatim, letter by letter: surname (watch the letters carefully: Шредеръ vs Шнейдеръ vs Шрейдеръ), first name, patronymic, the whole parenthetical with the start date(s), the instrument, any "переведенъ"/"оставилъ службу" note, and also the printed heading above the list segment the entry sits under (e.g. which orchestra: Оперы и балета, бывшій Михайловскаго театра, Оркестры ...). If two entries are adjacent, say which comes first.
Report one block per entry, in this form:
`<page_id> | no. N | SURNAME, First, Patronymic | full parenthetical/notes verbatim | instrument | heading/orchestra | confidence | note`
Be especially careful with the surname spelling and with every digit of every date (zoom ≥4x on each date; the year digits 1894/1902/1907/1906 matter). If you cannot find an entry, say so; do not guess. Do not look at the database, raw JSON, or any other file in docs/eval/.
