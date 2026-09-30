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

### Three-way ballet count: stats page, ballet list, Repertoire (2026-09-30)

- **Stats:** "Балетныхъ" + mixed lines that include ballet + "Феерій" (Кольцо любви).
- **List:** distinct dates, a date counted twice when its note says "2 раза".
- **Repertoire:** performed sessions that include a work with parent genre ballet (#118).

Result over 28 season-cities: all three agree in 11; exactly two agree in 14; all three differ in 3. Mapping every
list/Repertoire difference to its dates:

- **Counting artifact (mine):** two different ballets on one date, as a matinée and an evening, share a single list
  date. This explains 1893-94 Moscow and SP (29 Dec 1893, 20 Feb 1894), all 5 of 1898-99 Moscow, and all 5 of 1899-00
  Moscow. Corrected, 1893-94 Moscow, 1893-94 SP and 1898-99 Moscow agree in all three sources.
- **Already on the disagreements list:**
  - 1895-96 Moscow: A2.
  - 1897-98 SP: A3–A6.
  - 1898-99 SP: A7.
  - 1900-01 SP: D3, plus "Ученики Дюпрэ" = "Les élèves de Dupré", now aliased for the parent genre.
  - 1901-02 Moscow: A9.
  - 1902-03 Moscow: D4. 1902-03 SP: E1.
  - 1903-04 Moscow: D5. 1903-04 SP: D6–D8, E2.
  - 1904-05 SP: A12, B1, E4.
- **Observed:** in 1902-03 and 1903-04 the stats page equals the list, and both leave out the same charity and jubilee
  bills (D4–D8, E1, E2) that the Repertoire prints. This is a pattern, not a stated rule.
- **New leads (not yet scan-checked):**
  - 23 Jan 1899, Маріинскій: "Балъ изъ бал. Пахита" (1898-99 SP).
  - 12 and 19 Dec 1901, Новый: "Коппелія" (1901-02 Moscow).
  - 21 Feb 1902, Большой утро: "Жизель / 1-е, 2-е и 3-е д. бал. Корсаръ" (1901-02 Moscow).
- **Stats page differs from list = Repertoire:** 1894-95 SP (+2), 1895-96 SP (−1), 1899-00 Moscow (−2), 1904-05
  Moscow (−2), 1903-04 Moscow (−2 vs list). These are probably questions of how the stats page classed mixed bills.
  Not yet examined.

**Built into the script (2026-09-30):** `pipeline/compare_season_stats.py` level 3 writes `ballet_counts.csv` and
`ballet_count_dates.csv`. A list date counts as the larger of what the list states itself (утро/вечеръ rows, "2
раза") and the number of separate Repertoire sessions that day playing one of its listed ballets, capped at the
list's rows for that date. Result: all three agree in 14 of 28.

**"Смѣшанныхъ" lines printed without a qualifier** are now reported separately (`stats_mixed_unqualified`), with a
second verdict that counts them in:
- **1899-00 Moscow: resolved, all three sources agree.** Footnote 12 gives the Bolshoi's 75th anniversary (6 Jan 1900:
  Торжество музъ / Мѣщанинъ во дворянствѣ / Танцовщики по неволѣ, бал.) and an "(опера и балетъ)" Иверская Община
  benefit (12 Apr 1900: Лакме / Фея куколъ). Both include a listed ballet, and the list prints both dates:
  62 + 2 = 64 = list = Repertoire.
- **1898-99 SP:** of the two mixed performances (footnote 8), the РТО benefit on 23 Jan 1899 is a gala ending with
  "Балъ изъ бал. Пахита"; nothing was found for the Литературный фондъ one. Counting the РТО gala, 53 + 1 = 54 =
  list = Repertoire in total. The list reaches 54 by including 21 Sep 1898 (A7) and leaving out 23 Jan (a charity
  gala, like section D).
- **1900-01 SP:** the one mixed performance is the РТО benefit of 30 Dec 1900 with "2-е д. бал. Фіаметта" (= D3).
  54 + 1 = 55 = list; the Repertoire has 56.
- **1903-04 Moscow:** one mixed performance, no footnote. The Repertoire has two candidates: the 18 Oct 1903 benefit
  (… "1-е д. Донъ-Кихотъ Ламанчскій") and the 24 Oct 1903 Tchaikovsky memorial (… "3-е д. Лебединое озеро"). The
  page doesn't say which it counts.
- **1901-02 Moscow:** the 20 Apr 1902 benefit with "Балетный дивертиссементъ" (F4). Not a listed ballet, so it is
  correctly outside the count.

**1894-95 SP resolved (2026-09-30): the stats page counts plain-divertissement drama bills as "русская драма и
балетъ".** Stats 28 vs list = Repertoire 26. Line by line, the Repertoire matches exactly: ballet Маріинскій 17,
Михайловскій 3, opera + ballet 4. The gap is on "русская драма и балетъ 4", where the Repertoire's listed-ballet bills
number 2: 25 Sep 1894 (Комикъ XVII столѣтія + Тщетная предосторожность) and 5 Apr 1895 (second-artists' benefit,
… + 3-е д. балета Пахита = footnote 6). Five Александринскій drama bills have a ballet element outside the lists: three
with the comedy-ballet Батюшкина дочка (15 Sep, 13 Oct, 11 Apr) and two with a plain "Дивертиссементъ" (21 Sep:
Дворянское гнѣздо; 29 Sep: Собака садовника / Въ бѣгахъ). The printed receipts decide it. 1,671.75 + 4,173.60 +
1,561.76 + 1,608.87 = 9,015.98 р., exactly the stats line, and no other pair of the five gives it. So in 1894-95 the
statistics counted the two divertissement bills as drama + ballet and the comedy-ballet bills as drama; the list
includes neither. (This is one season's evidence on RG's open question about plain "Дивертиссементъ", not a rule.)
Also noticed, receipts paused: the Маріинскій ballet receipts differ from the stats by exactly 200.00 р.

**1895-96 SP resolved (2026-09-30): a free student matinée with a ballet counted as drama.** Stats 51 vs list =
Repertoire 52. Every stats line is matched exactly: Маріинскій ballet 46; Михайловскій ballet 1 (17 Jan 1896,
Коппелія / Жертвы Амуру, 1,195.60 р. = stats); "(русская драма и балетъ) 4" = the four Михайловскій bills of 31 Aug,
1 Sep, 5 Sep and 12 Sep 1895 (a comedy or drama + Очарованный лѣсъ / Жертвы Амуру / Волшебная флейта), 2,457.95 р. =
stats to the kopeck. The 52nd performance is 3 Jan 1896, Александринскій утро, "Безплатный спектакль для воспитанниковъ
учебныхъ заведеній": Старый закалъ, др. + Очарованный лѣсъ, бал. (no receipts). The list gives it ("января 3"), and the
stats page doesn't count it as ballet or mixed. Presumably it is one of the 4 free student performances in footnote 2
of the Александринскій drama line, but that is inference, not stated.

Contrast with 1894-95: this season the Александринскій benefit of 29 Mar 1896 (Друзья-пріятели + Дивертиссементъ) is
NOT in the mixed line, because that line is fully accounted for by the Михайловскій bills. So a drama +
plain-divertissement bill was counted as mixed in 1894-95 but not in 1895-96, and the comedy-ballet bill (22 Jan 1896,
Батюшкина дочка) was again not counted as mixed. The yearbook's own practice varies by season.

**1904-05 Moscow narrowed, not fully resolved (2026-09-30).** Stats "Балетныхъ 39" (no theater or mixed lines) vs list
= Repertoire 41. The Repertoire's 41 sessions total 82,893.95 р. against the stats 82,893.92 р., a 3-kopeck difference,
so the two uncounted performances must be among the five with no receipts: three free student matinées (14 Nov, 6 Dec
1904, 24 Feb 1905), the 16 Feb 1905 benefit for the actors' retirement home (scenes from Макбетъ and Гамлетъ +
Фіаметта), and the 19 Apr 1905 Иверская Община charity morning (Волшебное зеркало). The list prints all five dates.
The likeliest reading is that the stats page left out the two charity performances: that fits 1902-03 and 1903-04,
where the stats page and the list both leave out charity bills (D4–D8). It is not proven, because receipts can't
separate performances that have none.

