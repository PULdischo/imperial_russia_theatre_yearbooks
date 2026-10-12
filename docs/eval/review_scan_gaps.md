# Missing pages in the Season Review scans, and who holds the volumes

Established 2026-10-12, after RG pointed out that the scans have missing
pages and I had filed the `missing_page` quality flags as "limits of the
source" without reading them. The check had caught every one of these.

**Revised later the same day**, after the folio parser was fixed. The
revision matters: one of the two "confirmed" gaps turned out not to be a
gap at all. See *The two-page spread, and why it fakes a missing page*.

## How each gap was tested

Two instruments, and they do different jobs:

- **Folio arithmetic** is what *finds* candidates — it is the only check
  that notices a page nobody transcribed.
- **The text-flow test** is what *confirms* them: does the prose run across
  the boundary? An unnumbered plate leaves the sentence intact; a missing
  page breaks it.

Flow must be read semantically, not mechanically. Two mechanical rules
failed here. A trailing hyphen means the word *should* continue (a first
pass had that backwards). And "the next page starts with a capital, so the
text broke" is wrong in Russian prose, which is full of capitalised
surnames: `…г-жа` / `Брайнина` is one name across a page turn, not a gap.
Run mechanically on the whole corpus, the flow test produced 125 flags of
which essentially all were false, and **it did not detect either real gap**.

## The two-page spread, and why it fakes a missing page

**Six scans in the corpus are double-page spreads** — one image holding two
printed leaves, roughly twice as wide as a normal page. The page table
records one `page_id` with one folio, so the folio sequence appears to skip
exactly one number. Every `+1` discontinuity in the corpus is one of these:

| spread `page_id` | folios | recorded | prose |
|---|---|---|---|
| `review_1890-91_SP_all_p027` | 146–147 | *(blank)* | procession list |
| `review_1892-93_SP_ballet_p005` | 224–225 | 224 | yes |
| `review_1893-94_SP_opera_p004` | 192–193 | 192 | yes |
| `review_1894-95_SP_opera_p014` | 180–181 | 180 | **thin — see below** |
| `review_1896-97_SP_ballet_p018` | 248–249 | 248 | yes |
| `review_1900-01_SP_ballet_p025` | 180–181 | *(blank)* | none — double-page engraving |

Both leaves' text is present in all but one case, so these are **not**
content gaps. Treat a spread as two folios before calling anything missing.

**Open worklist item (not chased):** `review_1894-95_SP_opera_p014` holds
only 222 characters of prose for two printed pages, against a median of
1,444 for a *single* page. The boundary flows, so nothing is lost at the
page turn, but the middle of the spread looks under-captured. Worth a scan
check; it needs no new scanning.

## Confirmed content gap — 1

| review | missing printed pages | what is on them | volume | held by |
|---|---|---|---|---|
| **1900-01 SP Ballet** | **176–177** (2 pages) | the rest of the «Дочь фараона» *Grand pas des fleuves* cast — p022 stops mid-name on `Темза — г-жа Фо-` — and the opening of the «Камарго» synopsis: its heading, premiere details and the start of scene 1, since the next surviving leaf picks up mid-sentence inside it | Main, vol. 11 | **ILL — UIllinois** |

Revised from "176–178, three pages". `review_1900-01_SP_ballet_p023` **is**
one of those three leaves and is physically present: it carries the end of
that synopsis and runs cleanly into folio 179. It is missing from the
arithmetic only because **the volume misprints its folio as `174`**, a
number already used by `p021` three leaves earlier — both verified at the
foot of the scans. Since p023 runs straight into 179, it is folio **178**,
leaving **176 and 177** unaccounted.

## Cleared — not gaps after all

**1896-97 SP Ballet p. 249 — NOT missing. No re-request needed.**
Previously listed as a confirmed gap on the strength of a 248→250 jump.
The jump is an artefact: `review_1896-97_SP_ballet_p018` is a **two-page
spread**, and the scan plainly shows `— 248 —` at the foot of the left leaf
and `— 249 —` at the foot of the right. The folio was stored as the dirty
string `'248 —'` (number plus the flanking rule), so every numeric test read
the leaf as carrying one folio instead of two. Both pages' text is in the
corpus. **The UMich 1896-97 request is cancelled.**

**1890-91 SP All, folios 145 → 149 — not a gap** (unchanged):
`p027` is an unnumbered double-page plate occupying **146–147** — the
«Шествіе волшебныхъ сказокъ» procession from Спящая красавица, signed
Е. Пономаревъ. `p028` is a sideways plate that **does** print its folio,
148, at the foot. 145, [146–147 spread], 148, 149: all accounted for.

**Four more single-folio jumps, all spreads, all flowing:** 1892-93 SP
Ballet (`…за прежними исполнителями:` / `г. Кшесинскимъ 1-мъ`), 1893-94 SP
Opera (`…г-жа` / `Брайнина`), 1894-95 SP Opera (`…атаманомъ имъ` / `будетъ
Антонъ`), 1900-01 SP Ballet 179→182 (`…письмо, въ` / `которомъ`, across the
double-page engraving).

## Consequences

**One re-request, not three.** Only **1900-01 (Main vol. 11, ILL —
UIllinois)** needs re-checking, for pages **176–177**. The UMich requests
for 1896-97 and 1890-91 are both cancelled — in each case the pages are
present in scans already held.

**Inventory:** every Main volume's scanning status reads `Complete!`. For
1900-01 that is wrong. Correcting `Imperial Yearbook Inventory.xlsx` needs
RG's per-change permission.

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

## The `no_folio` flags — fixed 2026-10-12

`docs/season_reviews_fields.md` said of `printed_folio`: *"76 blanks are
correct — plates and tailpiece pages carry none."* That was not right, and
the parser has since been fixed.

Six folios were recovered, all verified directly on the scans, plus one
dirty value normalised. They live in `docs/review_folio_corrections.csv`
(read by `parse_reviews.py --folio-corrections` at parse time, and
re-asserted on the merged table by
`apply_review_text_corrections.py --pages`, because the view that can see
the folio is not always the view the merge keeps).

The defect was never scanning and never the model's reading. **In these
volumes the folio is printed at the *foot* of the leaf**, alternating
right/left by recto/verso and sitting directly under the text block — not
at the head, which is where capture looked. That is why it failed on exactly
the pages with no text to anchor to: full-page plates. Plates here **are**
foliated, including rotated ones and pure half-tones that yield no text
blocks at all.

Result: blank folios **77 → 70**, and text-bearing pages with no folio
**17 → 8**. Folio arithmetic over the corpus now leaves **no** unexplained
discontinuity except the 1900-01 gap above.
