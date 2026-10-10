# Jubilees and obituaries in the Yearbooks

Every jubilee notice and obituary in the scanned jubilee/obituary sections of the
*Ежегодникъ Императорскихъ театровъ* (Yearbook Scans - Originals), 1890-91 to 1910-11,
with the ballet-relevant ones pulled out.

## Files

| File | What it is |
|---|---|
| `catalogue.csv` | Every entry on the 273 scanned pages: 347 person entries (obituaries, jubilees, memorial features) plus 27 section-heading and other-article rows. |
| `ballet_entries.csv` | The subset with `relevance` = `core` or `mentions`. |
| `first_read/` | The per-section first readings (A–H), the Season Review notices (`R_reviews.csv`), the contents-page listings (`T1`, `T2`) and the reader briefs. |
| `blind_second_read/` | An independent second reading of every heading name and date (V1–V5). |
| `build/` | `compare_readings.py` (first vs second read → `reading_comparison.csv`) and `build_catalogue.py` (writes the two CSVs above). |

## Relevance tiers

- `core` — a career in ballet: dancers, ballet masters, régisseurs, teachers, ballet composers and
  conductors, ballet-orchestra players. By RG's ruling (2026-10-10) also: designers and machinists,
  administrators over the ballet, the ballet critic Плещеевъ, players in the combined
  opera-and-ballet orchestras, and drama actors who began in ballet.
- `mentions` — not a ballet person, but the text says something about ballet (see `evidence_verbatim`).
- `none` — no ballet content.

`tier_basis` says whether the tier is the reader's call or RG's ruling.

## How it was checked

Each section was read entry by entry from page images (the PDFs' text layers are unusable).
A second reader, blind to the first, then re-read every heading name and date.
Of 338 headings paired between the two readings, 320 matched exactly; the rest differed only in
how much of the heading was copied (bracketed aliases, titles for names), except three names, settled on the scan in favour of the
second read: Борншейнъ, Платонова Юлія Ѳедоровна, Пфейферъ Ѳедоръ. No death or jubilee date
disagreed across the 316 entries where both readings give one.

Not second-read: roles, evidence quotes, and the `none` verdicts themselves.

## Not yet done

- The Season Review notices (`first_read/R_reviews.csv`) are not merged in; 25 death-list names
  there have no job stated and need matching to the obituaries and rosters.
- Unscanned items found in the contents pages (`T1`, `T2`) are not yet turned into a scan list.
- Coverage is limited to what was scanned: e.g. 1894-95 jubilee pp. 333-367 and
  1907-08 obituary pp. 287-291 are not in the scans.
