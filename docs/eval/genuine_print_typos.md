# Genuine print typos and typesetting quirks

A running collection of confirmed errors and oddities in the *original*
1890–1908 yearbook printing itself — not extraction or OCR errors. Every
entry here was scan-verified directly against the source page image
before being added; per this project's verbatim-preservation rule
(`CLAUDE.md`), none of these are "corrected" anywhere in the dataset —
they're transcribed exactly as printed, dropped letters, wrong words,
worn type and all.

Kept here purely because they're a nice trace of the actual human hands
that set this type by hand under deadline, well over a century ago —
and, per the "material constraints" section below, of the physical
production process itself (running out of page, a fold swallowing a
figure) rather than just individual keystrokes. Add to it as new ones
turn up — no format requirements, just: what's printed, what it "should"
say, where, and why it's confirmed genuine rather than an extraction
slip.

## Dropped or added letters

- **`repertoire_1903-04_p010`, "4 Ворникъ."** — should be "Вторникъ"
  (Tuesday); the compositor dropped the т. Printed identically across
  all three theater columns on the row, so it's not a one-column slip —
  the whole row shares one printed date label.
- **`repertoire_1899-00_p037`, "9 Четвергъ."** — appears out of sequence
  between "3 Среда" and "5 Пятница"; the scan confirms the page really
  does print it there, misnumbered, not a transcription reordering.

## Wrong word / misheard-by-the-typesetter substitutions

- **`review_1901-02_SP_ballet_p027` (folio 193): "Пребраженская"** for
  "Преображенская" — the compositor dropped the о. What makes this one
  worth having is that **the same page prints the name both ways**:
  "О. Преображенская" correctly at full width near the top, then
  "О. Пребражен-ская" four lines down in the narrow column running beside
  the photograph. Same page, same dancer, same setting session.

  Caught in the pilot triage (2026-09-25): of three extraction passes, two
  transcribed the column instance as printed and one silently normalised it
  to the standard spelling. Scan-verified at 4x; RG confirmed. Kept verbatim
  in both places, per the verbatim rule.

  This is the same phenomenon as the surname variants in the Season Reviews
  gold set — Карлсонъ/Карльсонъ, Пршебылецкая/Пржебылецкая,
  Цалисонсъ/Цалисонъ, all within a page or two of each other — which is
  why the standing rule is never to assume spelling consistency and to
  verify every instance on its own.

- **German operetta program, `repertoire_1904-05` range: "Husarenlieber"**
  for "Husarenliebe" — an extra letter, print-original.
- **"Das aite Heim"** for "Das alte Heim" — a worn/broken "l" glyph in
  the actual printing block, confirmed by zoom; reads as "aite" on the
  page itself.
- **`repertoire_1900-01_p030`: "Denice"** for "Denise" — a genuine period
  spelling variant in the print, not a misread.

## Receipts-figure typos (rubles marker "р." misprinted)

A recurring class: the compositor printed the *kopecks* marker's letter
("к.", or a lookalike) where the *rubles* marker "р." belongs, sometimes
twice in the same figure. All confirmed by direct scan comparison —
these are why `quality_checks.py`'s `receipts_parse_failed` flag will
never go to zero, by design:

- `repertoire_1901-02_p026`: "1495 д. 25 к."
- `repertoire_1901-02_p011`: "263 д. 64 к."
- `repertoire_1902-03_p019`: "876 к. 18 к."
- `repertoire_1904-05_p009`: "736 к. 49 н."
- `repertoire_1905-06_p017`, `_p018`, `_p043`: same pattern
- `repertoire_1906-07_p021`: "1041 и. 53 к."
- `repertoire_1906-07_p023`: "701 г. 06 к."
- `repertoire_1906-07_p035`: "433 к. 45 к."
- `repertoire_1907-08_p000`: "1055 к. 04 к."
- `repertoire_1907-08_p024`: "1107 к. 62 к."
- `repertoire_1901-02` range: "7166 р. 87 г." (kopecks marker garbled
  this time, rubles marker fine)

## Misprinted day numbers (weekday word right, digit wrong)

The compositor's eye clearly tracked the weekday correctly but slipped on
the day number — confirmed because the printed sequence becomes
internally consistent again the moment you assume the digit is off by
one:

- **`repertoire_1904-05_p014`**: "28 Понед." printed directly after
  "28 Воскрес." with no "29" anywhere — should be "29 Понед."
- **`repertoire_1905-06_p027`**: "23 Вторн." printed directly after
  "23 Понед." with no "24" — should be "24 Вторн."
- **`repertoire_1905-06_p036`**: "16 Среда." printed before "16 Четв."
  with no "15" — should be "15 Среда."
- **`repertoire_1907-08_p036`**: header prints "9" where the table
  itself (cross-checked against the neighboring page) actually starts
  at day 6.
- **`repertoire_1904-05_p011`**: "23 Пятница." printed directly after
  "4 Четв." with no "5" anywhere — should be "5 Пятница."
- **`repertoire_1898-99_p017`**: "28 Среда." printed directly after
  "15 Вторн.", skipping days 16–27 entirely, as an isolated inserted
  row — the whole gap and its weekday label are exactly as printed.
