# TheaterSchoolStaff BLIND SAMPLE -- full-row check against the scan -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Imperial Theater yearbook "Списокъ личнаго состава преподавателей и служащихъ ... въ Императорскихъ Театральныхъ Училищахъ" (staff of the Petersburg and Moscow Theater Schools), 1890-91..1909-10, pre-reform orthography -- report EXACTLY as printed (ъ ѣ і ѳ), never modernize; do not "correct" print variants (Всеволожской, Михаиловичъ, кол./колл. асс.). Run python only as `uv run python3` from the project directory.

## Purpose
These pages were picked at random to measure how clean the stored data is after an audit. Be independent and skeptical: read the scan FIRST, compare second. Every field of every row is in scope.

## Stored fields (per row, in `/tmp/tss/blind2/<page_id>.txt`; eNNN = 1-based index into outputs/full_run/raw/<page_id>.raw.json 'entries')
`eNNN | list number | surname | first name | patronymic | RANK: rank_or_title | SUBJ: subject_taught | NOTE: tenure_note_text | PERIODS: start->end[end_type] | INST: institution | HP: heading_path`
Conventions (settled; report only real deviations from the PRINT):
- `INST` = the printed LIST TITLE (e.g. "Списокъ личнаго состава преподавателей и служащихъ въ Императорскихъ Театральныхъ Училищахъ."; 1890-91 "Списокъ личнаго состава преподавателей и служащихъ."; 1909-10 "Списокъ служащихъ при Императорскихъ Театральныхъ Училищахъ лицъ.").
- `HP` = every printed heading governing the person, top to bottom, joined by " / ", FIRST segment = the school ("Императорское С.-Петербургское Театральное Училище" -- without "Императорское" in 1891-92..1894-95 -- or "Императорское Московское Театральное Училище"), then the printed section/sub-section headings (e.g. "Преподаватели", "а) Балетное отдѣленіе", "Классныя дамы ...", "Причтъ церкви Училища", "Служащіе"...). Trailing "." / ":" and letter-spacing are typography (ignored). Page footers/running heads are not headings.
- `SUBJ` = the printed subject taught (e.g. "Танцы", "Музыка"); post notes in parentheses such as "(священникъ церкви Училища)", "(инспекторъ Училища)" and leaving/death notes ("Оставилъ службу ...", "†") live in NOTE as printed. `RANK` is a printed title/rank only.
- Layout is two columns (left top-to-bottom, then right); a column-top continuation belongs to the previous list; list numbers continue across columns/pages; raw row order is NOT always print order (rows missed originally were appended at the END of the page's array) -- judge by the print. A person printed twice is two rows. Letter-spaced "1-й/2-й" ordinals after a surname are not part of family_name.
- The opening "(" and closing ")." around date text may be dropped in storage (cosmetic, ignore). Dates in PERIODS are derived from NOTE; check NOTE's dates against the print and PERIODS against NOTE.

## Procedure, per page
1. Open the scan `outputs/roster_images_full/images/<page_id>.png`. **You MUST zoom with PIL**: crop strips of 4-8 entries at 2.5-3x, save in /tmp/tss/blind2/crops/<your group>/, and Read every crop. State at the end how many crops you made per page. (A full-page view alone is not enough: digits and endings are small.)
2. For EVERY row, in print order, compare the stored fields with the print: surname (letter by letter: ъ/ь, ѣ, і/и, ѳ, д/л, ц/щ, н/м ...), first name, patronymic, list number, subject, every date digit and month word, end / † / leaving / transfer / appointment notes, and the heading chain + school (is the person under the right school and the right printed section/sub-section; no missing or extra level; no person name or number leaked into a heading; the Moscow list begins where the print says). Also look for printed entries that are MISSING from the stored rows, stored rows that are not on the page, and duplicates.
3. Report ONLY real discrepancies, each with the exact printed text and the exact stored text. Mark UNCERTAIN where the print is illegible; do not guess. Beware reading Ukrainian "є" where the print is і followed by е -- compare against a plain е on the same line.

## Rules
REPORT ONLY. Do NOT edit/create/delete project files. Crops ONLY under /tmp/tss/blind2/crops/<your group>/; also write your final section to /tmp/tss/blind2/results/group<N>.txt. No spawn_task.

## REPORT FORMAT (end with exactly this)
```
PAGE SUMMARY
<page_id> | rows stored: N | rows checked: N | crops made: K | discrepancies: M (surname a, first/patronymic b, date/tenure c, list-number d, subject e, heading/school f, missing/extra rows g)
DISCREPANCIES
<page_id> | eNNN | FIELD | STORED: "<exact>" | PRINTED: "<exact>" | confidence DIRECT|UNCERTAIN | note
OTHER FINDINGS
- one short line each
```
