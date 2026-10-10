# Blind reader brief 2: summaries that continue past a column or page break

Read BRIEF.md first and follow all its rules (blind reading, pre-reform orthography, Cyrillic letters, ‹?› for an
unreadable character, join hyphenated words, one report row per input row). This brief only adds the following.

Our transcription of every entry in your chunk is CUT OFF: the entry's printed summary does not end where we stopped.
Its remaining lines are at the top of the NEXT COLUMN on the same page, or at the very top of the NEXT PAGE image
(the CSV's `next_image` column; empty means the list ends on this page).

For each row: find the entry (by list number and name) on `image`; read its WHOLE printed summary from the first
word to its real end (the last «)» and full stop of the «Въ томъ числѣ: …» list, or the end of the «Всего» sentence if
there is no such list), following it into the next column or into `next_image` where it continues. Do NOT include the
next entry (its number and name). If the summary ends on this page, say so in the note.

In the note, say WHERE it continued: `same column`, `next column`, `next page`, or `ends here`.
