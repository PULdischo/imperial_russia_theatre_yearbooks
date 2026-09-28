# Ballet productions lists vs. the Repertoire tables — first audit pass

Issue #101. `pipeline/compare_productions_repertoire.py` (read-only)
against `outputs/full_run/imperial_theaters.duckdb`, 2026-09-28. Full row
detail in `outputs/ballet_productions_pilot/compare/`
(`list_dates_vs_repertoire.csv`, `repertoire_not_in_lists.csv`).

The two sources are independent transcriptions of different parts of the
same yearbook. A disagreement is a **lead to check on the scans**, not a
verdict, and nothing has been changed in either source.

## Headline numbers (1881 printed list dates, 30 lists, 1890-91 – 1904-05)

| Category | Dates | Meaning |
|---|---|---|
| exact | 1577 | same city, date and work |
| excerpt | 134 | matched through an excerpt row ("2-е д. бал. Фіаметта") |
| fuzzy | 77 | same date, near-identical title: a likely misread in one source |
| nearby_date | 23 | same work within ±3 days |
| other_titles | 23 | Repertoire has that city/date, but not this work |
| no_event | 46 | **Repertoire has no row at all** for that city/date |
| impossible_date | 1 | "декабря 38" (1897-98 SP Дочь микадо) |

That's 1711 of 1881 (91%) matched outright, 1788 (95%) counting the near-identical titles.

## Finding 1 — whole date blocks missing from the Repertoire (biggest)

All 46 `no_event` dates fall in gaps where the Repertoire has **no event
rows in either city**. The lists show ballets were given on those dates, so
the theaters were open. These are not closures; the week(s) appear to be
missing from the Repertoire transcription. The gaps have identical
boundaries in SP and Moscow, which points at whole blocks of the
Repertoire tables, not single cells. The existing `not_captured` synthesis
never flagged them (it only fills gaps inside a sequence):

| Season | Repertoire jumps from → to | List dates inside |
|---|---|---|
| 1892-93 | 1892-09-01 → 09-10 | 6 (both cities) |
| 1894-95 | 1895-04-21 → 04-28 | 2 |
| 1895-96 | 1896-01-17 → 01-24; 03-27 → 03-30; 04-11 → 04-19 | 5 |
| 1896-97 | 1896-12-31 → 1897-01-09; 01-21 → 01-29; 02-09 → 02-18; 04-24 → 05-04 | 17 |
| 1897-98 | 1897-10-16 → 10-24; 11-05 → 11-13; 1898-02-08 → 02-14 | 11 |

Several `nearby_date` rows sit right at these gap edges (e.g. 1897-98
Moscow Звѣзды 11, 12, 13 Feb all pointing at 14 Feb), so they're likely
the same problem: dates squeezed or shifted around a missing block.

**Next:** open the Repertoire renders for these weeks and check whether
the content is on the page but untranscribed (like issues #73/#85/#87),
or whether pages are missing.

## Finding 2 — Repertoire title misreads (fuzzy + other_titles + reverse direction)

Same error types the lists had: ь for ъ (Корсарь ×25, Кандавль, куколь,
Ненюфарь), н for и (Данта ×9 for Даита), and one-letter slips (Бандерка
and Вандерка for Баядерка, Паяда, Кальнабрино, Пригалъ, Ациснъ, Ukrainian
є in Грацієла, "Сиящая красавица", "Нарыбакъ" for Наяда и рыбакъ,
"Очарованный принцъ" for Очарованный лѣсъ?, "Рустикальный" for
Хрустальный башмачекъ). Also one excerpt row that has lost its title:
"1-я и 2-я карт. 3-го д. бал." (1893-94 SP, 1893-11-28).
**Per RG's spelling rule, every one is a scan check, never a blanket
replace** — some variants (Волшебные грезы, Царь Кандавъ, Фіамметта,
Лебединное) may be genuinely printed that way in the Repertoire.

## Finding 3 — list print errors the Repertoire can speak to

- **Дочь микадо 1897-98 SP:** the list prints "ноября 9, 24, 16, 19;
  декабря 14, 38". The Repertoire has 14, 16, 19 Nov and 14, 29 Dec,
  which suggests "24" = 14 and "38" = 29. 9 Nov falls in a Repertoire gap
  (Finding 1).
- The four out-of-season list years (Пери "1897", Дочь Микадо 1899-00
  апрѣля, Коппелія "1903 ноября", Тщетная "1904 апрѣля"): the comparison
  finds Тщетная on 1903-04-28 (list "1904-04-27", nearby_date +1).
  Коппелія's 1902-11-06 and Пери's 1898-02-12 fall in gaps. Worth a
  targeted look.

## Not problems

Comedy-ballets (Батюшкина дочка, Мѣщанинъ во дворянствѣ, genre
"ком.-бал."), benefit evenings and divertissements are in the Repertoire
but not on the ballet lists. Expected: they belong to other lists.
