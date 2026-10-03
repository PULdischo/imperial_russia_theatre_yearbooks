# ProductionTeam BLIND SAMPLE -- full-row check against the scan -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Imperial Theater yearbook staff list (ProductionTeam: decorators, machinists, lighting, props, wardrobe, wigmakers; St Petersburg and Moscow), 1890-91..1909-10, pre-reform orthography -- report EXACTLY as printed (ъ ѣ і ѳ), never modernize. Run python only as `uv run python3` from the project directory.

## Purpose
These pages were picked at random to measure how clean the stored data is. Be independent and skeptical: read the scan FIRST, compare second. Every field of every row is in scope.

## Stored fields (per row, in `/tmp/audit18/<page_id>.txt`; eNNN = 1-based index into outputs/full_run/raw/<page_id>.raw.json 'entries')
list number | surname | first name | patronymic | rank_or_title (a title, rank, or the workshop specialty) | tenure_note_text (the date parenthetical and every note after it: "(съ 1 сентября 1882 г.). Оставилъ службу ...", † dates, "Переведенъ ...", "Назначенъ ...", specialty text) | institution // heading_path.
Conventions (settled; report only real deviations from the PRINT): `institution` = the list title "Списокъ личнаго состава служащихъ по монтировочной|постановочной части."; `heading_path` = every printed heading governing the person, top to bottom, joined by " / ", FIRST segment = the city heading (С.-ПЕТЕРБУРГЪ or МОСКВА, no period), then department ("Отдѣлъ декораціонный", "Отдѣлъ освѣтительный", "Отдѣлъ бутафорскій", "Отдѣлъ гардеробный"; "Главный гардеробъ" and "Мѣстные гардеробы" are printed one rank BELOW Отдѣлъ гардеробный and are stored as its children; Moscow 1908-10 "Парикмахерскій отдѣлъ" and "Мастерская по раскраскѣ тканей" are departments of their own; machinists sit under "Отдѣлъ декораціонный"; "Парикмахеры" under "Отдѣлъ гардеробный"), then group/sub-list ("Декораторы", "Помощники декораторовъ", "Ученики декораціонной живописи", "Гардеробмейстеры"/"-ши", "Костюмеры"/"Костюмерши", "Смотрительницы отдѣловъ"...), troupe/theatre, role. A theatre heading is a chain level, printed order kept. Trailing "." / ":" and letter-spacing are typography (ignored); the opening "(" and closing ")." around the date text may be dropped in storage (cosmetic, ignore). Layout is two columns (left column top-to-bottom, then right); a column-top continuation belongs to the previous list; list numbers continue across columns/pages; raw row order is NOT always print order -- judge by the print. A person printed twice on a page (two troupes/posts) is two rows.

## Procedure, per page
1. Open the scan `outputs/roster_images_full/images/<page_id>.png`. **You MUST zoom with PIL**: crop strips of 5-8 entries at 2.5-3x, save in /tmp/audit18/crops/<your group>/, and Read every crop. State at the end how many crops you made per page. (A full-page view alone is not enough: digits and endings are small.)
2. For EVERY row, in print order, compare the stored fields with the print: surname (letter by letter: ъ/ь, ѣ, і/и, ѳ, д/л, ц/щ, н/м ...), first name, patronymic, list number, every date digit and month word, end / † / leaving / transfer / appointment notes, the specialty text, and the chain + city (is the person under the right heading, the right theatre/troupe, the right city, no missing or extra level, no person name or number leaked into a heading). Also look for printed entries that are MISSING from the stored rows, stored rows that are not on the page, and duplicates.
3. Report ONLY real discrepancies, each with the exact printed text and the exact stored text. Mark UNCERTAIN where the print is illegible; do not guess.

## Rules
REPORT ONLY. Do NOT edit/create/delete project files. Crops ONLY under /tmp/audit18/crops/<your group>/; also write your final section to /tmp/audit18/results/group<N>.txt. No spawn_task.

## REPORT FORMAT (end with exactly this)
```
PAGE SUMMARY
<page_id> | rows stored: N | rows checked: N | crops made: K | discrepancies: M (surname a, first/patronymic b, date/tenure c, list-number d, chain/city e, missing/extra rows f)
DISCREPANCIES
<page_id> | eNNN | FIELD | STORED: "<exact>" | PRINTED: "<exact>" | confidence DIRECT|UNCERTAIN | note
OTHER FINDINGS
- one short line each
```
