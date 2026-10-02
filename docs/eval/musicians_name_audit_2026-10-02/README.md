# Musicians name-field + start-date audit (issue #130, items 1 and 2) -- INCOMPLETE, paused 2026-10-02 (usage limit)

43 groups x 5 pages (215 Musicians pages). Each agent reads every surname / first name / patronymic / instrument / list number / ordinal against the scan and, for entries whose stored start date disagrees with the
same person's other entries (`datecheck_entries.json`, 341 entries on 160 pages), reads the printed start date.
- **Finished groups** (results in `results/groupN.txt`): see the files present -- groups 1, 5, 6 certainly; any other `groupN.txt` present was written by an agent that finished before the stop.
- **Not done**: every other group; agents for groups 2-4, 7-16 were stopped mid-run. Re-run those groups with `AUDIT_PROMPT.md` (bundles are rebuilt by the query in docs: stored name fields + AUTO-FLAGS).
- **Nothing has been applied to the data yet.** Plan: apply a correction only if an agent read it at zoom AND it is corroborated (another season's spelling for the same person / the earlier worklists in ../musicians_notes_audit_2026-10-02/);
  contested items get a hand zoom.
- **Finding so far on item 2**: every date-check on groups 1, 5, 6 printed exactly the stored date (e.g. Марквардтъ 19 сентября 1882 vs the conductor 15 августа 1884; Лебедевъ 26 сентября 1885 vs 1 сентября 1868): the persons are genuinely
  TWO different men merged under one name -- a person-merge problem for the entity layer, not misreads.
- Recurrent structural slips seen: ordinal "1-й/2-й/3-й" stored in the first-name field (Адольфи), patronymic stored inside the first-name field, hyphenated double first names split into first+patronymic (Мейеръ-Гиршъ, Іоганъ-Фридрихъ),
  surname part stored as first name (Туровичъ фонъ-Охота), instrument "Піанистъ при драматическихъ спектакляхъ" truncated, final ъ read as ь (Гейнь, Руссь, Кунсть), Виолончель/Біолончель for printed Віолончель.

## Update 2026-10-02 -- audit completed and applied
All 43 groups reported (results/group1..43.txt); every flagged item was re-read blind by a second agent (verification/, 16+1 batches; analysis/decisions.json) and
the verified corrections applied to the raw JSON (apply/: engine.py, apply_all.py, spec_struct*.py, change_log.json, residual_log.json). Full account, counts, policy
decisions, items left as stored and the entity-layer effect: docs/eval/known_issues.md, "Issue #130 batch 9". Typos stored verbatim: docs/eval/genuine_print_typos.md.
