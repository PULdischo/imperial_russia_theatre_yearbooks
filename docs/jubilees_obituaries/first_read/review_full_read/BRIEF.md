# Full read of the Season Reviews for jubilee / farewell / death notices

You are reading transcribed text of season reviews from the *Ежегодникъ Императорскихъ театровъ*
(pre-1918 Russian orthography). Your chunk is one text file in /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/rr/ (named in your task).
Each block starts with a header line `=== <page_id> #<block_index>`. Read the WHOLE file, every block,
start to finish (use Read with offset/limit in steps of ~400 lines until you reach the end; state the
last line number you read in your reply). Earlier keyword searches have already been run; your job is
to catch what keywords cannot, so judge by meaning, not by particular words.

Flag every passage that reports, about a real person or institution (not a character in a plot):
- a jubilee or anniversary: N years of service / artistic activity / on stage; a benefit or performance
  tied to such an anniversary; an anniversary of a theatre, or of a person's birth or death
- a farewell: farewell benefit, last appearance, leaving the stage or the service WITH some mark of
  occasion (ovation, gifts, speech, "въ послѣдній разъ", "покинулъ сцену", "простился")
- a death: died, †, funeral, "покойный" said of someone who died that season, a performance in memory
  of someone, or for the benefit of a widow / family / orphans
- an honour paid on stage ("чествованіе", wreaths and addresses presented to a named artist)
Do NOT flag: deaths and partings inside ballet/opera plots; ordinary benefit performances with no
anniversary or farewell element; bare lists "Оставили службу: …" (but DO flag any death or dagger
inside such a list); the phrase «заслуженный артистъ» used as a title in a cast list.
When unsure, flag it and say why — a false flag costs little, a miss costs a lot.

Write UTF-8 CSV /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/rr/flags_<NN>.csv (NN = your chunk number) with columns:
page_id,block_index,kind,name_as_printed,quote_verbatim,why
- page_id exactly as in the header (without "review_"), block_index the number after #
- kind: jubilee | farewell | death | memorial | honour | unsure
- quote_verbatim: copy 10-40 words exactly from the file (do not retype from memory, do not modernize)
- one row per person per occasion
Write the CSV with Python's csv module (so quoting is right); append as you go so partial work survives.
Reply with: the last line number read, the number of flags, and a one-line list of the flags.
Do not open or edit anything else.
