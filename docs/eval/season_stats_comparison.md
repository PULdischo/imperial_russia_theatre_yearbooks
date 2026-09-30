# Season production-stats pages vs. the Repertoire tables

Started 2026-09-30 (issue #116). The stats pages transcribed in `docs/season_stats/` (17 seasons, 1891-92 to
1908-09, not 1905-06) are compared with `research.event` by `pipeline/compare_season_stats.py`. Outputs go to
`outputs/season_stats_compare/`: `city_totals.csv` and `family_totals.csv`. Nothing here is a confirmed error
yet. These are leads for a scan audit of both sides, with the same rules as the ballet-list audit.

## What the comparison has established

- **The yearbook counted morning and evening performances separately.** Counting sessions, the Repertoire is
  within −3..+11 of the stats totals in 1891-92 to 1900-01. Counting distinct theater-days, it is 19–63 short
  in every season (level 1, `city_totals.csv`).
- **A drama curtain-raiser on an opera or ballet bill is counted under the opera/ballet.** This was chosen
  by fit, not stated by the yearbook. With it, exact category matches rise from 20 to 48 and the total
  difference falls from 1,236 to 748. Treating those bills as "mixed" leaves the Repertoire with far more
  mixed bills than the stats, and matching shortfalls in ballet and opera. Folding opera + ballet together as
  well did worse (43 exact).
- **Rules for foreign performances**, all taken from the data:
  - A Cyrillic genre decides the family even for a Latin title ("Viola tricolor, ком.").
  - German genre words also count when printed inside the title ("Grossmama, Schwank").
  - A French-looking + German bill with a German-marked work counts as German.
  - "опер." is operetta by the drama company, not opera.
- **After these rules:** 55 of 222 season-city-category rows match exactly, and the total difference is 642.

## Leads

**A. Count matches exactly, receipts differ.** These are the strongest receipt leads, because the same set
of performances is being summed. Several look like a single misread digit: −30.00, −40.00, +100.00,
−200.00, +50.00, −146.00, −294.00 and the 1896-97 Михайловскій drama −19,709.00. Tiny differences (±0.01 to
±5.68) are kopeck-level; half-kopecks are printed in three seasons. Full list:
`family_totals.csv` rows with diff = 0 and diff_receipts_rub ≠ 0; 63 rows as of 2026-09-30.

**1893-94 is systematically low on the Repertoire side in every category** (for example Moscow drama −4,188,
opera −4,402, SP French −5,265). The pattern across all categories suggests a difference in what the two
sources count as receipts that season, not a set of misreads. This is not assumed; it needs a look at the
1893-94 volume.

**B. Count gaps of 5 or more:**
- **Early seasons:** a few categories off by 5–8 (1892-93 SP French −8 with mixed +12; 1897-98 SP "other"
  −9, the guest companies and school performance, which the rules can't separate).
- **From 1901-02: Petersburg Russian drama exceeds the stats** by +8 to +14 a season, rising to
  +37 (1906-07), +58 (1907-08) and +50 (1908-09), with Moscow +40 in 1907-08.
  - In 1906-07 the venue lines place the excess: Маріинскій drama 12 vs 1, Михайловскій 50 vs 25.
  - In 1907-08 the Михайловскій has about 37 unreceipted sessions from 14 Apr to 13 May 1908 (Брандъ,
    Росмерсхольмъ, Вишневый садъ …). No company is named on the scan (p042).
  - Charity and free performances also fall in these gaps.
  - Whether the later stats pages leave such performances out is the open question, not a conclusion.

**C. 85 performed sessions have no works listed** (benefit headings, concerts with no title and similar).
They can't be sorted into a category.
