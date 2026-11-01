# Reader brief R9 — dropped leaving notes (person field audit, 2026-11-01)

Read `READER_BRIEF.md` in this folder first: same tools (render.py, read-only DB queries), same rules
(pre-reform spelling verbatim, never modernize; read-only on everything except your own results CSV;
zoom on every row; your readings are "checked by Claude" finding aids).

## The question
Each row is a person's LAST listing in one list (city + list type) before 1910-11, and the database has NO
end date for that listing. Scan reads found that the transcription often DROPPED the line printed under or after
an entry — «Оставилъ/Оставила службу <date>», «† <date>», «Умеръ/Умерла <date>», «Переведенъ/а … съ <date>»,
«Назначенъ … съ <date>», «Уволенъ …». In BalletArtists that line is printed after the performance tally.
For each row: find the entry on the scan (list_no + surname; pages are often two columns; a tally can run
over to the next column/page — follow it), and read everything printed for that person after the name.

## Output
Append rows as you go (after each page) to `slices/r9_sliceN_results.csv`, header once:
`item, verdict, printed_line, end_date_text, end_type, note`
- `verdict`: `none_printed` (print gives no leaving/death/transfer line — data is right),
  `dropped` (print has the line, data lacks it entirely), `stored_no_end` (the line is in the stored tenure/credit
  text but no end date was parsed — column `leaving_text_already_stored`=yes hints at this), `unclear`.
- `printed_line`: the line verbatim as printed (blank for none_printed).
- `end_date_text`: the date verbatim («1 сентября 1898 г.»); `end_type`: `left service` | `died` | `other`
  (other = transferred / appointed / moved to another post or theatre).
- `note`: zoom used; `ALSO:` any other dropped departure lines you notice on the same page for people NOT in
  your slice (give entry number, name and the line) — these matter.
Every item gets exactly one row. When done, reply with counts per verdict, per season if a season stands out,
and anything systematic.
