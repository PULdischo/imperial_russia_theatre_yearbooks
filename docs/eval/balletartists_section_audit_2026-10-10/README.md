# BalletArtists section audit (heading_path / institution), 2026-10-10

RG asked for the whole ballet company section to be rebuilt after the stuck "Балетмейстеры" heading turned out
to be one symptom of a section that had never had a structural audit.

## Method
1. **Blind reading of all 392 pages** (21 seasons, both cities) by eight readers working from the scans only
   (`BRIEF.md`): every printed heading, its kind (title / section / staff post / another list's heading), and the
   entry it stands before; plus the first and last entry of each page and where the numbering restarts.
   Result: `readings.json`.
2. **`build_map.py`** walks each list's raw entries in page order, attaches each heading to the entry it stands
   before (list number + surname), and carries the title and the current heading forward. Output: `section_map.csv`.
3. **Cross-checks** in the same script: the women's and men's headings must fall where the numbering restarts
   at 1; the surnames under "Артистки" must be mostly feminine and under "Артисты" masculine; numbering inside a
   section must rise. All 42 lists pass; the exceptions it lists are print quirks (below).
4. **`apply.py`** writes the two fields, after checking every row against the raw file. Then the usual rebuild.

## What the print looks like
Every list has one title, **"Балетная труппа."**; a block of staff posts on the first page (sometimes running
onto the second, where the first page is an illustration: 1894-95 MSK, 1895-96 SP, 1897-98 SP, 1904-05 MSK,
1908-09 MSK, 1909-10 MSK); **"Артистки:"** numbered from 1; then **"Артисты:"** numbered from 1 again. No pupil,
guest or "left the service" sections exist before 1909-10. In 1909-10 SP, 1910-11 SP and 1910-11 MSK a short
guest heading is printed ("Танцовала / Танцовали на Петербургской | Московской сценѣ Императорскаго театра").
No continuation page carries a heading. From 1908-09 the pages have a running head and the first and last pages
share space with neighbouring lists (opera chorus above, orchestra or French drama below); none of that
neighbouring matter is in the ballet data.

## Conventions
- `institution` = the printed list title, "Балетная труппа." for all 8,760 entries. 1896-97 MSK sets the title in
  display capitals ("БАЛЕТНАЯ ТРУППА.", checked on the scan); stored in the common form.
- `heading_path` = the heading the entry stands under, verbatim with its final colon or period. Two lists print
  the women's heading with a period ("Артистки.": 1891-92 SP, 1900-01 SP; the first checked on the scan).
- A staff post applies to the name(s) under it only. A man with two posts (Легатъ, 1905-08: second ballet master
  and chief répétiteur) has two entries, each under its own post.
- The running head is not a heading and is not stored.

## Result
heading_path changed on 8,007 entries and institution on 7,861 (of 8,760). Distinct headings 164 -> 53; one
institution value instead of 32; no BalletArtists entry is left without a heading. Parsed diff: only those two
columns changed, on BalletArtists rows only (plus one `instrument`: Асафьевъ's post "Піанистъ." is now his
heading, as printed, instead of being moved to the Musicians-only instrument column). Person links untouched
(alignment check: 0 shift blocks before and after). The parse-time override that blanked the institution of
`balletartists_1903-04_MSK_p002` is retired.

Garbled post labels corrected from the readings: "Валетмейстеръ", "Виблютень" (Библіотекарь.), "Репетиторъ
(въ компаніаторъ)", "Исп. обв./облз. …", "Исп. сб. режиссера", "ціанистка", "піанисть", "Пианистъ/Пианистка".

## Raw array out of print order (handled, not reordered)
- `1902-03_MSK_p005`: women 109-118 are stored after the men's first entries; they keep "Артистки:".
- `1906-07_SP_p006`: women 120-121 likewise.
- `1904-05_MSK_p001`: the répétiteur-pianist Васильевъ is stored last (appended); he keeps his post.

## Reader caveats
Five readers lost their early page images from working memory and re-read only part of them; about 90 pages
rest on a single reading. Every such page was covered by the numbering and surname cross-checks, and none
disagreed.

## Found on the way, NOT fixed (content, not headings)
- **1907-08 SP: men's entries 78-82 are on no image** (p009 ends at 77; p010, a cropped strip, starts at 83).
  Five dancers may be missing from the data.
- `1901-02_SP_p001` idx 17: the guest Замбелли, Карлотта is stored with list_number "Замбели" and family_name
  "Карлотта" (fields shifted).
- `1899-00_SP_p000` idx 7: a note ("Прикомандированъ къ Монтіровочной части …") stored as a person.
- `1902-03_MSK_p005`: four surnames stored with Є for Ѳ ("Єедорова", "Єеоктистова").
- Print quirks reported by the readers: 1900-01 SP women jump from 127 to 158; no 65 (women) and no 46 (men) in
  1900-01 SP; 65 twice in 1900-01 MSK men; "60." for 70 and one woman printed twice (31 and 38) in 1908-09 SP;
  77 twice in 1893-94 SP; two "15." in 1906-07 SP men; Ѳ-surnames placed last in 1903-04 SP and 1905-06, but
  printed with Ф in both 1904-05 lists.
