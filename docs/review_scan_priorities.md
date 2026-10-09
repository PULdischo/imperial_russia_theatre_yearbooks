# Drama/Opera season reviews: which need from-volume scans (dance-related content)

Built 2026-10-09 from the HathiTrust page-reading checks (`docs/eval/review_check_*/`), the inventory (read-only) and the review tables already in the database. Rule (RG): HathiTrust is for **triage**; anything cited or extracted by name comes from RG's own scans. The ballet reviews are already scanned for all seasons that have them; this list is about the **Opera and Drama** reviews. "Dance pages" = pages where the blind readers found a ballet/dance mention (includes some plot summaries, so it overstates a little).

## 1. Needs a from-volume scan (checked on HathiTrust, dance-related content found)
| Priority | Season, city, section (printed pages) | Volume, source | Evidence | Request-list status |
|---|---|---|---|---|
| 1 | **1903-04 SP Opera 77-106** | Vol. 14, **Princeton** | 14 of 31 pages: named dancers and balletmasters in at least seven operas; the 3 Apr, 10 Apr, 17 Apr 1904 divertissements resolved (Гельцеръ in «Конекъ-Горбунокъ», Act 4; Преображенская, Павлова 2-я, Трефилова) | on list (TO SCAN, Princeton copy) |
| 1 | **1903-04 Moscow Opera 149-178** | Vol. 14, **Princeton** | 11 of 27 pages: 18 Oct 1903 benefit with Act 3 «Конекъ-Горбунокъ» + Act 1 «Донъ-Кихотъ» (conflicts with the Repertoire: «Алеко» vs «Моцартъ и Сальери»); Горскій's named dancers in «Добрыня Никитичъ», «Наль и Дамаянти», «Искатели жемчуга» | on list |
| 2 | **1903-04 SP Drama 3-76** | Vol. 14, **Princeton** | 3 of 64 pages, but one is major: «Калигула», Act 5 «Вакхическій танецъ» by Кшесинская, Чумакова, Борхардтъ, Карсавина, Макарова (folio 65) | on list |
| 1 | **1901-02 SP Opera 103-165** | Vol. 12, ILL UMich (returned) | 8 of 56 pages: ~40 named dancers in the «Демонъ» revival of 23 Feb 1902; Ширяевъ's dances in two operas; 27 Apr 1902 plain Дивертиссементъ = ballet | on list |
| 1 | **1901-02 Moscow Opera 265-284** | Vol. 12, ILL UMich | 1 of 18 pages, but it itemizes the 20 Apr 1902 «Балетный дивертиссементъ» with named dancers and numbers (folio 283) | on list |
| 2 | **1901-02 SP Drama 17-102** | Vol. 12, ILL UMich | 6 of 82 pages: «Сонъ въ лѣтнюю ночь» staged with ballet and Theatre School pupils (22 performances in the Repertoire), named dancers in the drama «Фаустъ» | on list |
| 1 | **1905-06 Moscow Opera 183-208** | Vol. 16, ILL Yale (returned) | 7 of 26 pages: named dancers in «Панъ-воевода» and «Аида»; the 15 Apr 1906 «Травіата» + divertissement | on list |
| ? | **1905-06 SP Opera 80-125** | Vol. 16, ILL Yale | **not yet checked** (on the list at RG's request; check on HathiTrust first) | on list |

## 2. Checked, no from-volume scan needed (nothing dance-related found)
- **Moscow Drama:** 1905-06 (1 of 33 pages, only lines of *The Tempest*), 1901-02 (2 of 40, nothing real), 1903-04 (0 of 24). Skip unless something else turns up.

## 3. Not yet checked on HathiTrust (decide order; cheapest first)
Season, held-by from the inventory's Main volume (Opera/Drama sections not yet in hand):
| Season and city | Main volume | Held by |
|---|---|---|
| 1892-93 Moscow, 1893-94 Moscow (Opera; SP Opera already scanned) | Vols. 3, 4 | **Princeton** |
| 1895-96 (both), 1897-98 (both), 1904-05 (both) | Vols. 6, 8, 15 | **Princeton** |
| 1891-92 (both) | Vol. 2 | ILL UMich |
| 1896-97 (both) | Vol. 7 | ILL UMich |
| 1898-99 (both) | Vol. 9 | ILL NYPL |
| 1899-00 SP, 1900-01 SP (Opera; Moscow ones already scanned) | Vols. 10, 11 | ILL UIllinois |
| 1905-06 SP Drama/Opera | Vol. 16 | ILL Yale |
| 1906-07, 1907-08 (both) | Vols. 17, 18 | ILL Yale |
| 1908-09, 1909-10, 1910-11 Moscow (issue era, several issues per season) | see `yearbook-issue-structure-from-1908-09` | varies |
Princeton-held volumes can be checked by RG on the physical copy as well as through the Princeton scan on HathiTrust (`njp.32101060036769` is the 1903-04 volume).

## 4. Already scanned and in the database (dance words can be mined at no cost)
Opera or whole-theatre reviews already extracted (blocks with a ballet/dance word / blocks): 1890-91 SP (all) 28/313; 1892-93 SP 17/153; 1893-94 SP 10/133; 1894-95 Moscow 17/120, SP 9/108; 1899-00 Moscow (all) 14/74; 1900-01 Moscow 9/62; 1902-03 Moscow 3/66, SP 7/93; 1910-11 SP 3/79. Not in the database but scanned (PDFs exist): 1908-09 Opera SP and Moscow, 1912-13 Opera SP (check why). These can be read for named dancers and divertissements without any HathiTrust step.

## Caveats
- Dance-page counts come from blind model readers and were checked by hand on the key pages only; treat them as a triage ranking, not data.
- Season-by-season cost of the page-reading checks was 0.6-1.3 million tokens per city-season; a keyword triage on the HathiTrust text is untested.
