# ProductionTeam START-DATE audit -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Imperial Theater yearbooks staff list (ProductionTeam), 1890-91..1909-10, pre-reform orthography -- report everything exactly as printed (ъ ѣ і ѳ), never modernize. Run python only as `uv run python3` from the project directory.

## Why
A consistency check found PERSONS (one `person_id`) whose entries in different seasons give different FIRST START DATES ("съ 1 сентября 1882 г."). Causes can be: (a) a misread digit/month in one season's entry; (b) the printer's own variation (an erratum, a corrected date); (c) two DIFFERENT men with the same name wrongly merged into one person (e.g. a father and son, or two successive holders of a post); (d) a genuine re-hire or a second period. I need, for each person, the printed truth.

## Your input
`/tmp/audit15/group<N>.txt`: PERSON blocks; each lists entries (entry_id = `<page_id>__eNNN`; NNN = 1-based index into outputs/full_run/raw/<page_id>.raw.json key 'entries', which has family_name, first_name, patronymic, tenure_note_text, service_periods) with the stored start date and text. The listed entries are the ones that DISAGREE with the person's other entries plus up to 2 agreeing "control" entries.

## Procedure, per entry
1. Open the scan `outputs/roster_images_full/images/<page_id>.png` and find the entry (match surname + first name; the raw JSON entry tells you the neighbours). **Zoom with PIL** (crop strips of 5-8 entries at 2.5-3x, save in /tmp/audit15/crops/<group>/, Read them). Dates are small: read every digit and the month word.
2. Transcribe LETTER-EXACT what is printed after the name: the whole parenthetical/tenure text including all dates, "по ... " end dates, "и съ ..." re-hire dates, † / "Оставилъ службу" / "Переведенъ" notes, and the specialty text if any. Give surname, first name, patronymic as printed.
3. Compare with the stored text/start date and say: SAME (print matches stored) or DIFFERENT (give the exact printed text and what differs).
4. Per PERSON, then judge: SAME MAN or DIFFERENT MEN? Use the printed evidence: same first name + patronymic, same start date text in most seasons, continuous career (a role progression, a transfer note), vs. incompatible facts (a death/leaving note followed by a later start, two different start years for the same-named man in the SAME season, different patronymic, the print repeating both dates in different seasons). Say which entries belong to which man if different.

## Rules
REPORT ONLY. Do NOT edit/create/delete project files. Crops ONLY under /tmp/audit15/crops/<group>/; write your final section also to /tmp/audit15/results/group<N>.txt. No spawn_task. Mark UNCERTAIN where illegible; do not guess.

## REPORT FORMAT (end with exactly this)
```
PERSON <id8> <surname> | verdict: MISREAD | PRINT VARIANT | DIFFERENT MEN | RE-HIRE/ORDINARY | UNCERTAIN | confidence DIRECT|UNCERTAIN
  <entry_id> | printed: "<letter-exact tenure text>" | stored-vs-print: SAME|DIFFERENT -> <what differs> 
  ... (one line per listed entry)
  note: <one or two lines of reasoning; for DIFFERENT MEN say exactly which entry_ids belong to which man>
```
Finish with `OTHER FINDINGS` (anything odd: wrong first name/patronymic, wrong surname, wrong end date).
