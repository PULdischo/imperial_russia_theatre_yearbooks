# Reader brief D1/D2 — leaving, transfer and death dates (person field audit, 2026-11-01)

Read `READER_BRIEF.md` in this folder first: same tools (render.py, read-only DB queries), same rules
(pre-reform spelling verbatim, never modernize; read-only on everything except your own results CSV;
zoom on every row; your readings are "checked by Claude" finding aids). RG: "we never really audited leaving
dates, moving dates, and death notices." This is that audit.

## D1 slices (`d1_sliceN.csv`) — every stored end
Each row is a roster entry with a stored service end. `stored_end` shows each period's end as
`end_date_text -> end_date_undate [end_type]` (end_type: `left service`, `died`, `other` = transferred / appointed
/ moved post). Find the entry on the scan and read every date-bearing line printed for the person (the tenure in
brackets after the name, and any line under or after the entry; BalletArtists print it after the tally).
Check: (1) the printed end date, digit by digit, against end_date_text AND the parsed undate (day, month, year);
(2) the kind: «Оставилъ/а службу», «Уволенъ» = left service; «†», «Умеръ/ла» = died; «Переведенъ/а», «Назначенъ/а»,
«Освобожденъ» = other; (3) the line really belongs to THIS person, not the neighbour above/below;
(4) a start date stored as an end, or two periods merged/split wrongly («съ … по …»).

## D2 slices (`d2_sliceN.csv`) — listing before a gap
The person is absent from this list the next season and returns later; no end is stored. Was a
leaving/transfer/death line printed and dropped? Same reading as R9.

## Output
Append rows as you go (after each page) to `slices/<your slice name>_results.csv` (e.g. `d1_slice3_results.csv`),
header once: `item, verdict, printed_line, end_date_text, end_type, proposed_fix, note`
- `verdict`: `correct` (stored end matches the print in date and kind), `wrong_date`, `wrong_type`,
  `wrong_person` (the line belongs to a neighbour), `wrong_structure` (periods merged/split, start stored as end),
  `not_printed` (data has an end the print doesn't give), `none_printed` / `dropped` (D2 only, as in R9), `unclear`.
- `printed_line`: verbatim line(s) as printed. `end_date_text`/`end_type`: what the print gives.
- `proposed_fix`: e.g. `end_date_undate=1898-09-01; end_type=left service` (blank if correct).
- `note`: zoom used; print slips (wrong digit in print vs data faithful → verdict `correct`, say "print slip");
  `ALSO:` dropped departure lines you notice on the page for others (entry number, name, line).
Every item gets exactly one row. When done, reply with counts per verdict and anything systematic.
