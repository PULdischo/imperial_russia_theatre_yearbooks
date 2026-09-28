# Ballet productions lists — items for RG to check against the scans

Source: the per-season ballet productions lists ("Балетъ" section of the
списокъ пьесъ), 1890-91 – 1904-05, SP + Moscow, 29 lists / 47 pages
(`pdf/Spiski_BalletProductions/`). Transcribed with `qwen3-vl-plus`, then
every entry and field scan-checked (known_issues.md #100). Everything
below is **left exactly as printed / as best read from the scan**; none
of it has been corrected, and no reading was settled from the Repertoire
data (the lists are an independent audit of it). Page refs are
`season city page_index` (p000 = first page of that list) + printed page.

Per-change detail for every item: `outputs/ballet_productions_pilot/verify_logs/<page_id>.csv`
(kind = `genuine_print` / `uncertain`).

## 1. Things that don't add up (numbers and dates)

| # | Where | Entry | What's printed | Why it doesn't add up |
|---|---|---|---|---|
| 1 | 1897-98 SP (pp. 32–33 spread) | #2 Дочь микадо | "декабря 38"; also "ноября 9, 24, 16, 19" | impossible day; ноября dates out of order. 9 dates = Всего—9 |
| 2 | 1897-98 Moscow p001 (p. 40) | #9 Пери | "Исполнено: 1897 г.—февраля 12" | Feb 1897 is before the 1897-98 season (Feb 1898?). Zoom-checked: 1897 is clearly printed |
| 3 | 1899-00 SP p000 (p. 46) | #6 Дочь Микадо | "…1899 г.—… апрѣля 19" (no new year printed) | year carries forward as 1899, but April falls in 1900 by season |
| 4 | 1902-03 SP p001 (p. 45) | #14 Коппелія | "1903 г.—ноября 6. 1903 г.—февраля 15" | November 1903 is outside the 1902-03 season (1902?) |
| 5 | 1902-03 SP p001 (p. 45) | #25 Тщетная предосторожность | "1904 г.—апрѣля 27" | April 1904 is outside the season (1903?) |
| 6 | 1904-05 Moscow p000 (p. 145) | #4 Золотая рыбка | 6 dates, "Всего—7 разъ"; ноября 14 note "2 раза: утромъ и вечеромъ" | the only dates-vs-Всего mismatch in the whole corpus; probably consistent (14 Nov counted twice) |

All six were read twice from the scan, by the checking agent and then by a
second close-up zoom (2026-09-28); in every case the transcription matches
what's printed, so these are the print itself, not reading errors.

Every other entry's printed dates match its printed Всего (1778 counted
dates vs 1779 total across all 467 entries; the difference is #6).

## 2. Uncertain readings (blurred, damaged or ambiguous type)

| # | Where | Entry | Best reading | Alternative | Note |
|---|---|---|---|---|---|
| 7 | 1890-91 Moscow p000 (p. 38) | #7 Сатанилла | сентября **23** | 22 | **RESOLVED — RG, original volume, 2026-09-28:** 23 |
| 8 | 1890-91 Moscow p000 | #8 Хрустальный башмачекъ | сентября **30**, января **30** | 20, 20 | **RESOLVED — RG, original volume, 2026-09-28:** 30, 30 |
| 9 | 1890-91 Moscow p000 | #8 Хрустальный башмачекъ | "Всего—**4** раза" | — | **RESOLVED — RG, original volume, 2026-09-28:** 4 |
| 10 | 1890-91 SP p001 (p. 32) | #11 Фіаметта | ~~ноября 16~~ → **18** | — | **RESOLVED — RG, original volume, 2026-09-28:** 18 (scan too blurred; the checker's 16 was wrong). Agrees with the Repertoire |
| 11 | 1890-91 SP p001 | #11 Фіаметта | "Сенъ Леона" (no hyphen) | Сенъ-Леона | **RESOLVED — RG, original volume, 2026-09-28:** no hyphen |
| 12 | 1890-91 SP p001 | #12 Шалость Амура | февраля **28** | 26 | **RESOLVED — RG, original volume, 2026-09-28:** 28 |
| 13 | 1892-93 Moscow p001 (p. 39) | #10 Приключенія Флика и Флока | Морен**г**о | Морен**і**о | **RESOLVED — RG, original volume, 2026-09-28:** Моренго |
| 14 | 1896-97 Moscow p001 (p. 40) | #13 Хрустальный башмачекъ | ~~"Мюлъ-ендорфера"~~ → **Мюльендорфера** | — | **RESOLVED — RG, 2026-09-28:** ь, and the hyphen is only the line break |
| 15 | 1896-97 SP p000 (p. 33) | #2 Волшебная флейта | Бернад**е**лли (RG's reading, from the scan) | Бернад**ѣ**лли / Бернад**ь**лли (checker) | **Still flagged** — RG "pretty sure" it's е; confirm in the 1896-97 volume. Cross-check: the ballet lists 1892-93, 1893-94, 1894-95 and 1895-96 all print "соч. Бернаделли", as do the season reviews (1892-93 SP ballet, on this ballet's history; 1894-95 SP ballet, "г-жи Бернаделли … г. Бернаделли", visiting artists from Vienna). Only 1897-98 has "Бернарделли". He is in no staff roster (query_log 2026-09-28) |
| 16 | 1897-98 SP spread | #5 Конекъ-горбунокъ | hyphen | — | **RESOLVED — RG, from the scan, 2026-09-28:** a faint/misprinted hyphen; kept as "-" |
| 17 | 1901-02 SP p001 | #21 Пробужденіе Флоры | "Всего—2 раза." | no final period | **RESOLVED — RG, from the scan, 2026-09-28:** a faint period; kept "раза." (a period normally ends these lines) |
| 18 | 1902-03 SP p000 (p. 44) | #4 | "Г***," | "Г***" | **RESOLVED 2026-09-28:** three asterisks in a triangle (asterism = withheld name), recorded as **Г⁂**; close-up shows no comma here (1903-04 and 1904-05 do have one). RG: the person is Всеволожскій → research layer, not the transcription |
| 19 | 1903-04 SP p001 (p. 45) | #3 | "Г***" | — | **RESOLVED 2026-09-28:** same asterism, recorded **Г⁂,** (comma printed). Also 1904-05 SP #4 (Г⁂,) and 1897-98 Moscow #15 Шалости сверчка "музыка ⁂" (composer unidentified; RG doesn't know yet) |
| 20 | 1902-03 SP p001 #18; 1903-04 SP p001 #17; 1904-05 SP p001 #20 | Пахита | Дельдевез**а** | Дельдевез**ъ** / **л** | **RESOLVED — RG, from the scan, 2026-09-28:** all three are a poorly printed "а". 1903-04 and 1904-05 show the same damaged glyph (the entry's wording is identical, so the type was probably reused). The 1904-05 checker's "Дельдевезъ" was a misreading, now corrected. Every season prints Дельдевеза |
| 21 | 1903-04 SP p001 | #4 | "Всего—3 раза" | — | **RESOLVED — RG, from the scan, 2026-09-28:** a faint em dash; kept "Всего—3 раза." |
| 22 | 1904-05 SP p001 (p. 139) | #29 Фея куколъ | "сюжетъ **и.** Асрейтера" | **н.** | **RESOLVED — RG, from the scan, 2026-09-28:** printed "и.", a lowercase slip for the initial "И." (Josef Hassreiter); kept as printed |
| 23 | 1890-91 SP p001 (p. 32) | #13 Эсмеральда | ~~П.~~ → "музыка **Ц.** Пуни" | — | **RESOLVED — RG, original volume, 2026-09-28:** Ц. (the checker's П. was wrong) |

## 3. Printing slips and typesetting quirks (candidates for `genuine_print_typos.md` once you've confirmed them)

- 1896-97 Moscow p001 #10 Сатанилла: "(Le diable amour**ea**ux)"
- 1897-98 Moscow p001 #11 Тщетная предосторожность: "(La Fil**i**e mal gardée)"
- 1900-01 SP p001 #22 Щелкунчикъ: "**в**аимствованъ" (заимствованъ)
- 1901-02 Moscow p000 #3 Донъ-Кихотъ: "сентябр**и** 9"
- 1901-02 SP p000 #9 Жизель: "По**сг**авленъ" (Поставленъ)
- 1901-02 SP p001 #16 Наяда и рыбакъ: "октябр**и** 10" and "**Вв**его—1 разъ"
- 1898-99 Moscow p001 #8 Наяда и рыбакъ: "1899 г.—г.—января 3" (doubled "г.—")
- 1893-94 Moscow p000 #11 Эсмеральда: "ноября 7 14 декабря 30" (comma and semicolon missing)
- Missing periods / dashes: 1893-94 Moscow #10 "1893 г —"; 1894-95 Moscow #5 "въ 4 д и 8"; 1895-96 Moscow p001 #8 "4 карт ,"; 1898-99 SP p001 #17 "Всего 1 разъ"; 1899-00 SP #21 "1900 г. апрѣля"; 1901-02 SP #9 "2 д, соч."
- Пахита, 1903-04 SP #17 and 1904-05 SP #20: the same damaged "а" in "Дельдевеза" in both years (entry wording identical; the type was probably reused)
- 1904-05 SP p001 #29 Фея куколъ: "сюжетъ **и.** Асрейтера", lowercase "и." for the initial "И." (Josef Hassreiter; RG confirmed)
- 1897-98 SP p. 32 #5 Конекъ-горбунокъ: the hyphen in the title printed as a short raised dot (faint/misprinted hyphen, RG confirmed)
- 1899-00 SP p000 #3 Волшебная флейта: "актѣ.," and "Всего—1 разъ,"; 1899-00 SP p001 Эсмеральда "Всего--7 разъ."

## 4. For the Repertoire audit (not a list problem)

- The Repertoire data has "**Рустикальный** башмачекъ" at the Большой on 1890-11-11; the list prints Хрустальный башмачекъ on ноября 11 — very likely a Repertoire misread. To be picked up in the list-vs-Repertoire comparison.

## 5. Interim source: 1899-00 Moscow (stand-in copy)

`pdf/Spiski_BalletProductions/ForUpload_1899-00_Spisok_BalletProductionsMoscow.pdf`
(p. 55, entries 1–13) is **not from RG's volumes**. It's a black-and-white
Google Books scan of the University of Michigan copy that RG found on
2026-09-28, original image kept in `pdf/Spiski_BalletProductions_interim_sources/`.
Checked on arrival: every entry's printed dates add up to its "Всего".
Use it until RG requests and scans a physical copy, then **replace it and
re-verify that list against the new scan**. Faint punctuation and fine ъ/ь
distinctions are less reliable on this bilevel copy.
