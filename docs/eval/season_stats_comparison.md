# Season production-stats pages vs. the Repertoire tables

Started 2026-09-30 (issue #116). The stats pages transcribed in `docs/season_stats/` (17 seasons, 1891-92 to
1908-09, not 1905-06) are compared with `research.event` by `pipeline/compare_season_stats.py`. Outputs go to
`outputs/season_stats_compare/`: `city_totals.csv` and `family_totals.csv`. Nothing here is a confirmed error
yet. These are leads for a scan audit of both sides, with the same rules as the ballet-list audit.

## What the comparison has established

- **The yearbook counted morning and evening performances separately.** Counting sessions, the Repertoire is
  within −3..+11 of the stats totals in 1891-92 to 1900-01. Counting distinct theater-days, it is 19–63 short
  in every season (level 1, `city_totals.csv`).
- **Correction (2026-09-30, RG asked for examples):** an earlier version of this note said "a drama
  curtain-raiser on an opera or ballet bill is counted under the opera/ballet (chosen by fit)". That was
  wrong. The examples showed that the "drama" in those 299 bills was almost never a curtain-raiser. It was
  mostly genre-less items that the classifier had defaulted to drama:
  - benefit headings stored as works ("Бенефисъ г-жи Гейтенъ 1-й / Фіаметта, бал.");
  - "Гимнъ";
  - excerpts carrying their genre in the title ("3-е д. бал. Пахита");
  - "Дивертиссементъ".

  The classifier now takes a genre-less work's family from the excerpt marker in its title, or else treats
  it as neutral, and the convention was dropped: 57 exact without it, 55 with it. Of the bills that still
  join drama to opera or ballet, many are further classifier misreads:
  - the prologue of Псковитянка ("Боярыня Вѣра Шелога, прологъ, др.");
  - comedy-ballets;
  - an opera-vaudeville.

  Genuine ones exist ("О время!, ком. / Ѳедулъ съ дѣтьми, оп.", 1896-97 Большой) but are few.
- **Rules for foreign performances**, all taken from the data:
  - A Cyrillic genre decides the family even for a Latin title ("Viola tricolor, ком.").
  - German genre words also count when printed inside the title ("Grossmama, Schwank").
  - A French-looking + German bill with a German-marked work counts as German.
  - "опер." is operetta by the drama company, not opera.
- **After these rules:** 57 of 223 season-city-category rows match exactly, and the total difference is 710. Venue rows: 51 of 99 exact.

## Leads

**A. Count matches exactly, receipts differ.** These are the strongest receipt leads, because the same set
of performances is being summed. Several look like a single misread digit: −30.00, −40.00, +100.00,
−200.00, +50.00, −146.00, −294.00 and the 1896-97 Михайловскій drama −19,709.00. Tiny differences (±0.01 to
±5.68) are kopeck-level; half-kopecks are printed in three seasons. Full list:
`family_totals.csv` rows with diff = 0 and diff_receipts_rub ≠ 0; 64 rows after the correction.

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

## Audit round 1 (issue #117, 2026-09-30): the receipt-less sessions

All 79 performed sessions with no receipts in the positive receipt leads (stats higher) were read on the scans:
- 46 genuinely print no figure;
- 31 have their receipts line in the binding fold, all on 1893-94 to 1897-98 spreads;
- 1 fold reading was held back;
- 1 is the bracketed "(3058 р. 08 к.)".

No dropped figure could be restored with certainty. So for 1893-98 the receipts gaps are largely fold-hidden figures, and
settling them needs the physical volumes (`docs/eval/stats_receipts_fold_cells.csv`). Along the way the check fixed two
shifted Новый columns (+3 sessions) and restored 45 free-performance banners.

## Stats ballet counts vs. the ballet productions lists (2026-09-30)

The number of distinct dates in a season's ballet list matches the stats page in 13 of 28 season-cities: the "Балетныхъ"
line alone in 8, or with the stats mixed lines that include ballet in 5. Summing the lists' printed "Всего" totals never
matches, because double bills are counted per work.

**1892-93 Moscow is explained by "Феерій".** The list includes Кольцо любви, "Волшебная сказка въ 3 д. и 10 карт."
(В. А. Крыловъ, music partly П. П. Золотаренко), with 11 dates. These equal the Repertoire's 11 Большой sessions printed
"феерія", and the stats page's "Феерій 11": 41 + 2 + 11 = 54 = the list's dates. 1893-94 Moscow likewise has Кольцо любви
5 = "Феерій 5" (total 50 vs 49 list dates). The stats pages print a "Феерій" line only in these two seasons, and only
for this work. The works the lists call "Балетъ-феерія" (Спящая красавица, Щелкунчикъ, Синяя борода) are counted under
"Балетныхъ". So in the stats, "Феерій" is not the ballet-féerie. Whether Кольцо любви itself is a ballet is RG's
question: the yearbook calls it a "волшебная сказка" but prints it in the ballet list.