**1904-05 SP narrowed, not resolved (2026-09-30).** Stats 46 (130,012.64 р.), list 48, Repertoire 47 (135,020.94 р.).
The list's extra dates are the recorded disagreements A12 (17 Dec) and B1 (13 Feb; the Repertoire cell prints only
"Бенефисъ кордебалетныхъ артистовъ" and 8,750.70 р.). The Repertoire's extra is E4 (29 Mar, a charity Эсмеральда, no
receipts). No choice of performances matches the stats count and receipts exactly. The reading most consistent with
the other seasons is: the stats page leaves out the two charity performances (29 Mar Эсмеральда, and 6 Apr Рафаэль +
Наяда и рыбакъ + Брама, no receipts) and includes the 13 Feb corps-de-ballet benefit (B1). The receipts would then fit
only if the 28 Dec 1904 morning "Корсаръ", printed 15,291 р. 95 к. and already flagged as a likely print typo (#111
notes), had taken 1,532 р. 95 к. That is not a simple one-digit slip, so it stays unresolved. It goes with the receipt
audit, which is paused until RG's fold checks.

**1900-01 SP resolved (2026-09-30): a French-company benefit ending with a ballet is counted as French.** Stats 54
ballet + 1 unqualified mixed (the 30 Dec 1900 РТО gala, D3) = 55; list 55; Repertoire 56. The list omits D3, so the
Repertoire's other 55 = the list's 55, and the stats page counts one of them elsewhere. The ballet receipts decide it.
The Repertoire's 55 total 149,818.37 р., 2,590.51 р. above the stats ballet line. The 2 Mar 1901 Михайловскій
"Bénéfice de M-lle Barety" (Rosalie / Nos alliées / Les élèves de Dupré, ballet) took 2,590.50 р., the only match.
So the stats page counts it under "Французскихъ", while the list gives it under "Ученики Дюпрэ". Removing it gives 54
and a 1-kopeck receipts difference. Also noted, receipts paused: the stats page prints 5,043.90 р. for the РТО mixed
performance, but the Repertoire cell for 30 Dec 1900 prints no figure (scan-checked in #111).

**Summary of the ballet-count reconciliation (2026-09-30).** Of the 28 season-cities with both a stats page and a
list:
- 14 agree in all three sources as counted by the script.
- 1899-00 Moscow agrees once its unqualified mixed line is included.
- The others are explained by how the stats page classified particular bills: Кольцо любви as "Феерій" (1892-94
  Moscow), plain-divertissement drama bills as drama + ballet (1894-95 SP), a free student matinée as drama
  (1895-96 SP), a French-company benefit as French (1900-01 SP).
- Or by the recorded list/Repertoire disagreements (A, B, D, E).
- Two stay open: 1904-05 Moscow (which two receipt-less performances the stats omit) and 1904-05 SP (receipts tied to
  the 15,291.95 р. Корсаръ figure).
- 1903-04 Moscow's single unqualified mixed performance can't be identified from the page.

### Is the Repertoire complete for ballet? (RG's priority, 2026-09-30)

**1906-07 to 1908-09 (stats pages, no ballet lists).** A Repertoire session counts as ballet when a work is printed with a
"бал" genre (the parent_genre rule can't apply without a list):
- **1907-08 SP:** 52 / 172,712.87 р. = stats, exactly.
- **1908-09 SP:** 41 pure-ballet sessions + 7 bills with "Шопеніана, сюита" (Евника, Египетскія ночи, Павильонъ Армиды …)
  = 48 / 156,197.22 р. = stats, exactly. The only one left out is the Lohengrin + Балетный дивертиссментъ charity bill.
- **1908-09 Moscow:** 48 + the Арендсъ benefit (Нуръ и Анитра, хореограф. карт. / Раймонда) = 49 / 101,477.91 р. = stats,
  exactly.
- **1906-07 SP:** 55 sessions; receipts 168,182.50 р. = stats exactly; the stats count 53 leaves out 2 of the 3 receipt-less
  sessions.
- **1906-07 Moscow:** Repertoire 51 vs stats 49 (the Repertoire has more).
- **1907-08 Moscow:** Repertoire 47 vs stats 48. The one short is the 11 Nov 1907 Большой "Коппелія", printed "оп."
  (scan-confirmed genuine, #100; 2,578.77 р.). As a ballet, 48 = stats. Receipts remain 5,002.94 р. short of the stats
  (paused with the other receipt leads).

**Conclusion, for every season with a stats page (1891-92 to 1908-09, except 1905-06):** the Repertoire has at least as
many ballet performances as the stats page counts, once the stats page's own classing and the recorded list
disagreements are allowed for. No ballet performance the yearbook's statistics count is missing from the Repertoire.
Many seasons match performance for performance, often to the kopeck in receipts. Open items affect receipts or which
receipt-less performance the stats page omitted, never a missing ballet performance. 1890-91 (no stats page) and 1905-06
(no stats page found) aren't covered by this check.

## Petersburg drama excess, 1906-07 (2026-09-30): resolved except a small Александринскій receipts residual

Stats: Russian drama by theater, Александринскій 197 (247,576.17 р.), Михайловскій 25 (10,353.15 р.), Маріинскій 1
(7,262.50 р.). Opera 159.
- **Михайловскій:** the Repertoire's 24 receipted Russian-drama sessions total 10,353.15 р., exactly the stats figure.
  The unreceipted extras are:
  - **the Moscow Art Theatre tour, 24 performances, 23 Apr – 17 May 1907.** The 23 Apr cell is headed "Спектакли
    Московскаго Художественнаго Театра"; the plays are Горе отъ ума, Три сестры, Брандъ, Драма жизни and Дядя Ваня
    (9 May morning, "На памятникъ А. П. Чехову");
  - a charity bill on 14 Feb and one morning performance on 6 Dec.
  The stats count 25 = the 24 receipted + one of those two. The 1906-07 stats page has no line for the Art Theatre (the
  1909-10 page has one: "Московскаго художественнаго театра 35").
- **Маріинскій:** stats 1 = the Стрѣльская 50-year benefit, 7,262.50 р., exactly. The Repertoire's extras are two charity
  operetta evenings with no receipts (Веселая вдова, 16 Dec; Боккаччіо, 23 Apr), and 4 performances of "Сказаніе о
  невидимомъ градѣ Китежѣ", printed without a genre. The classifier had counted them as drama; they are Rimsky-Korsakov's
  opera, and with them the opera count is 155 + 4 = 159 = stats.
- **Александринскій:** 197 = 197 after the fix below. The receipts are 2,307.23 р. higher than the stats, with no single
  session or pair matching; left with the paused receipts leads. Also noticed: the 26 Nov 1906 evening, printed
  "Безплатный спектакль для георгіевскихъ кавалеровъ", carries receipts of 600.75 р. That is odd for a free performance
  and worth a scan look sometime.

**Classifier change:** a session whose works all lack a genre is now "unknown", not drama. It had inflated drama with
Китежъ and three "Драма жизни" cells. Level 2 now: 59/254 family rows exact.

**Pattern for 1907-09 (to test next):** the excess is unreceipted runs by visiting companies (the Art Theatre in 1906-07;
likely the spring 1908 Михайловскій run too, but that is not assumed) and charity evenings. The stats pages count neither
as Russian drama.

## Petersburg drama excess, 1907-08 (2026-09-30): explained except a small Александринскій residual

Stats: Russian drama 217 (263,589.03 р.), single line, no theater breakdown. Footnote 1: 2 benefits, 3 free student
performances, 1 free performance for the георгіевскіе кавалеры. The Repertoire counts 268 drama sessions:
- **Александринскій 218:** 214 with receipts (265,164.75 р.) + 4 without (the free performance for the георгіевскіе
  кавалеры, 26 Nov; two free student mornings, 6 Dec and 20 Feb; the prompters' benefit, 21 Apr). These are the kinds the
  footnote says are included. It is one over the stats (218 vs 217), with receipts +1,575.72 р.; no single session
  matches. Left with the paused receipts leads.
- **Маріинскій 6 and Михайловскій 6:** charity evenings, all without receipts.
- **Михайловскій, 38 sessions, 14 Apr – 13 May 1908, all without receipts:** Росмерсхольмъ, Жизнь человѣка, Докторъ
  Штокманъ, Брандъ, Вишневый садъ, Горе отъ ума.
  - **Not on the Imperial record:** the yearbook's own "Списокъ пьесъ, исполненныхъ на сценахъ Императорскихъ театровъ въ
    сезонѣ 1907–1908 гг." (1907-08_ProductionStats.pdf, file p. 2 = printed p. 127) has none of these plays among its
    Petersburg Russian-drama entries: no Брандъ, Вишневый садъ, Горе отъ ума or Докторъ Штокманъ in their alphabetical
    places.
  - **The company is not named** in the Repertoire (p042, checked at 300 dpi) or anywhere found in the 1907-08 materials
    we hold. The digitized reviews are ballet only.
  - **Why it is probably the Moscow Art Theatre (strong inference, not a finding):** the repertoire is that theatre's (the
    named 1906-07 tour also gave Брандъ and Горе отъ ума); it is the same spring slot at the same theatre; and the
    1909-10 stats page gives the Art Theatre its own line.

So 268 = 217 + 1 (Александринскій) + 12 charity + 38 spring run. Nothing counted by the stats page is missing from the
Repertoire.

## Petersburg drama excess, 1908-09 (2026-09-30): explained

Stats: Russian drama 223 (281,966.05 р.); footnote 1: 1 benefit and 4 free student performances. The Repertoire counts
273 drama sessions:
- **Александринскій 223 = stats, exactly.** Its 4 receipt-less sessions are the free student performances (14 Nov,
  6 Dec, 4 Feb) and the free Gogol-centenary performance (20 Mar). Receipts are 317.43 р. short of the stats; left with
  the paused leads.
- **Moscow Art Theatre at the Михайловскій, 46 sessions, 30 Mar – 3 May 1909, no receipts.** Named on the scan: the 30 Mar
  cell reads "Спектакли Московскаго Художественнаго театра". Plays: Синяя птица, Ревизоръ, Три сестры, У царскихъ вратъ.
- **Two charity benefits at the Михайловскій with receipts** (17 Dec 1908: 3,225.75 р.; 26 Jan 1909: 749.25 р.). They are
  not in the stats' drama line; from 1898-99 the stats' receipts exclude charity.
- **Маріинскій:** a charity operetta (Птички пѣвчія, 20 Apr, no receipts), and "Черевички, эп," (6 Feb, 3,283.90 р.). That
  is Tchaikovsky's opera, with the genre misprinted in the yearbook itself (added to genuine_print_typos.md), so it
  belongs to opera, not drama.

So 273 = 223 + 46 + 2 + 1 + 1. Nothing counted by the stats page is missing from the Repertoire. Across 1906-07 to
1908-09 the pattern holds: the "excess" is visiting-company runs (the Art Theatre named in 1906-07 and 1908-09; the
1907-08 run unnamed) and charity evenings, which the stats pages don't count as Russian drama.

## 1909-10 SP (2026-09-30): Moscow Art Theatre line matches; residuals wait for a transcription fix

**Transcription issue in the new 1909-10 Repertoire (the other chat's work; reported, not fixed here):** 46 French-play
entries on 6 pages carry a Cyrillic genre that the print doesn't have ("ком." 32, "пьеса" 12). Example, repertoire_1909-10_p023
(p. 24), 15 Dec 1909, Михайловскій: the scan (500 dpi) prints "La rampe, pièce nouv." / "Les vacances d'Antoinette, com. nouv.",
while the raw has genres "пьеса" / "ком.". Other seasons have 1–15 such entries each, mostly genuine, like "Viola tricolor, ком.".
The comparison script's Cyrillic-genre rule would count these French performances as Russian drama.

Counting every Latin-titled play as foreign for this check:
- **"Московскаго художественнаго театра 35" = the Repertoire's 35 Михайловскій sessions, 19 Apr – 14 May 1910,
  exactly.** In 1909-10 the stats page counts the Art Theatre on its own line, not as Russian drama.
- French 100 / 107,243.10 р. vs 107 (99 with receipts) / 107,172.60 р.
- Ballet 51 / 167,180.22 р. vs 47 + 3 Шопеніана bills = 50 / 165,051.62 р.
- German 25 vs 19 + 3 French/German double bills.
- Russian drama 258 / 327,041.88 р. vs Александринскій 236 + Михайловскій 33 = 269 / 328,682.43 р. (+11).

These residuals are left until the genres are corrected, then to be rerun.

**1909-10 SP rerun after the Main session's fix (f0f0545) of the 46 added genres:** French 101 vs stats 100 (receipts
−70.50 р.). Russian drama 294, which includes the 35 Moscow Art Theatre sessions that the stats page puts on their own
line; without them, 259 vs 258. German 22 vs 25, with 3 more in French/German double bills (mixed). Ballet 47 vs 51, with
the Шопеніана bills in mixed. The 1909-10 residuals are now as small as the other seasons'.
