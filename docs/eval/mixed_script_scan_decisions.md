# Mixed-script queue — scan decisions, 2026-10-09

Every word `parse_reviews.repair_mixed_script` left `unresolved` or `boundary`,
checked against the scan at zoom. The governing fact, established first on
`Флеръ-де-Лисъ` and confirmed on every Cyrillic case below: **the print is
Cyrillic and the Latin letters are the model's**, exactly as the earlier
`de-Бріена` check found.

Three cases go the OTHER way, and three are not letter errors at all. Those are
the reason this queue had to be checked one by one rather than repaired by rule.

## A. Confirmed Cyrillic — repair toward Cyrillic (19)

| printed | extracted | repair | page |
|---|---|---|---|
| дѣй-ствіяхъ | `дѣйstвіяхъ` | дѣйствіяхъ | 1893-94 SP ballet p004 |
| Ва-сильева | `Ваsильева` | Васильева | 1893-94 SP opera p011 |
| сво-его | `своego` | своего | 1893-94 SP opera p022 |
| хитро-сти | `хитроstи` | хитрости | 1893-94 SP opera p037 |
| скороходъ | `скорohодъ` | скороходъ | 1894-95 SP ballet p010 |
| Ка-саткина | `Каsаткина` | Касаткина | 1895-96 SP ballet p025 |
| Нос-кова | `Носkova` | Носкова | 1896-97 SP ballet p012 |
| тебѣ | `tebѣ` | тебѣ | 1896-97 SP ballet p023 |
| дивер-тиссементъ | `диверtissementъ` | дивертиссементъ | 1897-98 SP ballet p029 |
| **Апрѣля** | `Aprilя` | **Апрѣля** | 1899-00 MSK all p010 |
| Чекетти | `Чеketti` | Чекетти | 1899-00 SP ballet p004, p042 |
| Грималь-ди | `Гримальdi` | Гримальди | 1899-00 SP ballet p004 |
| Кше-синская | `Кшеsинская` | Кшесинская | 1899-00 SP ballet p031 |
| **танцова-ли** | `tancovaли` | **танцовали** | 1901-02 SP ballet p023 |
| сво-имъ | `svoimъ` | своимъ | 1902-03 SP opera p016 |
| Пар-тіи | `Парtii` | Партіи | 1902-03 SP opera p020 |
| Имитація | `Имитacja` | Имитація | 1905-06 MSK ballet p009 |
| скороходы | `скорohоды` | скороходы | 1905-06 SP ballet p013 |
| дерева | `derева` | дерева | 1907-08 SP ballet p007 |

**Two of these no lookalike map could ever have produced**, which is why the
`c` and `i` mappings were withdrawn before this sweep:

- `Aprilя` -> **Апрѣля**: the Latin `i` stands for **ѣ**, not `и` or `і`.
- `tancovaли` -> **танцовали**: the Latin `c` stands for **ц**. Confirms the
  same reasoning that found `cапельмейстера` should be `капельмейстера`.

And two settle the і/и question the withdrawn `i` mapping raised: the print has
**Чекетти** and **Гримальди** with `и`, so the blind `i`->`і` would have been
wrong both times. But `Партіи` takes `і` — the position decides, and only the
page can say.

## B. Confirmed LATIN — repair toward Latin, the Cyrillic is the intrusion (3)

`repair_mixed_script` has no mechanism for this direction yet.

| printed | extracted | repair | page |
|---|---|---|---|
| Valse bohé-mienne | `bohémiennе` | bohémienne (Latin final e) | 1899-00 SP ballet p010 |
| P o l o n a i s e | `Polonaisе` | Polonaise (Latin final e) | 1899-00 SP ballet p035 |
| **Pana-deros** | `Рапаderos` | **Panaderos** | 1907-08 SP ballet p010 |

`Panaderos` is the Raymonda dance. The model read the Latin `Pana` as Cyrillic
`Рапа`, so Cyrillicising it — the obvious-looking repair — would have produced
`Рападерос`, a word that never existed. This was flagged as a risk before the
sweep and the scan confirms it.

## C. Not a letter error (3)

| case | what the page shows | action |
|---|---|---|
| `l’HermitageЛ` | Bakst's plate letters `Théâtre de l'Hermitage`, then on its OWN line `Л. Бакстъ.` | insert the separator; both halves correct |
| `ПетипаLouis` | two caption lines: `«Ученики Дюпрэ», бал. М. Петипа` / `Louis XV et M-me de Pompadour (…)` | insert the separator; both halves correct |
| `Картина·IX` | `Картина. IX. На соборѣ Парижской Богоматери.` | the `·` is a misread **period**; `Картина. IX` |

## D. Not an error at all — a false positive of the check (1)

`XLVлѣтнюю` — the print reads `за XLV-` / `лѣтнюю службу`. That hyphen is a
**genuine compound hyphen** (45-year), not a soft line-break hyphen, and the
stored raw text `XLV-\nлѣтнюю` is correct. The reflow in
`quality_checks_reviews.py` strips it and manufactures the flag. A reflow should
keep a hyphen that follows a numeral or Roman numeral.

## E. Settled by existing ruling, NOT scan-checkable (1)

`XIІІ` -> `XIII`. Cyrillic `І` and Latin `I` are **glyph-identical**, so no
amount of zoom can distinguish them — which is precisely why RG's gold ruling
exists: Roman numerals are Latin here, because a Cyrillic `І` makes the text
unsearchable. Already recorded in `repair_mixed_script`'s docstring.
