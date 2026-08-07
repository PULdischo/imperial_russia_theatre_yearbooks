# Gold-standard eval set (v1)

12 pages, hand-transcribed against `docs/schema.md`, spanning all five populated
entity types and the full 1890-1907 date range, including the structurally
hardest cases found in the survey (matinee/evening splits, multi-work bills,
French-language titles, the SP/Moscow table-format break, honorifics, service
periods with a death/resignation, rank-class annotations).

## Contents

- `images/` — the 12 source page renders (150dpi; one page was additionally
  re-rendered at 300dpi and cropped to resolve a dense matinee/evening block —
  see `source_pages.csv` notes for `repertoire_1898-99_MSK_p019`)
- `source_pages.csv` — manifest of the 12 pages (which PDF/page, season, city)
- `person_entry.csv`, `person_entry_service.csv`, `person_entry_credit.csv` — gold
  transcription for the 8 Spiski pages (138 person-entries, 125 service
  periods, 70 credit rows)
- `event_entry.csv`, `event_entry_performance.csv` — gold transcription for
  the 4 Repertoire pages (161 sessions, 145 works)
- `_build_roster.py`, `_build_repertoire.py` — the scripts that emit the CSVs
  from hand-transcribed Python data structures. Not part of the extraction
  pipeline — kept so a transcription fix is a script edit + re-run rather than
  a hand-edited CSV (safer given how much of this is Cyrillic text with
  embedded commas that a raw CSV edit could silently corrupt).

## Coverage

| page_id | entity | season | why selected |
|---|---|---|---|
| repertoire_1890-91_p000 | Repertoire | 1890-91 | earliest combined SP+Moscow grid format, no receipts printed |
| repertoire_1898-99_MSK_p019 | Repertoire | 1898-99 | post-split Moscow block, 3-venue, dense matinee/evening splits |
| repertoire_1898-99_SP_p020 | Repertoire | 1898-99 | post-split SP block, New Year boundary, French titles at Mikhailovsky |
| repertoire_1907-08_SP_p000 | Repertoire | 1907-08 | late SP-only format, dark cells, anniversary annotation, one apparent source misprint |
| administration_1890-91_p000 | Administrators | 1890-91 | earliest roster shape |
| administration_1907-08_p000 | Administrators | 1907-08 | rank-class annotations appear |
| balletartists_1890-91_SP_p000 | BalletArtists | 1890-91 | baseline role hierarchy + performance-tally shape |
| balletartists_1907-08_SP_p000 | BalletArtists | 1907-08 | expanded role hierarchy, honorific title, named-role credit |
| musicians_1890-91_SP_p000 | Musicians | 1890-91 | instrument field, pre-split orchestra organization |
| productionteam_1890-91_p000 | ProductionTeam | 1890-91 | deepest nesting (dept / sub-dept / role) in the sample |
| theaterschoolstaff_1899-00_p000 | TheaterSchoolStaff | 1899-00 | death-in-service example; the page whose date confirmed the filename rename |
| theaterschoolstaff_1906-07_p000 | TheaterSchoolStaff | 1906-07 | resignation example; the page that confirmed the other filename rename |

Not yet covered: Graduates and ProductionStats (no source PDFs yet), and no
page currently exercises an `Undate` genuinely partial/uncertain date — every
date encountered so far in this sample was fully specified. Worth adding a
page with an illegible/partial date once one turns up, to confirm the
partial-precision path actually gets used somewhere.

## How this gets used once an OCR/extraction backend is chosen

1. Run the same 12 page images through the candidate model(s) with a prompt
   asking for output in the `person_entry`/`person_entry_service`/`person_entry_credit`
   or `event_entry`/`event_entry_performance` shape from `docs/schema.md`.
2. Score field-by-field against this gold set:
   - **Name fields** (family/first/patronymic): exact-match rate, plus a
     look at near-misses to catch systematic OCR failure modes (ѣ/е,
     і/и, ъ-dropping, digit transpositions in dates and receipts).
   - **Dates**: exact match on `*_date_text` (verbatim), separately on the
     parsed `*_date_undate` (catches cases where the model gets the string
     right but mis-parses it, or vice versa).
   - **Receipts**: numeric match on rubles/kopecks separately — money is
     where digit-transposition errors are costliest.
   - **Structural fidelity for Repertoire**: does the model correctly split
     multi-receipt cells into separate `event_entry` rows instead of
     flattening them into one multi-work session? (See the `p019` notes —
     this is a real, non-obvious parsing decision, not just an OCR problem.)
   - **Recall on child rows**: `person_entry_credit` and `person_entry_service`
     counts per entry — these are the fields most likely to get silently
     dropped since they're secondary/nested in the source layout.
3. Because this set already includes the known-hard structural cases (not
   just easy pages), a model that scores well here should generalize
   reasonably to the rest of the run — but re-check against a second sample
   once real volume processing starts, since 12 pages out of ~1,300+ is not
   a statistically large sample, just a deliberately adversarial one.
