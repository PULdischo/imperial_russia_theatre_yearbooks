# Reader brief — person field audit, 2026-11-01 (scan reads)

You are reading scans of the *Ежегодникъ Императорскихъ театровъ* (1890/91–1910/11) to check flagged
person data. The researcher (RG) asked for a field-level audit of every person: anything parsed wrongly,
put in the wrong field, missing or wrong. An automated pass flagged rows; you read each flagged row on the
scan and record what the print actually shows. **READ-ONLY: do not edit the database, raw JSON, or any
file other than your own results CSV.** Your readings are finding aids for RG ("checked by Claude"),
never final verdicts.

Working directory: `/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main`

## Inputs
- Your slice: `docs/eval/person_field_audit_2026-11-01/slices/sliceN.csv` — columns
  `item, check, signal, page_id, entry_id, list_no, stored, context`. Rows are grouped by page.
  `stored` for roster rows is `family_name | first_name | patronymic` as currently in the raw data.
- Render a page: `uv run python docs/eval/person_field_audit_2026-11-01/render.py <page_id> <out.png> [--band TOP BOTTOM] [--width W]`
  (TOP/BOTTOM = fractions of page height). Write PNGs into your own scratch folder
  `/private/tmp/claude-502/-Users-rachelglodo--claude-spares-spare-FBZJT3/e4b2dc47-5b06-4757-8829-4513b6269072/scratchpad/sliceN/`
  and look at them with the Read tool. Render the whole page once to find the row, then a narrow band
  (e.g. 0.08 of the height, `--width 2400`) to read letters. **Zoom every flagged row before judging.**
  Pages are often two columns; entries carry printed numbers (`list_no`).
- To see the full stored row (tenure note, credits, neighbours), query read-only:
  `uv run python -c "import duckdb;c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True);print(c.sql(\"select entry_id,list_number,family_name,first_name,patronymic,rank_or_title,instrument,tenure_note_text,credit_summary_text from raw.person_entry where page_id='PAGE' order by entry_id\").df().to_string())"`
  Service periods: `raw.person_entry_service` (entry_id, start_date_text, start_date_undate, end_date_text, end_date_undate, end_type).
  Review credits: `research.review_credit` (credit_id, printed_phrase...); production credits: `research.production_credit` (credit_id, name_printed, role_text...).

## Rules (RG's standing rules — important)
- Pre-reform orthography (ъ, ѣ, і, ѳ, ѵ) is preserved verbatim. Never modernize, never "correct" a spelling
  to a norm. Orthography in these volumes is unstable and the same surname is spelled several ways, even in
  one list; a different spelling is a misread only if the PRINT shows something else.
- If the print itself has the odd form (a typo, a broken letter, a missing hyphen), the verdict is
  `print_slip` and the data stays as printed. Note whether the type is broken/damaged.
- Known print habits, not errors: foreigners printed without patronymic; Moscow 1901-02 ballet list prints
  some people as a bare surname; ballet-orchestra entries «(см. оперный оркестръ)» are surname-only cross-
  references; Graduates lists print «Surname, Name.»; BalletArtists print «Оставила службу …» after the tally;
  «фонъ-», «де-» lower-case particles; maiden/stage names in brackets.
- Don't guess. If you can't read it, say `unclear` and why.

## What each check asks
- **R1** name-field shape: is each part in the right field (surname / first name / patronymic)? Is a patronymic
  missing in the data but printed? Give the print's reading of all three parts.
- **R2** gender conflict in row: read all three name parts.
- **R3** one-off spelling: read the flagged field letter by letter. Misread, or the print's own spelling?
- **R4** content in the wrong column / missing column (e.g. instrument missing for a musician; date in the rank
  field; subject_taught used for an instrument): what does the print say and where does it belong?
- **R5** tenure: read the whole tenure note exactly (dates, «съ», «по», «Оставилъ службу», «†», «Переведенъ»).
  Give the correct start/end dates and what kind of end it is. Month-word oddities («юня», «седтября»): is the
  print really like that (broken type?) or is it a misread?
- **R6** numbering gap/duplicate/backwards: do the printed numbers really skip (print's own numbering, a new
  sub-list, a page not scanned), or were entries DROPPED from the transcription? If dropped, transcribe each
  missing entry in full in `scan_reading` (number, names, rank, tenure note, instrument/tally).
- **R7** BalletArtists tally: does the print give a tally («Въ N балетахъ—…; Всего—…») for this person? If
  yes, transcribe it exactly. If the print gives none, verdict `matches_print`.
- **C1** ballet production-list credit: read the credit as printed (name, initials, role words). Is it linked to
  the right person (context gives the linked person)? Is an initial printed oddly (e.g. «Ю. Перро»)?
- **V1** Season Review credit: read the phrase on the review page. Is the linked person plausible given the
  initials, gender (г-жа = woman) and date? Is the review text's transcription right?
- **J1** jubilee/obituary link (no page_id): judge from `docs/jubilees_obituaries/jubilees_obituaries_all_entries.csv`
  and the database (person's seasons, names). Scan not required. Is the link right / is a person missed?

## Output
Append rows AS YOU GO (after each page) to `docs/eval/person_field_audit_2026-11-01/slices/sliceN_results.csv`
(write the header once), columns:
`item, verdict, scan_reading, proposed_fix, confidence, note`
- `verdict` one of: `matches_print`, `print_slip`, `misread`, `field_misplaced`, `missing_in_data`,
  `extra_in_data`, `wrong_link`, `link_ok`, `unclear`
- `scan_reading`: what the print shows, verbatim, for the relevant fields.
- `proposed_fix`: `field=value; field=value` against the raw row (or `person=…` for links); blank if none.
- `confidence`: high / medium / low. `note`: zoom used, broken type, anything odd seen nearby
  (also note other errors you notice on the same page that weren't flagged — prefix with `ALSO:`).
Use a proper CSV writer (values contain commas). Every item in your slice gets exactly one row.
When done, reply with: counts per verdict, the 5–10 most important findings, and anything that looks
systematic (same error across many rows).
