# Second reading: does each entry have any ballet content?

You are re-reading obituaries and jubilee notices in scanned pages of the *Ежегодникъ Императорскихъ
театровъ* (pre-1918 Russian orthography) to decide, independently, how each relates to ballet.
Page images (PNG, 250 dpi) are in /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/jo/ . Your worklist is /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/tier2/work_<label>.csv
(n, image_files, printed_page, entry_heading_as_printed). Do NOT open any key_*.csv file, anything under
docs/, or any other folder — this must be an independent reading.

For each row: open the image(s), find the entry under that heading, and READ THE WHOLE ENTRY to its end
(entries run from a few lines to several pages; some continue onto the next image — the list gives all
of them). Read at a size where every line is legible: crop the page into halves or thirds with PIL
(`uv run python` from "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main";
save crops under /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/tier2/crops_<label>/) and Read the crops. Do not skim, and do not decide from the
heading or the first sentence: the thing we are looking for is often one clause deep in the text.

What counts as ballet content — anything of these, however brief:
- the person danced, mimed, or served in a ballet troupe at any time, even as a child or briefly;
  entered or studied in the ballet department / dance class of a theatre school; taught dancing
- staged, composed, conducted, accompanied, or played in an orchestra for ballet; "балетный оркестръ",
  "оркестръ оперы и балета", "репетиторъ балета"
- designed, painted, built or ran machinery for a ballet; made costumes or wigs for the ballet
- wrote a ballet, a ballet libretto, or about ballet; a named ballet in a list of works or décors
- administered the ballet troupe or the theatre school, or was Director of the Imperial Theatres
- family tie to a dancer that the text states (married to, child of, parent of)
- dancers took part in the person's jubilee or benefit; a ballet was on the bill
Beware look-alikes: «балъ» (a ball), opera roles with the same name as a ballet role, «дивертиссементъ»
that is plainly vocal, «пластика» taught to opera singers. If you meet one, say so in the remark.

Tier each entry:
- core     — a career in ballet, or one of: designer / machinist who worked on ballets; administrator over
             the ballet or the theatre school; ballet critic; player or conductor in a ballet or
             opera-and-ballet orchestra; drama or opera artist who began in the ballet troupe
- mentions — not a ballet person, but the text has ballet content of any kind listed above
- none     — you read the whole entry and it has no ballet content

Write UTF-8 CSV /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/tier2/out_<label>.csv with Python's csv module, appending as you go:
n,entry_heading_as_printed,tier,ballet_quote_verbatim,what_it_says,read_whole_entry,remark
- ballet_quote_verbatim: for core/mentions, the exact words from the page (preserve ъ ѣ і ѳ); empty for none
- what_it_says: one English line
- read_whole_entry: yes, or no + why (never claim yes if you did not)
Reply with: counts by tier, the list of core and mentions entries with one line each, and any entry you
could not fully read.
