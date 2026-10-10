# Arbiter brief: which reading is printed?

Scanned pages of the Ежегодникъ Императорскихъ театровъ (1890-1910), pre-reform Russian orthography (ъ, ѣ, і, ѳ).
Each row of your chunk CSV names ONE place in the small credit summary printed under a BalletArtists entry
(the italic lines «Въ 7 балетахъ—21; … Всего—22 раза. Въ томъ числѣ: …») where two earlier readers disagree.

Columns: `item_id, entry_id, image, list_number, name, context, option_A, option_B`.
- `image`: the page image (two columns; entries are numbered).
- `list_number` and `name`: find that entry. The name is only to help you find it.
- `context`: the words printed around the place in question (a few words before and after).
- `option_A`, `option_B`: the two readings of the word or number at that place. `(nothing there)` means one
  reader had no word there at all.

## Your task
For every row, zoom in on that exact place (crop and enlarge) and decide what is PRINTED:
- `A` if option_A is what is printed, `B` if option_B is, 
- `OTHER:<what you read>` if neither is right (type it exactly as printed),
- `UNREADABLE` if you cannot tell.
Look at the letter shapes, not at which option looks more like a normal word: pre-reform spelling is not
consistent, a printer's slip is a slip, and both options can be plausible words. Typical confusions to check
carefully: final ъ/ь, и/н, ч/г, д/л, ѣ/е, 3/8, 5/6, 1/7. Do NOT guess. Do NOT make a number add up.
Type every letter in Cyrillic unless the print itself is Latin.

## What to write
Create ONLY your report: UTF-8 CSV `item_id,answer,note` (quote fields containing commas), one row per input
row, same order. `note`: a few words on what you saw (e.g. "closed loop, clearly 8", "worn, ь vs ъ uncertain").
Do not edit any other file. Do not run git. Do not start background tasks or spawn agents. Do not look in any
database or other reports: the point is an independent reading of the scan.
