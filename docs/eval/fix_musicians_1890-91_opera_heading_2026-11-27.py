"""Musicians 1890-91 SP: the opera-orchestra list (Оглоблинъ + musicians 1-103,
p000-p002) is printed under «Оперный оркестръ.» but stored without it
(2026-11-27, scan-read by Claude). Only heading_path changes."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
n = 0
for p in ("p000", "p001", "p002"):
    name = f"musicians_1890-91_SP_{p}.raw.json"
    d = json.load(open(f"{src}/{name}", encoding="utf-8"))
    for e in d["entries"]:
        h = e.get("heading_path")
        if h == "Музыканты" or (p == "p000" and h == "Капельмейстеръ военной музыки"):
            e["heading_path"] = "Оперный оркестръ / " + h
            n += 1
    json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n)
