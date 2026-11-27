# Roster gold refresh, 2026-11-27

Goal: bring `docs/eval/gold/_build_roster.py` up to date so `eval_against_gold.py`
works as a regression check again. Before: roster 76.4% (949/1,242 fields) on
`outputs/full_run/parsed`. After: **97.3% (1,418/1,458)**. Repertoire unchanged at 97.8%.

All scan reads are by Claude, from `docs/eval/gold/images/` (checked by Claude, not RG).

## Rulings

- **Tenure notes (RG, option C):** the gold holds the whole printed note after the name,
  brackets included («(съ 1 сентября 1889 г.). Первая скрипка.»). The scorer compares
  tenure notes without brackets and stops (`norm_tenure`), and reports the run's count of
  notes with a closing bracket but no opening one separately (2,435 now).
- **Heading end punctuation (Claude, by the same reasoning, for RG to confirm):** the
  scorer compares heading segments without a printed end colon or stop (`norm_heading`).
  The stored rows keep them on BalletArtists and Musicians and not on TheaterSchoolStaff.

## What changed in the gold

- Conventions ruled after the gold was made: #137 office roots on Administrators headings,
  the school and ProductionTeam roots, `service_class` without the final stop.
- Gold transcription errors fixed (the print agrees with the data): «Владимиръ» (Теляковскій,
  Кусовъ 1907-08); Аршеневскій 1890-91 «1889», not «1839»; «Вильеръ - де-Лиль - Адамъ»
  printed with spaced hyphens in 1890-91; «И. д.» spacing; Журналистъ sits in the
  Распорядительное отдѣленіе (column break); Шенкъ's «Завѣдывающій центральною
  библіотекою.» is a note under his entry, not a heading; Алексѣева 2-я's printed
  «† 25 мая 1891 г.» added; tenure notes now carry the printed instrument (Musicians) and
  second lines.
- Partial pages completed: musicians_1890-91_SP now has all 37 entries (was 14);
  theaterschoolstaff_1906-07 gains Абрамова («И. д. фельдшерицы»).

## The 40 remaining mismatches are data errors (NOT fixed; for RG)

1. **Musicians 1890-91 SP:** «Капельмейстеръ военной музыки» (Оглоблинъ) and all 31
   «Музыканты» are printed under «Оперный оркестръ», but stored without it (Направникъ and
   Кучера have it). 32 fields. Not checked whether other seasons do the same.
2. **Administrators 1907-08:** «баронъ» (Кусовъ) and «графъ» (Бергъ) are missing from
   rank_or_title. The same two rows are also missing them in 1906-07; every other season has
   «баронъ, …» / «графъ, …» (the #137 convention).
3. **Administrators 1907-08:** the printed heading «Помощники дѣлопроизводителя:» is missing
   for Посниковъ and Шенкъ.
4. **Administrators 1890-91:** the printed heading «Полиціймейстеры:» is missing for
   Старженецкій-Лаппа and Клечковскій.
5. **TheaterSchoolStaff 1906-07:** Боборыкинъ has the stored note «съ 1 сентября 1903 г.»;
   nothing is printed after his name (that is Смирновъ's date).
6. **TheaterSchoolStaff 1906-07:** Абрамова is stored under «Лекарскій помощникъ /
   И. д. фельдшерицы»; the print sets «И. д. фельдшерицы.» as its own heading at the same
   level. Structure question rather than a clear error.

Also seen, not scored: 2,435 tenure notes have a closing bracket but no opening one.

## Uncertain in the gold

- administration_1907-08 Шарыпинъ: the only printed heading is «VIII кл.», after the
  «Помощники дѣлопроизводителя» entries; the gold puts him under «Распорядительное
  отдѣленіе» with no position, like the stored row.
- The musicians entries 12-31 were read on the scan after the stored rows had been seen.
