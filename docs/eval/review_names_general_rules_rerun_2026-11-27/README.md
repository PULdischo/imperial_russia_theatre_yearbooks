# General rules G1-G3 re-run on the remaining ties (2026-11-27)

Status index item 1(a): the rules RG ruled on 2026-11-07 ran then against candidate lists cut to 8; the matcher now keeps
every candidate (c27d36f; up to 38 per mention). Scripts are copies of `../review_names_general_rules_2026-11-07/` with
paths changed and ONE new safeguard in `g2_candidates.py` (below). Nothing here changes the database or
`docs/eval/review_mention_links.csv`; `proposed_links.csv` waits for RG.

Run: `g1_candidates.py`, `g2_candidates.py`, `oldcast_check.py`, `g3_candidates.py`, `build_links.py` (writes `new_links.json`).

## Result

Tied person mentions before: 1,813. Picks: G2 191 → 179 after the new safeguard and the old-cast check; G1 2; G3 1.
`build_links.py`: 180 new rows, 2 skipped because RG had already unlinked them (Бочаровъ 1901-02 SP pupil, Лебедева 1901-02
Moscow old cast). Held (`held.csv`, 6): the 5 pupil picks, which fail RG's nine-season rule of 2026-11-07 (another
person of that surname and gender joined or graduated within nine seasons: Ивановъ x4 SP, Ѳедорова Moscow 1897-98);
G1 «г. Булгаковъ» 1910-11 Moscow (open merge question, Group D). **Proposed: 174 links** (`proposed_links.csv`; G2 173,
G3 1); ties would fall 1,813 → 1,639. Largest: Ѳедорова 2-я Софія 45, Ѳедорова 3-я Ольга 22, Смирновъ 1-й 19,
Смирнова 4-я 17, Смирновъ 2-й 12, Ивановъ 2-й 10, Ѳедорова 1-я Екатерина 10.

## New safeguard (G2): a feminine-looking ending is also the masculine genitive

The first run picked 10 mentions on gender from the surname ending in creator wording. 8 were wrong: «бал. М. Петипа и
Л. Иванова» x6 (Лев Ивановъ, sent to Лариса), «художника К. М. Иванова» (scenery painter), «Весталка», бал. М. Иванова
(composer). Rule added: without a woman's honorific or a feminine ordinal, the ending does not decide gender after
creator wording (бал., балетъ, соч., постановка, танцы, музыка, декорація, художника …) or after bare initials. It
removed exactly those 8 (+5 like them) and kept the two performer mentions (Китри—«1-жа Федорова 2-я»).

## Scan sample (checked by Claude, finding aid)

10 random proposed links (`scan_sample.csv`, full-res `outputs/reviews/images/`): printed as transcribed 10/10, the
printed number/gender supports the pick 10/10 (Ѳедорова 3 / 2 / 1 / 2-я Moscow; «Иванова 4» = Надежда, printed «Иванова
4-я» in the 1900-01 list; Ивановъ 2-й, 4, 1-й SP; Ѳедорова 3-я, «Хита—1-жа Ѳедорова 2-я»). The flat-top 3 of the
1904-05 Moscow face was compared with «5-й картинѣ» on the same line: the name's digit is 3.

## Found on the way (not in this batch)

1. Production already holds 16 links of the masculine-genitive kind, made by the matcher ('bare+ranked' etc.):
   «Л. Иванова» → Лариса Михайловна x8, → Ираида Даниловна x1, → a record «Иванова» x1 (all Лев Ивановъ, creator);
   «музыка А. Давидова» → Давыдова, Елизавета Денисовна x4 (composer); «танцовщика А. Обухова» → Обухова, Евгенія
   (1913-14); «Декорація К. Ѳ. Вальца и г. Какурина» → Какорина, Екатерина (1894-95). Plus «Эскизъ художника А. Д.
   Головина» → Головина, Марія (already decisions.md item 4).
2. The 1864 premiere cast of «Конекъ-Горбунокъ» quoted in 1895-96 SP (p005__b003 «Составъ первыхъ исполнителей …» →
   p006__b002) is not in `review_historical_passages.csv`; its names are linked to 1890s people in production (e.g.
   «А. Богдановъ» → Богданова, Александра; Волковъ, Пишо, Васильева, Радина, Соколова 2-я, Ѳедорова 1-я/2-я, Гельцеръ,
   Игнатьевъ, Щербаковъ, Іогансонъ). The old-cast safeguard does catch it for the general rules.
