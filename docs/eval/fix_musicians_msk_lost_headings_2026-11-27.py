"""Moscow Musicians continuation pages whose heading was lost or garbled (RG 2026-11-27
"Yes, fix those"; each page read on the scan by Claude: all four are plain continuations
that print no heading or title of their own). Values follow the season's own p000 form.
- 1892-93 p002 e016 (Альбрехтъ, Людвигъ): stored heading «Балетный оркестръ / Музыканты / Музыканты»
  (doubled). Raw already has «Балетный оркестръ / Музыканты»; the doubling came from
  parse_and_validate._repair_musicians_stray_heading, which appends «Музыканты» when this row's
  rank_or_title holds the printed section header «Музыканты:» (written before #130 put the segment
  into the raw heading). Fix: clear that stray rank_or_title (the print gives him no rank).
- 1896-97 p002 e001-e049 (Nos. 77-125): garbled «Оркестръ оперы и балета. Завѣдывающій …
  Музыканты:» -> «Оркестръ оперы и балета. Музыканты:»
- 1901-02 p002 e001-e039 (Nos. 35-73): no heading -> «Оркестръ оперы и балета / Музыканты».
  The blank came from parse_and_validate._HEADING_PATH_RESTORE_FIXES forcing NULL (raw held
  «Музыканты»); that table entry is removed in the same change.
- 1903-04 p002 e001-e038 (Nos. 60-97): no heading -> «Оркестръ оперы и балета / Музыканты», and
  the invented institution «Списокъ скрипачей, альтовъ, …» -> the series' «Оркестры»
usage: fix_...py <src_raw_dir> <dst_raw_dir>"""
import json, sys
src, dst = sys.argv[1:3]
GARBLED = "Оркестръ оперы и балета. Завѣдывающій дѣлами оркестровъ и капельмейстеръ оперы. Музыканты:"
PLAN = [  # page, first..last entry (1-based), expected old heading, new heading, new institution
    ("musicians_1896-97_MSK_p002", 1, 49, GARBLED, "Оркестръ оперы и балета. Музыканты:", None),
    ("musicians_1901-02_MSK_p002", 1, 39, "Музыканты", "Оркестръ оперы и балета / Музыканты", None),
    ("musicians_1903-04_MSK_p002", 1, 38, None, "Оркестръ оперы и балета / Музыканты", "Оркестры"),
]
n = 0
name = "musicians_1892-93_MSK_p002.raw.json"
d = json.load(open(f"{src}/{name}", encoding="utf-8"))
e = d["entries"][15]
assert e.get("family_name") == "Альбрехтъ" and e.get("rank_or_title") == "Музыканты:", e
assert e.get("heading_path") == "Балетный оркестръ / Музыканты", e
e["rank_or_title"] = None
n += 1
json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for page, a, b, old, new, inst in PLAN:
    name = f"{page}.raw.json"
    d = json.load(open(f"{src}/{name}", encoding="utf-8"))
    for i in range(a - 1, b):
        e = d["entries"][i]
        assert (e.get("heading_path") or None) == old, (page, i, e.get("heading_path"))
        if inst:
            assert (e.get("institution") or "").startswith("Списокъ скрипачей"), (page, i, e.get("institution"))
            e["institution"] = inst
        e["heading_path"] = new
        n += 1
    if inst:  # the next entry must not be part of the run
        assert len(d["entries"]) == b, (page, len(d["entries"]))
    json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n)
