# ProductionTeam FINAL-OUTPUT spot check -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook staff list (ProductionTeam: decorators, machinists, lighting, props, wardrobe, wigmakers; St Petersburg and Moscow). Run python only as `uv run python3` from the project directory.

## Background
Each stored row has `institution` and `heading_path`. By convention (docs/schema.md): `institution` = the printed LIST TITLE ("Списокъ личнаго состава служащихъ по монтировочной|постановочной части."); `heading_path` = every printed heading between the title and the person, top to bottom, joined by " / ", FIRST segment = the city heading (С.-ПЕТЕРБУРГЪ or МОСКВА, printed without its trailing period), then department ("Отдѣлъ декораціонный", "Отдѣлъ освѣтительный", "Отдѣлъ бутафорскій", "Отдѣлъ гардеробный", "Главный гардеробъ", "Мѣстные гардеробы", "Парикмахерскій отдѣлъ" ...), group/sub-list ("Декораторы", "Помощники декораторовъ", "Ученики декораціонной живописи", "Гардеробмейстеры"/"-ши", "Костюмеры"/"Костюмерши", "Смотрительницы отдѣловъ", "Парикмахеры" ...), troupe/theatre, role ("Машинистъ-механикъ", "Помощникъ машиниста", "Завѣдывающій освѣщеніемъ" ...). Conventions already settled and NOT to be re-litigated (report only real deviations from the PRINT): trailing "."/":" and letter-spacing are typography (ignored); layout is two-column and a column-top continuation belongs to the previous list; list numbers continue across columns/pages; machinists are chained under "Отдѣлъ декораціонный" (also in Moscow, where the group heading itself is not printed); Парикмахеры under "Отдѣлъ гардеробный" (except Moscow's own "Парикмахерскій отдѣлъ", 1908-10); "Главный гардеробъ" and "Мѣстные гардеробы" are top-level departments (never under Отдѣлъ гардеробный); a theatre heading is a chain level (e.g. "Мѣстные гардеробы / Гардеробмейстеры / Маріинскій театръ"); the raw row order is NOT always print order on interleaved pages -- judge by the print.

## Procedure, per assigned page
1. Read `/tmp/audit12/<page_id>.txt` (every row, in stored order, with its STORED institution // heading_path) and the scan `outputs/roster_images_full/images/<page_id>.png`. **Zoom with PIL** (crop strips of 6-8 entries at 2.5-3x, save in /tmp/audit12/crops/<your group>/, Read them) -- headings are small, bold or letter-spaced.
2. Go through the page in print order (left column top to bottom, then right). For EVERY row decide: is the stored chain exactly the printed chain governing that person (right city, department, sub-list, theatre/troupe, role; no missing parent, no extra/leaked level, no wrong word, no person name or list number in it)? Also check the city heading is right for the row (Moscow section starts at the printed МОСКВА heading), and that the surname on the row is the person printed there.
3. Report ONLY rows where the stored chain (or city, or surname) is wrong; give the correct chain. Mark UNCERTAIN where a heading is illegible; do not guess. Pre-reform spelling exactly as printed (ъ ѣ і ѳ).

## Rules
REPORT ONLY. Do NOT edit/create/delete project files. Crops ONLY in /tmp/audit12/crops/<your group number>/; also write your final section to /tmp/audit12/results/group<N>.txt. No spawn_task.

## REPORT FORMAT (end your final message with exactly this)
```
PAGE SUMMARY
<page_id> | rows checked: N | rows wrong: M
CORRECTIONS
<page_id> | eNNN[-eMMM] | STORED: "<stored heading_path>" | CORRECT: "<chain>" | confidence: DIRECT|UNCERTAIN | short note
OTHER FINDINGS
- one short line each
```
