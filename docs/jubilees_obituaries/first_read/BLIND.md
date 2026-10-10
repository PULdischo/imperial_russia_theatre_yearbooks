# Blind heading re-read

You are doing an independent second reading of scanned pages of the *Ежегодникъ Императорскихъ театровъ*
(jubilee and obituary sections, 1890–1911). Page images (PNG, 250 dpi) are in /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/jo/ .
Do NOT open anything in /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/catalogue/ or any crops_* / cr* folder — this read must be independent.

For every assigned page, find every entry heading (the bold/spaced name that opens an obituary or jubilee
notice — in running-text sections it's the bold surname + given names at the start of a paragraph; in later
volumes a centred heading). For each, record, reading letter by letter from a ZOOMED crop
(crop with PIL via `uv run python` from "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main", save crops under /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/blind/crops_<label>/, then Read them):
- the name exactly as printed (surname, given name, patronymic, any bracketed alias / Latin form / ordinal like 1-я)
- the death date or jubilee date as printed in that entry (the "†" line or the sentence giving it), verbatim
- the first ~8 words after the name, verbatim (gives the role)

Preserve pre-1918 orthography exactly (ъ ѣ і ѳ ѵ); never modernize or normalise; copy misprints as printed.
If a letter is unclear write [?] right after it. Do not guess from what the name "should" be.

Write UTF-8 CSV /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/blind/<label>.csv with columns:
image_file,printed_page,name_verbatim,date_verbatim,opening_words_verbatim,notes
One row per heading, in page order. Save incrementally. Reply with the row count and any [?] readings.
