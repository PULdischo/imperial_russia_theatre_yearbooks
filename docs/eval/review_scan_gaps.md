# Missing pages in the Season Review scans, and who holds the volumes

Established 2026-10-12, after RG pointed out that the scans have missing
pages and I had filed the `missing_page` quality flags as "limits of the
source" without reading them. The check had caught every one of these.

## How each gap was tested

Does the prose flow across it? An unnumbered plate leaf leaves the sentence
intact; a missing page breaks it. (A trailing hyphen means the word *should*
continue, so the question is whether the next page completes it — a first
mechanical pass had that backwards.)

## Confirmed content gaps — 2

| review | missing printed pages | what is on them | volume | held by |
|---|---|---|---|---|
| **1900-01 SP Ballet** | **176–178** | the rest of the «Дочь фараона» *Grand pas des fleuves* cast — p022 stops mid-name on `Темза — г-жа Фо-` — and the opening of the «Камарго» synopsis: its heading, premiere details and the start of scene 1, since p023 picks up mid-sentence inside it | Main, vol. 11 | **ILL — UIllinois** |
| **1896-97 SP Ballet** | **249** | p018 stops mid-sentence on `Является «Любопытство» и начинаетъ`; p019 opens on `Animation, groupes et danses—г-жи Ленъяни…` | Main, vol. 7 | **ILL — UMich** |

## Checked and cleared — the 1890-91 case is NOT a gap

**1890-91 SP All**, folios 145 → 149, resolved 2026-10-12 against the scans
already held:

- `p027` is an **unnumbered double-page plate** (4954 px wide) — the
  «Шествіе волшебныхъ сказокъ» procession from Спящая красавица, signed
  Е. Пономаревъ. It occupies folios **146-147**.
- `p028` is a sideways plate («Мальчикъ-съ-пальчикъ» и его братья) and it
  **does print its folio, 148**, at the foot — our extraction recorded it as
  `no folio` only because the page is rotated 90°.

145, [146-147 spread], 148, 149: every folio accounted for. **No page is
missing and no re-request is needed for 1890-91.**

**Worth noting beyond this case:** folio capture fails on rotated plate
pages. That inflates the `no_folio` count (76) and could in principle mask a
real gap elsewhere, since a page recorded as unnumbered is treated as
accounting for a folio it may not hold.

## No content lost — 5

The prose runs straight across an unnumbered plate: 1892-93 SP Ballet
(`…за прежними исполнителями:` / `г. Кшесинскимъ 1-мъ`), 1893-94 SP Opera
(`…г-жа` / `Брайнина`), 1894-95 SP Opera (`…атаманомъ имъ` / `будетъ
Антонъ`), and two inside 1900-01 SP Ballet — 174→179 (clean sentence end,
then `Въ 3-й картинѣ`) and 179→182 (`…письмо, въ` / `которомъ`, across the
double-page engraving).

## Consequences

**All three affected volumes are ILL, none of them Princeton.** Re-checking
means a fresh request from **UIllinois** (1900-01) and **UMich** (1896-97,
1890-91) — not a walk to the shelf like the 1890-91 pages RG photographed
in September.

**Every Main volume's inventory scanning status reads `Complete!`**,
including these. At least two of them are not. Correcting
`Imperial Yearbook Inventory.xlsx` needs RG's per-change permission and has
not been done.

## Corpus-wide context

Folio arithmetic over all 47 reviews (page count against printed-folio span,
less the unnumbered pages) leaves **5 folios unaccounted**, in 1890-91 SP
All, 1892-93 SP Ballet, 1894-95 SP Opera and 1900-01 SP Ballet. The measure
is rough — several reviews come out *negative*, meaning more pages than the
folio span allows, because the same printed page is scanned into two PDFs
(the shared-page bleed) and because 1900-01 prints folio 174 twice. The
text-flow test above is the authoritative one.

## Seasons with no review in the corpus at all (2026-10-12)

Separate from the missing-leaf gaps above: four seasons have **no review
page whatsoever**.

```sql
SELECT season, count(*) FROM raw.review_page GROUP BY 1 ORDER BY 1;
```
20 seasons held, 1,074 pages. Absent: **1898-99, 1909-10, 1911-12,
1913-14.**

- **1898-99** — the inventory note on Main vol. 9 (ILL, NYPL) reads *"This
  issue is truncated (no prose, just …)"*, so there may be no review to
  scan.
- **1909-10, 1911-12, 1913-14** — genuine gaps in what has been scanned.

Thin seasons worth a look in the same pass, since the issue-era volumes
split the review across numbers: **1912-13** holds only 4 pages (SP Ballet
alone), **1908-09** 12, **1910-11** 34.

**RG, 2026-10-12: the 1912-13 translation waits until all remaining season
reviews are scanned (expected the week of 2026-10-19), so the billed
translation run happens once, over the whole set.** Do not propose it
piecemeal before then.
