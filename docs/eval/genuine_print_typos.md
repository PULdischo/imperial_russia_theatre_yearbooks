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
- **`repertoire_1890-91_pair008` (p. 9, 24 Октября 1890, Малый):
  "Севильскій обольстатель, др."** — should be "обольститель"; а set
  for и. Confirmed at full resolution on RG's 2026-09-28 photograph of
  the previously-missing pp. 8-9 (issue #97) — the letter is clearly an
  а, not a worn и. The same play is printed correctly as "Севильскій
  обольститель" on two later 1890-91 pages (`pair010`, `pair014`), so it
  is one slip on this page, not the volume's spelling of the title.

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
- **`repertoire_1900-01_p025`, "30 Вторникъ." Малый: "Шутники, вартина."**
  for "картина" (tableau) — а В/К swap, found 2026-09-28 while checking
  the genre-candidate review queue (known_issues.md issue #99). Zoomed
  directly on the cell: reads cleanly "вартина," no smudging or damage,
  matching the raw extraction exactly — a genuine period typesetting
  slip, not an OCR/extraction misread.

## Receipts-figure typos (rubles marker "р." misprinted)

A recurring class: the compositor printed the *kopecks* marker's letter
("к.", or a lookalike) where the *rubles* marker "р." belongs, sometimes
twice in the same figure. All confirmed by direct scan comparison —
these are why `quality_checks.py`'s `receipts_parse_failed` flag will
never go to zero, by design:

- `repertoire_1901-02_p026`: "1495 д. 25 к."
- `repertoire_1901-02_p011`: "263 д. 64 к."
- `repertoire_1902-03_p019`: "876 к. 18 к."
- `repertoire_1904-05_p009`: "736 к. 49 к." (kopeck marker re-read on the scan 2026-09-29; earlier transcribed "н.", but the print has к.)
- `repertoire_1905-06_p017`, `_p018`, `_p043`: same pattern
- `repertoire_1906-07_p021`: "1041 и. 53 к."
- `repertoire_1906-07_p023`: "701 г. 06 к."
- `repertoire_1906-07_p035`: "433 к. 45 к."
- `repertoire_1907-08_p000`: "1055 к. 04 к."
- `repertoire_1907-08_p024`: "1107 к. 62 к."
- `repertoire_1909-10_p050`, 21 Среда., Малый театръ: "1425 к. 60 к."
  (zoom-confirmed 2026-09-30 against `repertoire_1909-10_p050.png`,
  same corpus-wide pattern — rubles marker printed as "к." instead of
  "р."; `receipts_text` kept verbatim)
- `repertoire_1901-02` range: "7166 р. 87 г." (kopecks marker garbled
  this time, rubles marker fine)
- **Named 2026-09-29 (scan-checked, issue #109):** `1905-06_p017` 4 Воскрес. Новый утро "323 к. 37 к.";
  `1905-06_p018` 8 Четвергъ Александринскій "1667 г. 46 к." (г., not к.); `1905-06_p043` 16 Воскрес. Новый утро "79 к. 02 к.".
  Kopecks marker misprinted: "292 р. 04 р.", "297 р. 87 р.", "478 р. 86 р.", "912 р. 02 г." (1901-02);
  "1483 р. 49 р.", "1939 р. 33 г.", "270 р. 25 г.", "1413 р. 58 р.", "703 р. 99 р." (1902-03); "856 р. 11 р." (1903-04);
  "720 р. 97 р.", "586 р. 82 л." (1905-06); "190 р. 98 р." (1906-07); "1497 р. 75 р." (1907-08).
  Punctuation: "276 р, 98 к.", "1062 р. 71 к;", "800 р, 06 к." (1899-00); "1155 р, 72½ к.", "994 р- 75 к." (1900-01);
  "1958 р, 57 к." (1901-02); "1421 р, 46 к.", "1556 р- 42 к." (1902-03); "557 р: 75 к:", "1132 р, 91 к." (1904-05);
  "552 р, 74 к.", "403 р, 01 к." (1905-06). Other: "19 22 р. 34 к." (space printed, 1902-03 p018);
  "13.472 р. 22 к." (thousands separator, 1906-07 p027); ".575 р. 40 к." (1907-08 p017, meaning unclear);
  "1553 р," (1895-96 pair008, no kopecks printed).
- **`repertoire_1892-93_pair012`, 8 Вторн., Михайловскій: "1225 q. 27
  к."** — a different case from the rest of this list. The others above
  are the compositor reaching for the *kopecks* marker glyph on the
  rubles side; this one is a Latin "q", which doesn't visually resemble
  "р." at all in this typeface. Confirmed directly against the scan
  (RG, 2026-09-25) that the glyph genuinely is a "q" — read as the
  rubles marker from context (its position in the figure, matching
  every other session's "<rubles> р. <kopecks> к." shape corpus-wide),
  not from any visual similarity. `receipts_text` stays exactly as
  printed, and (RG's call) so does the rest of this section's
  treatment: left unparsed at the raw/analysis layer, same as every
  other entry here (`receipts_rubles`/`receipts_kopecks` empty, joins
  `receipts_parse_failed`) rather than special-cased into
  `_RUBLES_MARKER_RE`. A corrected numeric value for cases like this
  belongs in the `research` layer (derived via SQL only, never baked
  into raw-tier parsing) — not yet built; when it is, this is the case
  that motivated it.

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

## 1909-10 volume (Repertoire, added 2026-09-30, issue #119)

Found during the new season's full scan-verification sweep (6 parallel
agents, 56 pages). Only confirmed-genuine items are listed here; the
sweep's raw JSON fixes for actual extraction errors are documented in
known_issues.md issue #119, not here.

- **Receipts, rubles marker misprinted**: `p016` Большой 8 Воскрес.
  evening "2466 **о.** 88 к." (coordinating-session re-check † against
  `repertoire_1909-10_p016.png` -- confirmed, same corpus-wide class as
  the `p050` entry already in the Receipts-figure typos section above).
- **Receipts, missing/stray period**: `p032` "3049 р 78 к." (no period
  after "р"); `p034` "1388 р- 90 к." (hyphen for period); `p037`
  "734 р· 30 к." (mid-dot for period).
- **Receipts, wrong unit letter**: `p036` "727 р. 70 **р.**" (kopecks
  marker printed as рубли); `p037` and `p039` both print "2841 р. 60
  **р.**" for the same Михайловскій benefit-receipts line -- same slip
  twice, possibly this compositor's habit.
- **Genuine period-typo in running text**: `p019` "**моледежи**" for
  "молодежи" (Спектакль для учащейся молодежи) -- extraction had
  silently "corrected" this to the expected spelling; restored verbatim.
- **Genuine letter substitution**: `p007` "Тихая пристань, **цьеса**."
  for "пьеса" (ц/п confusion, confirmed at zoom).
- **Genuine letter substitution, title**: `p047`, 8 Четвергъ, Маріинскій:
  "**Шоиеніана**" for "Шопеніана" (и/п confusion; RG read the scan
  letterform directly). Fokine's ballet *Chopiniana*, Mariinsky,
  premiered 1907 -- no ballet named "Шоиеніана" exists. Kept verbatim in
  raw; corrected to "Шопеніана" in the research layer only via
  `build_research_model.RESEARCH_TITLE_CORRECTIONS` (RG, 2026-09-30).
- **Printing ghost / genuine leading hyphen**: `p006` "**-**Евгеній
  Онѣгинъ, оп." -- a stray leading hyphen genuinely printed before the
  title, not an extraction artifact.
- **Genre abbreviation, no closing period**: `p040` "Спящая красавица,
  **бал**" (scan shows no period where one is used everywhere else for
  this genre).
- **Name/spelling variance across consecutive days, not an error**:
  `p023` "**La** paradis" vs "**Le** paradis" (French article gender
  slip, printed differently on two consecutive dates for what appears
  to be the same production).
- **Genuine capitalization typo**: `p027` "**Eamily**-hôtel" (capital E
  for F, confirmed at zoom, appears twice).

## 1908-09 volume (Repertoire, added 2026-09-26, issue #93)

Found during the new season's full scan-verification sweep. Items marked
† were re-checked directly against the scan by the coordinating session,
not only by the sweep agent; the rest were zoom-verified by the agent.

- **`p022`, date column** †: "4 Четвергъ." followed by "4 Пятница." --
  Friday 5 December 1908 printed as "4". Contents not shifted.
- **Receipts, rubles marker for kopecks**: "3049 р. 78 р." (`p004`
  Большой 8 Сентября), "366 р. 54 р." and "777 р. 33 р." (`p024` Малый).
- **Receipts, comma after р.**: "2650 р, 28 к." (`p023`), "2286 р, 28 к."
  (`p025`), "2686 р, 15 к." (`p045`) -- all Маріинскій; also "3493 р. 40
  к," (`p007`).
- **Receipts, stray period after kopecks**: "937 р. 06. к." (`p013`) †,
  "1439 р. 37. к." (`p009`), "571 р. 45. к." (`p023`).
- **Receipts, missing unit**: "3977 р. 50" (`p010` Большой, no "к.").
- **Uninked digit** (physical check needed): `p009` Александринскій
  11 Сентября, "15?2 р. 34 к." -- third digit didn't print.
- **French titles (Михайловскій)**: "La course du flambean", "L'ami de la
  maisou", "La chrysaeide", "Le demi-moude", "La famme de César" / "La
  femme dé César", "Vingt. jours à l'ombre".
- **French genres at the column rule without final period** †: "vaud"
  (`p013`), "vaud. nouv" (`p017`); also "vaud nouv." (`p005`), "com,
  nouv." (`p029`).
- **Russian**: "Донъ Кихотъ Ломанчскій" (`p024`); "Черевички, эп,"
  (`p035`, "эп," where "оп." expected); "Карменъ, др." (`p006`);
  "Женитьба, оп." (`p044`); "Сполохи, ком." (`p013`, elsewhere "пьеса");
  "Дивертиссментъ" (dropped е, several pages); banner "...учебныхъ
  аведеній." (`p033`, з missing).
- **Printing ghost**: rotated session label "ВВЧЕРЪ." for "ВЕЧЕРЪ."
  (`p001`, 7 Сентября; label text isn't stored as data).
- **Lone УТРО. cell** †: `p027` Маріинскій 3 Января 1909 -- labelled "УТРО."
  (Пиковая дама, 2201 р. 28 к.) but no ВЕЧЕРЪ sub-cell was ever drawn.
- **Duplicated figures, possibly typesetter repeats**: `p047`
  Александринскій 12 Апрѣля morning and evening both "1491 р. 07 к.";
  `p052` Малый 26 and 28 Апрѣля both "1467 р. 02 к.".

---

*Started 2026-09-24. Harvested from `docs/eval/known_issues.md`'s
scan-verification history plus that day's single-page-season full sweep;
add new finds here as they turn up.*

## Season production-stats pages: arithmetic that doesn't add up (added 2026-09-30)

Found while transcribing the season totals pages ("Всего въ теченіе сезона … было
спектаклей") into `docs/season_stats/`. Both were checked at high magnification;
every other subtotal on these pages adds up.

- **1896-97 (p. 27), Petersburg "Балетныхъ":** the lines print 50 (Маріинскій)
  and 3 (Михайловскій), but the subtotal prints **52**, not 53. The receipts
  subtotal (118,760 р. 24 к) does equal its two lines. Which figure is off (50, 3
  or 52) is still open; the Repertoire itself can arbitrate.
- **1906-07 (page number unreadable), Petersburg "Русскихъ драматическихъ":** the
  receipts lines print 247,576 р. 17 к. + 10,353 р. 15 к. + 7,262 р. 50 к. =
  265,191 р. 82 к., but the subtotal prints **265,272 р. 82 к.**, exactly 81 р.
  more. The counts (197 + 25 + 1 = 223) add up.
- **1900-01 (p. 40), Moscow "Русскихъ оперныхъ":** the lines print 337,935 р. 17 к.
  + 33,944 р. 03 к. = 371,879 р. 20 к., but the subtotal prints **371,878 р. 20 к.**,
  exactly 1 р. less. All three figures were checked magnified.

### Other slips on the same pages (kept verbatim in `docs/season_stats/`)

- 1893-94 (p. 26), Moscow drama at the Большой: "24,517 р. 92 **л.**", with "л." for "к.".
- 1897-98 (p. 27): "Спектаклей труппы **Берлинскго** Лессингъ-театра" (а dropped).
  In footnote 2, "**соорженія** памятника" (у dropped); in footnote 11, "**вп** пользу" for "въ".
- 1904-05 (p. 134), SP drama subtotal: the "р." has lost its descender and looks like "ь".
  That is damaged type, not a wrong letter, and is transcribed as "р".

## Genre abbreviation misprinted (added 2026-09-30)

- **`repertoire_1908-09_p035` (6 Feb 1909, Маріинскій, вечеръ): "Черевички, эп,"**. The genre should be "оп." (Tchaikovsky's
  opera), but "э" is set for "о" and a comma for the full stop. Checked at 600 dpi; the transcription matches the print.
  Found through the season-stats comparison, where the misprinted genre made the opera count as drama.

## BalletArtists credit totals that don't sum (Roster, added 2026-10-01, issue #123)

Found scan-verifying the `credit_sum_mismatch` flags on the newly-onboarded 1908-10 Roster batch. In each case both the
per-category counts and the printed "Всего" total were checked directly against the scan at full resolution and are
unambiguous -- the components genuinely don't sum to the stated total in the original print, not a transcription error.

- **`balletartists_1908-09_SP_p006`, Матятинъ А.А.**: "Времена года (сатиръ—3). Всего—въ 1 балетѣ—2 раза." Both digits
  (3 and 2) are crisp; 3≠2.
- **`balletartists_1909-10_MSK_p006`, Козловъ 2-й А.М.**: "Въ 13 балетахъ—43; въ 5 операхъ—34. Всего—83 раза." 43+34=77≠83.
- **`balletartists_1909-10_MSK_p007`, Никитинъ 1-й В.Д.**: "Въ 10 балетахъ—37; въ 5 операхъ—40. Всего—67 раза." 37+40=77≠67.

## Stray dagger (†) with no date (Musicians, added 2026-10-02, issue #130)

- **`musicians_1906-07_SP_p006`, Новоселовъ А.И. (Старшій библіотекарь Центральной Музыкальной Библіотеки)**: the entry "(съ 1 августа 1882 г.)." is
  followed on its own line by a lone **"†"** with no date. He is still listed alive in 1907-08, where the note reads "† 5 мая 1908 г." -- so the
  1906-07 dagger is not a death notice for that season. RG's reading: the 1906-07 volume may have been in production after his death (1908), which would
  explain a dagger being set in it. The scan does not settle it either way. Transcribed verbatim: "†" stays in `tenure_note_text`, but the row carries no
  `end_type` (previously "died" with no date, now empty), so it no longer contradicts the 1907-08 record.

## Musicians notes audit, 2026-10-02 (issue #130, batch 7) -- probable genuine print oddities

All read at zoom by an audit agent; those marked * I also saw on the scan myself. Stored verbatim unless noted.
- `musicians_1895-96_MSK_p003` Колосовъ: tenure "(съ 1 **декабри** 1894 г.)" (я -> и). Stored as "декабря" (normalized) -- left.
- `musicians_1898-99_SP_p004` Ѳедоровъ Петръ and `musicians_1904-05_SP_p005` Подгорбунскій: "Оставилъ службу **:** сентября/февраля" -- the day digit is a colon-like damaged glyph.
- `musicians_1909-10_MSK_p002` Петрушевъ: "18 **сентябрб** 1903 г." (б for я); stored normalized to "сентября".
- `musicians_1906-07_SP_p003` Степановъ*: "съ 31 марта **1802** г." (presumably 1892); his 1905-06 entry is blotted but reads "31 ма?та 1892".
- `musicians_1906-07_SP_p004` Алексѣевъ: "Вторая **скричка**"; `musicians_1909-10_SP_p000` Лачиновъ: "Первая **срипка**"; `musicians_1909-10_SP_p003` Помазанскій: "**Аленсандровичъ**".
- `musicians_1903-04_MSK_p001` Зайцевъ: "Оставилъ службу 1 сентября **1905** г." in the 1903-04 volume (print anomaly).
- `musicians_1899-00_SP_p005` Федоровъ: leave date "1 іюня 1889" precedes his start "1 сентября 1889".
- `musicians_1903-04_MSK_p001` Зюсъ: death year printed "190з" (з-shaped 3), stored 1903. `musicians_1903-04_SP_p000` Гордонъ: print reads "Горлонъ"? (d/l ambiguity, unverified).
- `musicians_1907-08_SP_p003` Хейкель: stray comma "Хейк,елъ". `musicians_1904-05_SP_p005`: a stray lone "(" under Лачиновъ. `musicians_1905-06_MSK_p005` Орловъ*: the "і" of "іюня" is printed undotted (worn type); transcribed as "іюня".
- `musicians_1902-03_SP_p006` Напихъ: list number "18." for 28 (already known); `musicians_1906-07_MSK_p004` Стрекаловъ: printed number "7." duplicates Славинскій's; `musicians_1899-00_MSK_p002` Павловъ: contract span printed "по 30 декабря 1880 и (съ 19 сентября 1882 г.)" (no "г.", doubled paren).

## Musicians name/instrument audit, 2026-10-02 (issue #130 batch 9) -- print oddities confirmed by two independent zoom readings

Each was read at zoom by the first-pass agent AND by a blind second reader; stored VERBATIM in the raw JSON (RG's rule), so the research layer is where any
correction belongs. Entry ids are `<page_id>__eNNN`.
- **Людольфи / Лудольфи** (final и, not ъ), printed in every season where this double-bass player appears: 1898-99 SP p002 e025, 1899-00 SP p002 e012,
  1900-01 SP p002 e026, 1901-02 SP p002 e019, 1904-05 SP p002 e015, 1906-07 SP p002 e005, 1907-08 SP p002 e005, 1908-09 SP p002 e023, 1909-10 SP p002 e029.
  Nine consecutive-ish volumes: probably the printer's own form of the name rather than a one-off slip.
- `musicians_1907-08_SP_p000` e019 **Бѳльмъ** (barred ѳ where о is meant; same man is Больмъ elsewhere). `musicians_1901-02_SP_p000` e003 **Крушевекій**.
- Patronymics: `musicians_1904-05_SP_p002` e006 **Фелоровичъ** (л for д; a second л-shaped case, `musicians_1904-05_SP_p004` e039, was too worn to call and is left as
  stored Федоровичъ); `musicians_1909-10_SP_p003` e012 **Аленсандровичъ** (к missing); `musicians_1898-99_MSK_p001` e023 **Васильеничъ** (н for в).
- First names: `musicians_1897-98_MSK_p001` e016 **Фрацъ** (Францъ). Surnames: `musicians_1899-00_SP_p005` e031 **Беттенштелтъ**; `musicians_1894-95_MSK_p002` e003
  **Порубинозскій** (з for в, 9x zoom); `musicians_1904-05_MSK_p000` e029 **Валеніўсъ** (у with a breve).
- Instruments: **Вольдгорнъ** (1904-05 MSK p001 e010), **Флейга** (1904-05 SP p005 e001), **Флейтэ** (1905-06 MSK p004 e032), **Вторая скричка** (1906-07 SP p004 e001),
  **Кснтрабасъ** (1891-92 MSK p002 e004), **Первая срипка** (1909-10 SP p000 e008). Also `musicians_1897-98_MSK_p002` e050 **Тромбомъ** (stored as printed).
- Printed forms that were *not* stored (cosmetic): list numbers without the period after them (12 rows), "Хейк,ель" (1907-08 SP p003 e009), "Пекарскій I," with a Roman
  numeral (1906-07 MSK p002 e030; stored "Пекарскій 1"), "Карлъ·Вильгельмъ" with a middle dot (1892-93 MSK p000 e015), "Фридрихъ -Эрнестъ"/"Карлъ - Вильямъ" hyphen spacing,
  the misprinted list number "34." for 54 (1895-96 MSK p001 e032). Damaged-glyph cases resolved by corroboration (not typos): see known_issues #130 batch 9.
- `musicians_1901-02_SP_p000` e014 Ауэръ: first name printed **Лоопольдъ** (Леопольдъ everywhere else); stored as printed (seen on the scan, 2026-10-02).
- `musicians_1898-99_SP_p006` section heading "Старшій библіотекарь Центральной Музыкальной **Бблiотеки**." (first и dropped; seen at 4x zoom 2026-10-02); `musicians_1905-06_MSK_p001` heading "**И. сб.** 2-го капельмейстера балета" (сб. for об.). Both stored as printed.

## ProductionTeam audit, 2026-10-02 (issue #132) -- print oddities stored as printed
- `productionteam_1905-06_p001` e018 Павловъ: patronymic **Павлсвичъ** (с for о); `productionteam_1891-92_p002` e003 Яруцкій: leaving note **"Остваилъ службу 1 сентября 1892 г."**
- Surname variants consistently printed: **Семирадзкій / Семирадзскій** (1899-00 p001, 1907-08 p001, 1909-10 p000), **Науіокайтисъ** (1903-1908), **Фонъ-Фитингофъ-Шеель** (1904-05, 1909-10).
- Tenure text: `productionteam_1903-04_p001` e022 "къ къ С.-**Нетербургскимъ**" (stored normalised); `productionteam_1904-05_p002` e006 "г.,.)"; `productionteam_1908-09_p002` e006 doubled "(съ (съ"; `productionteam_1909-10_p001` e007 "(**сь** 25 октября"; `productionteam_1909-10_p002` e001 "Мужскіе па-" (cut at the column end, continuation not printed).
- Headings printed with slips: "Мѣстные **гадеробы**." (1890-91 p002), "Гардеробм**ё**йстеры" (1893-94 p003), "**Костюмерта**" (1895-96 p003), "**Руская** драматическая труппа." (1895-96 p001), "Маріинскій **тэатръ**" (1896-97 p001), "Отдѣлъ **бугафорскій**" (1897-98 p003), "Парикмахеръ"-initial decoration (1909-10 p004 "Л/П").
- `productionteam_1892-93_p000` list title: "СПИСОКЪ личнаго состава служащихъ по монтировочной **части,**" -- ends in what looks like a comma rather than the period of the other 19 seasons (checked on the scan 2026-10-02, medium confidence); stored with the period.

- `productionteam_1903-04_p001` e019 **Каменскій** Исаакъ Осиповичъ (the costumer printed Неменскій in 1890-1903 and 1904-06; same start date 30 іюня 1881); read at 4x zoom 2026-10-03, stored as printed.
- List numbering skips printed by the source (nothing missing): `productionteam_1896-97_p000` Помощники декораторовъ 6 -> 8; `productionteam_1900-01_p000` Помощники декораторовъ 12 -> 14.
- Start-date printer slips (stored as printed, 2026-10-03 audit): `productionteam_1908-09_p002` e002 Ефимовъ "съ 1 сентября **1899**" (1889 in 18 other volumes); `productionteam_1908-09_p001` e002 Лебедевъ "съ 1 іюня **1899**" (3 іюня 1889 in 1907-08 and 1909-10); `productionteam_1908-09_p000` e004 Зандинъ "съ 1 мая **1887**" (1 мая 1907 in the other three volumes);
  `productionteam_1905-06_p003`..`1907-08_p003` e003/e003/e003 Гуняшевъ "съ 3 октября **1861**" (the date printed for Вальцъ just above him; his own is 1 октября 1897); `productionteam_1890-91_p003` e013 **Кунъ 2-й, Альбертъ Францевичъ** (the assistant is Карловичъ in 1891-93).
- `productionteam_1908-09_p001` e006 **Бардюкъ** vs `productionteam_1909-10_p001` e006 **Бордюгъ** (same man, Николай Кирилловичъ); `productionteam_1898-99_p002` e002 stray period "(съ 19**.** мая 1869 г.)".
