# Blind re-read of death marks in the printed rosters

You are checking entries in scanned staff lists of the *Ежегодникъ Императорскихъ театровъ* (pre-1918 Russian
orthography). Each page lists people; a few carry a death mark, a dagger with a date («† 4 іюня 1891 г.»),
usually on its own line under the entry. Worklist: /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a3/work_<label>.csv
(n, image_path, surname_starts, roster, section_hint). Do NOT open anything in other folders or under docs/.

For each row: open the page image (PNG, 300 dpi), find the entry whose surname starts with the given letters and
that carries a dagger, and transcribe FROM A ZOOMED CROP (PIL, `uv run python` from
"/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main"; save crops in
/private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a3/crops_<label>/): the full name as printed (surname, given name, patronymic, any ordinal), the dagger line
verbatim, the service-date bracket and any instrument/post/subject printed in the entry, and the section heading the
entry stands under (look up the column, and say if the heading is on an earlier page). Preserve orthography exactly
(ъ ѣ і ѳ); do not normalise or correct. For every digit in the date compare with other clear digits on the page
(3/5/8, 1/7, 4) and say what you compared. If more than one entry on the page matching the letters has a dagger,
report each. If you find no dagger on such an entry, say so.

Write UTF-8 CSV /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/a3/out_<label>.csv with Python's csv module, appending as you go:
n,name_as_printed,dagger_line_verbatim,date_as_read,confidence,rest_of_entry_verbatim,section_heading,digit_note,problems
Reply with the table of n / name / date / confidence, and any problems.
