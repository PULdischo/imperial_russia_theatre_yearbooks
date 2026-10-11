# Looking for death, jubilee and farewell notices in pages not yet searched

Scanned pages of the *Ежегодникъ Императорскихъ театровъ* (pre-1918 Russian orthography), PNG at 200 dpi, in
/private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a5/ . Your files are named in your task. Read EVERY page in full (crop into halves or thirds with PIL —
`uv run python` from "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main",
crops under /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a5/crops_<label>/ — so that every line is legible). Do not open anything under docs/.

Report every statement about a real person that is one of:
- a death (died, †, скончался, умеръ, «покойный» of someone recently dead, funeral, in memory of)
- a jubilee or anniversary of service or activity; an award or honour marking years of service
- a retirement, dismissal with pension, leaving the school or service, a farewell
- a commemoration: a stipend, prize, fund or portrait in someone's name or memory
For the Theatre School reports also report, briefly, one row per page: what the page contains (so we know it was
read), and note any pupil or teacher said to have died, left, or been honoured.
Do NOT report ordinary graduation lists or appointments unless they carry one of the things above.

Write UTF-8 CSV /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a5/out_<label>.csv (Python csv module, append as you go):
image_file,printed_page,kind,person_as_printed,quote_verbatim,what_it_says,ballet_link
- kind: death | jubilee | farewell_or_leaving | commemoration | page_summary
- quote_verbatim: the exact words (keep ъ ѣ і ѳ); zoom on names and dates
- ballet_link: yes / no / unclear, with the reason (dancer, ballet teacher, ballet pupil, ballet composer, ...)
Reply with the list of notices found (not the page summaries), and the pages you could not read.
