# Masculine genitive read as a woman: 16 review-mention links (found 2026-11-27)

A feminine-looking ending (-ова, -ева, -ина) is also the masculine genitive. In creator wording («балетъ Л. Иванова»,
«музыка А. Давидова») the matcher linked such names to women. Found during the G1-G3 re-run
(`../review_names_general_rules_rerun_2026-11-27/README.md`). Every printing below read on the full-res page image
(`outputs/reviews/images/`) by Claude, as a finding aid; all print as transcribed except where noted.

## A. «Л. Иванова» = Лев Ивановичъ Ивановъ (a3f51b5c, Q282950), creator credits — 10 mentions

| mention | season | page | printed | linked now |
|---|---|---|---|---|
| 14324 | 1901-02 SP | p009 (caption, f. 175) | «Пробужденіе Флоры», бал. М. Петипа и Иванова, муз. Р. Дриго | a record «Иванова» |
| 16451 | 1902-03 SP | p003 | «Фіаметта» … танцы и постановка М. Петипа и Л. Иванова | Лариса Михайловна |
| 17246 | 1902-03 SP | p019 | исполненъ былъ балетъ Л. Иванова «Гарлемскій Тюльпанъ» | Лариса |
| 18162 | 1903-04 SP | p001 | «Очарованный лѣсъ», балетъ въ 1-мъ дѣйствіи Л. Иванова, музыка Р. Дриго | Лариса |
| 19413 | 1903-04 SP | p017 | «Гаарлемскій тюльпанъ», Л. Иванова и Б. Шелля | Лариса |
| 21734 | 1904-05 SP | p015 | Танцы и постановка — М. Петипа и заслуженнаго артиста Императорскихъ театровъ Л. Иванова | Лариса |
| 23647 | 1905-06 SP | p006 | «Гарлемскій тюльпанъ» … сочиненіе Л. Ива-|нова, музыка Б. Шеля | Лариса |
| 25048 | 1906-07 SP | p001 | балетъ М. Петипа и Л. Иванова и г. Дриго «Пробужденіе Флоры» | Лариса |
| 25695 | 1906-07 SP | p011 | «Очарованный Лѣсъ», балетъ Л. Иванова и Р. Дриго | Лариса |
| 23648 | 1905-06 SP | p006 | (see B) | Ираида Даниловна |

Context: Лев Ивановъ's creator credits up to 1901-02 («Иванова», «Ивановымъ», 1891-92 on) are already linked to him
(query 2026-11-27); the wrong links start once he is off the staff lists (d. Dec 1901), when the matcher ranks a listed
living Иванова first. «заслуженнаго артиста» (21734) is masculine.

## B. Duplicated word in our transcription (23648)

1905-06 SP p006: the print has «сочиненіе Л. Ива-» at a line end and «нова, музыка Б. Шеля» on the next line. Our
text reads «сочиненіе Л. Иванова,\nИванова, музыка» — the second «Иванова» is not in the print. Fix: a row in
`docs/eval/review_text_corrections.csv` removing it; the mention (now linked to Ираида Даниловна) then disappears.

## C. «А. Давидова» = the composer А. А. Давыдовъ («Давыдовъ, А. А.», 910162fe, Q4153603, from the 1907-08 ballet list) — 4 mentions

| mention | season | page | printed |
|---|---|---|---|
| 23991 | 1905-06 SP | p013 | «Принцъ садовникъ» … В. Я. Свѣтлова, музыка А. Давидова, постановка г-жи Куличевской |
| 24155 | 1905-06 SP | p014 | балетъ Свѣтлова, музыка Давидова «Принцъ садовникъ» |
| 26489 | 1907-08 SP | p003 | «Принцъ-Садовникъ», В. Я. Свѣтлова, муз. А. А. Давидова, постановка К. М. Куличевской |
| 26678 | 1907-08 SP | p014 | балетъ … В. В. Свѣтлова, музыка г. Давидова «Принцъ Садовникъ» |

All four now link to Давыдова, Елизавета Денисовна. The composer record is not among the matcher's candidates
(only Давыдова Марія / Елизавета are), so the link needs an explicit row.

## D. No record for the person — unlink

- 27529, 1913-14 SP p004: «дебютъ вновь принятыхъ въ труппу … а также танцовщика А. Обухова» → now Обухова, Евгенія
  Константиновна. «танцовщика» is masculine and «А.» fits neither male Обуховъ on record (Михаилъ Константиновичъ,
  Сергѣй Трофимовичъ). Newly engaged 1913 (rosters in the data end 1911-12), so there is no record yet.
- 3287, 1894-95 Moscow p007 (caption): «Сцена 3-го дѣйствія балета Ж. Перро—«Катарина». (Декорація К. Ѳ. Вальца и
  г. Какурина).» → now Какорина, Екатерина Сергѣевна (a Moscow dancer). «г.» = a man, a scenery painter; no Какуринъ on
  any staff list (only Какоринъ Михаилъ, Moscow Administrators 1905-06).