- **`repertoire_1905-06_p027`/`p028`, a two-page cascade**: `p027`'s
  "23 Вторн." (see above) is really day 24; the compositor's day-count
  then stayed one behind truth for the rest of that page AND rolled
  onto the next page — `p028`'s whole 25 Янв.–3 Февр. run (10 rows,
  all 3 theaters) prints weekday words that are internally consistent
  with each other but one day ahead of the true Julian calendar
  throughout. Confirmed by computing true weekdays directly (Jan 24
  1906 = Tue, matching `p027`'s fix; Jan 25 = Wed, but `p028` prints
  "25 Четвергъ." = Thu) — not a fresh defect, the same dropped day
  rippling forward. `validate_performance_dates.py` catches this whole
  class automatically (a run of ≥2 consecutive pages/rows agreeing on
  one consistent day-shift) and corrects the derived calendar date
  without touching the verbatim `date_text`.

## Wrong weekday word entirely (date_undate correct, printed word isn't)

- **`repertoire_1891-92_pair004`**: "1 Вторн./2 Среда/3 Четверг." across
  all 5 theater columns — should read "1 Воскр./2 Понед./3 Вторникъ".
  The calendar date was already right; only the printed weekday word is
  wrong, in the original.
- **`repertoire_1894-95_pair008`**: "25 Суббота." — scan confirms the
  print, but 25 Jan 1895 was actually a Среда (Wednesday). Left as
  printed.
- **`repertoire_1893-94_pair004`**: "13 Среда." — re-zoomed to rule out
  a misread "15"; the digit is genuinely 13 in print, but 13 Sept 1893
  was a Monday, not Wednesday.
- **`repertoire_1892-93_pair024`**: "2 Вторн." — legible despite sitting
  right on the binding fold. The surrounding sequence (30 Пятн.=Fri,
  3 Понедѣльн.=Mon, 4 Вторникъ.=Tue…) is only internally consistent if
  May 2, 1893 was a Sunday, not a Tuesday — the compositor mislabeled
  it.
- **`repertoire_1905-06_p023`**: "1 Вторникъ" for New Year's Day — the
  surrounding sequence (28 Среда→29 Четвергъ→30 Пятница→31 Суббота)
  makes Jan 1 a Sunday, not the printed Tuesday.
- **`repertoire_1906-07_p041`**: "6 Понед." printed right after
  "5 Четвергъ." — should be "6 Пятница." per the sequence.
- **`repertoire_1901-02_p002`**: "16 Вокрес." for "Воскресенье" (Sunday)
  — a dropped с, confirmed genuinely printed that way.

## Material constraints of the printing process itself

Not typos — cases where the physical limits of the page or the press
run visibly shaped what got printed, independent of any single
character being wrong. The compositor's hand shows up here too, just
at the level of layout and page-planning rather than spelling.

- **`repertoire_1905-06_p005` (Новый театръ, "1 Суббота.") and
  `repertoire_1905-06_p008` (Маріинскій театръ, "23 Воскрес.")**: both
  rows print a lone "УТРО." (morning) label with no "ВЕЧЕРЪ." (evening)
  counterpart, and both happen to be the very last row on their page.
  Confirmed this isn't a missing-scan problem (clean blank margin below
  each row, with the folio number fully legible) — the row's own
  printed column-divider lines simply run down past the morning entry
  and stop, with no closing border and no second sub-cell ever drawn,
  unlike a real morning/evening split elsewhere on the same page (a
  taller box with a horizontal divider). The compositor ran out of
  vertical space on the physical page mid-row; whatever evening
  performance may have occurred was never typeset at all. No amount of
  re-scanning recovers this — the original bound volume itself doesn't
  contain it. First flagged 2026-09-24, reasoning corrected 2026-09-25
  after being asked to double-check the "blank margin" detail directly.

## A whole misprinted date-range header

- **`repertoire_1902-03_p008`**: the page's own printed date-range
  header literally reads "22 ноября. 1902 г. 3 октября." — November
  before October. The table's internal "Ноябрь" divider row proves the
  true order is Oct 22 – Nov 3. Header text kept exactly as printed;
  only the derived calendar field uses the corrected order.

## People: a patronymic misprinted the same way across multiple editions

- **Орchestra roster entry, 1903-04 & 1907-08 editions**: patronymic
  printed "Вавиловичъ" where nine other editions of the same person's
  entry print "Васильевичъ" — confirmed genuinely printed that way (not
  a misread) on both source PDFs directly, page and item number checked.
- **Симонова Марія Петровна / Сапожникова Анна Іосифовна / Анкудинова
  Ольга Евгеніевна**: each has one edition printing a birth/service year
  a decade off from every other edition of the same person's entry — a
  recurring one-edition defect across multiple, unrelated print runs,
  not a single bad batch.
- **Рахмановъ Сергѣй Павловичъ**: two separate editions (1905-06 and
  1907-08) both print his *brother* Викторъ's service-start year ("1903")
  onto his own line — the same error, independently repeated in two
  different print runs years apart.

---

*Started 2026-09-24. Harvested from `docs/eval/known_issues.md`'s
scan-verification history plus that day's single-page-season full sweep;
add new finds here as they turn up.*
