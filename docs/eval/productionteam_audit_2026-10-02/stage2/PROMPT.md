# ProductionTeam SECTION-STRUCTURE verification -- REPORT ONLY

Project: "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main". Historical Imperial Theater yearbook staff lists (ProductionTeam: decorators, machinists, lighting, props, wardrobe, wigmakers; St Petersburg and Moscow theatres). Run python only as `uv run python3` from the project directory.

## Background
Each stored row has `institution` and `heading_path` (a chain of the printed headings that govern the entry, joined by " / "). The LAST segment of heading_path is the entry's role/sub-list (e.g. "Помощники декораторовъ", "Машинистъ-механикъ") and is used for analysis, so it must be exactly right. A rule-based clean-up has produced a PROPOSED section for every row (it fixed spelling, stripped leaked names/list numbers, and re-assigned rows whose list numbers continue the previous sub-list). Your job is to check, row by row against the scan, whether the PROPOSED section is right.

## Procedure, per assigned page
1. Read the bundle `/tmp/audit9/<page_id>.txt` (each row: eNNN, list number, surname, PROPOSED section, and WAS= the earlier stored value when the proposal changed it). Read the scan `outputs/roster_images_full/images/<page_id>.png`.
2. Go through the page in printed order (left column top to bottom, then right column; continuation text at the top of a column belongs to the list that began in the previous column or on the previous page). **Zoom** with PIL (crop strips of 6-8 entries, 2.5-3x, save in /tmp/audit9/crops/<your group>/, Read them) -- headings are small, letter-spaced or bold.
3. For each row work out the full chain of printed headings that governs it, top to bottom: department ("Отдѣлъ декораціонный", "Отдѣлъ освѣтительный", "Отдѣлъ бутафорскій", "Отдѣлъ гардеробный", "Машинисты и ихъ помощники", "Главный гардеробъ", "Мѣстные гардеробы", "Парикмахеры" ...), group/sub-list ("Декораторы", "Помощники декораторовъ", "Ученики декораціонной живописи", "Гардеробмейстеры"/"Гардеробмейстерши", "Костюмеры"/"Костюмерши", "Смотрительницы отдѣловъ" ...), troupe/theatre ("Большой театръ", "Оперная труппа" ...), role ("Машинистъ-механикъ", "Помощникъ машиниста", "Завѣдывающій освѣщеніемъ"...). Do not include the city (МОСКВА / С.-ПЕТЕРБУРГЪ) or the page's document title. Letter-spacing ("К о с т ю м е р ы") and the trailing "." or ":" printed after headings are typography -- ignore them.
4. Compare with PROPOSED. Report ONLY rows where the proposal is wrong or incomplete (wrong sub-list/role, wrong theatre or troupe, wrong department, a printed parent level missing, a wrong word, a person's name left in the chain). For each, give the correct chain. Rows that are right need no line.
5. Beware: a heading printed ABOVE an entry governs it; an entry printed at the top of a column/page BEFORE the next heading still belongs to the previous list.

## Rules
- REPORT ONLY. Do NOT edit/create/delete project files. Crops go ONLY in /tmp/audit9/crops/<your group number>/ (create it). Also write your final section to /tmp/audit9/results/group<N>.txt (the only file you may write besides crops). No spawn_task.
- Mark UNCERTAIN where a heading is not legible; do not guess.
- Pre-reform spelling exactly as printed (ъ ѣ і ѳ).

## REPORT FORMAT (end your final message with exactly this section)
```
PAGE SUMMARY
<page_id> | rows checked: N | rows with a wrong/incomplete proposed section: M
CORRECTIONS
<page_id> | eNNN[-eMMM] | PROPOSED: "<proposed heading_path>" | CORRECT: "<chain top->bottom, ' / ' separated>" | confidence: DIRECT|UNCERTAIN | short note
OTHER FINDINGS
- one short line each
```
