# Tallies copied onto a neighbour — scan readings, 2026-10-30

Evidence for `docs/eval/raw_fix_copied_tallies_2026-10-30.py` (see known_issues.md, same date).

- `pair_reads_group1-6.tsv` — every one of the 76 same-page pairs with identical stored credit lines, read on the scans (verdict SAME / NONE_PRINTED / DIFFERENT per entry). Reader agents, 2026-10-30.
- `blind_reread.tsv` — the 36 entries flagged in groups 1-3, re-read by a second reader who saw no stored text and no verdict; it also records the neighbours above and below.
- `fullpage_reads_group1-4.tsv` — every page with a confirmed copy (30 pages, 815 entries), transcribed in full by readers who saw only names; compared line by line with the stored credit lines. 1900-01 SP p000 was read in full by Claude.
- Claude re-read on the scan: 1900-01 SP p000 (whole page), 1893-94 SP p003 nos. 75-89, Нелидова (1890-91 MSK no. 68), Садовская (1903-04 SP no. 88), Бакинъ 1-й (1902-03 MSK), Николаидисъ and Нижинская/Ольхина (1907-08 SP p003), Брыкинъ (1895-96 MSK p004).

Readings are finding aids made by models; each data change rests on two independent readings or on Claude's own.

## Sweep of the remaining BalletArtists pages, 2026-10-30/31

- `sweep/sweep_reads_b*_g*.tsv` — the other 344 BalletArtists pages (7,550 entries), read by 43 reader agents in 8 batches: per person, whether a tally is printed, its «Всего» total and its first number (a lean read aimed at copies and shifts, not a full transcription).
- `sweep/sweep.py` — crop/worklist builder and the comparison against the stored credit lines; `sweep/sweep_flags_grouped.json` — the 135 disagreements, grouped.
- Result: 7,415 agree. Disagreements: 15 stored tallies with nothing printed (13 bare «Всего—N разъ» fragments, Мыльникова 1907-08 MSK's near-copy of Невельская's, Турчанинова's service note); 2 printed tallies not stored (Кольева 1892-93 MSK, Евлановъ 1906-07 MSK); 3 whole pages whose tallies were never stored (1891-92 MSK p005, 1895-96 SP p008, 1905-06 SP p006: 75 people); 43 number disagreements (20 cut lines, damaged digits or known slips; 23 to read on the scan). Nothing applied yet.
