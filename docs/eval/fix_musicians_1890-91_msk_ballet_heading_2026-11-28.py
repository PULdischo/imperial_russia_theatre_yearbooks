"""musicians_1890-91_MSK_p002 e040-e041 (Альбрехтъ, Людвигъ Nos. 1 and Альбрехтъ No. 2): printed
p. 108 sets them under «Балетный оркестръ.» > «Музыканты:» (scan-read by Claude 2026-11-28), but they
were stored with a bare «Музыканты»; the rest of the list (No. 3 on, p003) and the four ballet officials
above them carry «Балетный оркестръ / …». heading_path only (RG 2026-11-28 "Yes, fix them").
usage: fix_...py <src_raw_dir> <dst_raw_dir>"""
import json, sys
src, dst = sys.argv[1:3]
name = "musicians_1890-91_MSK_p002.raw.json"
d = json.load(open(f"{src}/{name}", encoding="utf-8"))
assert len(d["entries"]) == 41
for i, num in ((39, "1."), (40, "2.")):
    e = d["entries"][i]
    assert e.get("family_name") == "Альбрехтъ" and e.get("list_number") == num and e.get("heading_path") == "Музыканты", e
    e["heading_path"] = "Балетный оркестръ / Музыканты"
json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited 2")
