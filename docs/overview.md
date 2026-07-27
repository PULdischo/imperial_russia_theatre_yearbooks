# Corpus overview

Snapshot as of 2026-07-27, computed from `pdfs/_inventory.csv`.

## Totals

| | |
|---|---|
| PDFs | 144 |
| Pages | 1,299 |
| Seasons covered | 1890-91 → 1907-08 (18 consecutive academic years, all five populated folders) |
| Entity types populated | 5 of 7 (Graduates and ProductionStats have no source PDFs yet) |

## By entity type

| Folder | Files | Pages | Seasons | Notes |
|---|---:|---:|---|---|
| RepertoireTables | 18 | 519 | 1890-91 – 1907-08 | one file per season; page count nearly quadruples mid-series (see below) |
| Spiski_Administration | 18 | 78 | 1890-91 – 1907-08 | one file per season |
| Spiski_BalletArtists | 36 | 334 | 1890-91 – 1907-08 | two files per season (SP + Moscow) |
| Spiski_Musicians | 36 | 197 | 1890-91 – 1907-08 | two files per season (SP + Moscow) |
| Spiski_ProductionTeam | 18 | 82 | 1890-91 – 1907-08 | one file per season |
| Spiski_TheaterSchoolStaff | 18 | 89 | 1890-91 – 1907-08 | one file per season |
| Spiski_Graduates | 0 | 0 | — | not yet sourced |
| Spiski_ProductionStats | 0 | 0 | — | not yet sourced |

Roster-type folders (Administration/BalletArtists/Musicians/ProductionTeam/
TheaterSchoolStaff) stay roughly flat in page count across the 18 years —
growing headcount was absorbed by denser typesetting, not more pages.
RepertoireTables did not:

| Season | Pages | | Season | Pages |
|---|---:|---|---|---:|
| 1890-91 | 13 | | 1899-00 | 38 |
| 1891-92 | 12 | | 1900-01 | 38 |
| 1892-93 | 12 | | 1901-02 | 38 |
| 1893-94 | 12 | | 1902-03 | 38 |
| 1894-95 | 9  | | 1903-04 | 38 |
| 1895-96 | 13 | | 1904-05 | 44 |
| 1896-97 | 13 | | 1905-06 | 48 |
| 1897-98 | 13 | | 1906-07 | 50 |
| 1898-99 | 40 | | 1907-08 | 50 |

The jump from 13 → 40 pages at the 1898-99 boundary is the SP/Moscow table
split documented in `structural_survey.md` — the combined side-by-side grid
becomes two alternating full-width tables, roughly tripling page count for an
equivalent season. Worth remembering when estimating processing time/cost per
season: **later RepertoireTables seasons cost ~4x the OCR calls of early
ones for the same nine-year span**, and BalletArtists/Musicians don't share
that growth curve at all.

## What's missing

- **Spiski_Graduates** and **Spiski_ProductionStats**: no PDFs yet. Structure
  unconfirmed for the latter — see `structural_survey.md` for the working
  hypothesis (graduation rosters and a season repertoire-summary table,
  respectively).
- Coverage stops at 1907-08. If the Ежегодник run continues past this in the
  source archive, that's a separate sourcing question, not a processing one.
