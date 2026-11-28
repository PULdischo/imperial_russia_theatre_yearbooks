"""musicians_1900-01_MSK_p000 e005 (Герберъ, Александръ Юліевичъ): printed p. 119 sets «И. об. 2-го
капельмейстера балета.» as its own heading beside «Капельмейстеръ балета:» (scan-read by Claude), but it
was stored nested under it. heading_path only (RG 2026-11-28 "Yes, fix it").
usage: fix_...py <src_raw_dir> <dst_raw_dir>"""
import json, sys
src, dst = sys.argv[1:3]
name = "musicians_1900-01_MSK_p000.raw.json"
d = json.load(open(f"{src}/{name}", encoding="utf-8"))
e = d["entries"][4]
assert e.get("family_name") == "Герберъ", e
assert e.get("heading_path") == "Оркестръ оперы и балета / Капельмейстеръ балета / И. об. 2-го капельмейстера балета", e
e["heading_path"] = "Оркестръ оперы и балета / И. об. 2-го капельмейстера балета"
json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited 1")
