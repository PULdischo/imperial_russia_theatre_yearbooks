# Structural variation survey

Sampled pages across early (1890-91), middle (1898-1902), and late (1907-08) seasons
in each of the five populated folders, plus SP/Moscow variants where applicable.
Goal: catch format drift that would break a schema designed only from page 1 of the
first year. Source images are in the session scratchpad (`survey/` subfolder) and are
not part of this repo.

## RepertoireTables — the big one

**The table's shape changes mid-series, not just its content.** This is the most
important finding for schema design.

- **1890-91 through 1897-98**: one combined table per page. Two header bands —
  "С.-Петербургскіе театры" (3 columns: Маріинскій, Александринскій, Михайловскій)
  and "Московскіе театры" (2 columns: Большой, Малый) — sit side by side, plus a
  shared "Мѣсяцъ, день и число" date column and (in most years) a receipts figure
  under each title. 1890-91 file: 13 pages for the season.
- **1898-99 onward**: the combined table is gone. Each PDF instead alternates in
  *blocks* between a St. Petersburg-only table (3 columns, same as above) and a
  Moscow-only table — and Moscow gained a third venue, "Новый театръ" (New
  Theater), alongside Большой and Малый. A block covers a date range, then the
  file switches to the other city's block for a similar range, then back. This
  roughly triples the page count for an equivalent season (1898-99: 40 pages vs.
  1897-98's 13) because the two cities are no longer side-by-side.
- **Matinee/evening splits**: from 1898-99 on, a single calendar date can carry
  two sub-rows marked "УТРО" (morning) / "ВЕЧЕР" (evening) when a theater ran a
  matinee and an evening show the same day. Not seen in the 1890-91 sample.
  Occurs in both SP and Moscow blocks.
- **Language**: Mikhailovsky Theater (the French Imperial troupe's house)
  regularly carries French-language titles ("Célimare le bien-aimé, com.-vaud.").
  Everything else is Russian pre-reform orthography.
- **Annotations**: benefit-performance and anniversary notes appear inline in a
  cell instead of (or alongside) a title — e.g. "Въ пользу пострадавшихъ отъ
  недорода хлѣбовъ" (benefit for famine relief), "25-ти лѣтіе постановки" (25th
  anniversary of the production). These aren't a fixed enum; treat as free text.
- **Blank cells**: a theater dark that day/session is a plain dash — encode as
  "no performance," not a missing value.

**Design implication**: don't model this as a fixed-width grid (one column per
theater). Model it as one row per (date, session marker, theater, work) —
long/tidy — with theater name as a *value*, not a column. The theater roster
per date range (which cities, which venues, 2 vs. 3 Moscow houses) becomes
data, not schema, and survives every reshuffle above without a migration.

## Spiski_Administration

- Rank/service-class annotations ("VII кл.", "V кл.", "VI кл." — Table of Ranks
  class number) attached to position headers appear by 1907; not present in the
  1890-91 sample. Treat as an optional field on the position, not the person.
- Director's title phrasing shifts ("Директоръ Императорскихъ театровъ" vs.
  "Господинъ въ должности директора Императорскихъ театровъ" — i.e., *acting as*
  director) — a nuance worth preserving verbatim rather than normalizing to one
  canonical title string.
- "Оставилъ службу [date]" (left service) becomes a more frequent inline
  annotation by 1907. Same field as the death marker (†), different verb —
  model both as a single "service end" field with a type (death vs. resignation
  vs. other) plus date, since both close out a tenure the same way.

## Spiski_BalletArtists / Spiski_Musicians

- Moscow rosters are consistently smaller and structurally simpler than St.
  Petersburg's (fewer sub-role categories) across the whole period — this is a
  real difference between the two companies, not a data-quality issue.
- Role/position granularity **increases** over the 18 years: 1890-91 SP ballet
  lists only Балетмейстеръ + Режиссеръ before the artist roster; by 1907 it adds
  Репетиторъ балета, multiple Помощники режиссера, a "Главный репетиторъ
  классическихъ танцевъ," a "Руководитель класса характерныхъ танцевъ," etc.
  Schema needs an open-ended "position/role" field, not an enum of known roles.
- Honorific titles appear attached to top performers by the later years —
  "Солистъ Его Императорскаго Величества" (ballet), "Солистъ Двора Его
  Императорскаго Величества" (orchestra) — free-text, not universal, attach to
  the person/tenure record.
- Performance tallies ("Въ 11 балетахъ — 33; въ 8 операхъ — 43. Всего — 76
  разъ") are consistent in shape throughout, sometimes followed by an
  italicized named-role breakdown ("Въ томъ числѣ: Спящая красавица
  (красавица) — 5"). This breakdown is optional and variable-length — model as
  a separate child table (person × role × count), not columns.
- Musicians: instrument is a per-person free-text field ("Первая скрипка,"
  "Ударные инструменты"), present from 1890-91 onward. By later years the
  orchestra section itself splits into "Оркестръ оперы и балета" with separate
  opera/ballet kapellmeisters where 1890-91 had one combined "Оперный
  оркестръ" heading — another instance of growing organizational granularity.

## Spiski_ProductionTeam / Spiski_TheaterSchoolStaff

- Structurally stable across the period — same nested department → role →
  person shape throughout, just deeper nesting and more staff by 1907
  (consistent with the granularity trend above). No format break comparable to
  the Repertoire split.

## Net effect on schema design

1. Every Spiski type needs a **position/role field as free text with implied
   hierarchy** (institution → department → sub-department → role), not a fixed
   set of columns — the hierarchy itself grows over time.
2. **Service span** (start date, end type [active/left service/died], end date) is
   a shared shape across every Spiski type.
3. **Performance credit breakdowns** (ballet/opera/drama counts, named-role
   detail) belong in a child table keyed to the person + season, not inlined
   as wide columns — the number of named roles per person is unbounded.
4. RepertoireTables must be long/tidy (date × session × theater × work), never
   a fixed theater-per-column grid — the actual theater roster changed twice
   in the 18-year run we're digitizing.
