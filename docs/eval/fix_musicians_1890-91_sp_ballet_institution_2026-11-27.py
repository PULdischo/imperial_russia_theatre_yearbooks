"""musicians_1890-91_SP_p002: the 11 ballet-orchestra rows (Дриго, Каннегиссеръ, the three
répétiteurs, musicians Nos. 1-6) carried the raw institution «Императорское С.-Петербургское
Театральное Училище». The scan (printed p. 77) sets «Балетный оркестръ.» under «Оркестры.»; per
#130 (RG 2026-10-02) ballet-orchestra rows take institution «Оркестры.» with «Балетный оркестръ / …»
in heading_path, as on p003-p004 of the same list. Institution only (RG 2026-11-27 "Yes, fix them").
usage: fix_...py <src_raw_dir> <dst_raw_dir>"""
import json, sys
src, dst = sys.argv[1:3]
SCHOOL = "Императорское С.-Петербургское Театральное Училище"
name = "musicians_1890-91_SP_p002.raw.json"
d = json.load(open(f"{src}/{name}", encoding="utf-8"))
n = 0
for i, e in enumerate(d["entries"], start=1):
    if e.get("institution") == SCHOOL:
        assert 30 <= i <= 40 and (e.get("heading_path") or "").startswith("Балетный оркестръ / "), (i, e)
        e["institution"] = "Оркестры."
        n += 1
assert n == 11, n
json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n)
