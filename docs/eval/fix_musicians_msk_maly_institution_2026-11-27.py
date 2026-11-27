"""Moscow Musicians: Малый-theatre orchestra rows filed under the wrong institution
(RG 2026-11-27 "Yes, fix those"; every page read on the scan by Claude). Five first pages of
the Малый list carried institution «Императорское С.-Петербургское Театральное Училище» with
«Оркестръ Малаго театра[.] / <sub-heading>» in heading_path; 1898-99 p004 (Nos. 21-35, the
list's continuation) carried «Оркестры.». All now take the series form used by the rest of the
Малый rows: institution «Оркестръ Малаго театра.», heading_path the sub-heading alone, written as
the same season's other Малый page writes it.
usage: fix_...py <src_raw_dir> <dst_raw_dir>"""
import json, sys
src, dst = sys.argv[1:3]
SCHOOL = "Императорское С.-Петербургское Театральное Училище"
MALY = "Оркестръ Малаго театра."
# page, first..last entry (1-based), expected institution, {old heading: new heading}
PLAN = [
    ("musicians_1894-95_MSK_p002", 47, 52, SCHOOL, {"Оркестръ Малаго театра / Капельмейстеръ": "Капельмейстеръ",
                                                     "Оркестръ Малаго театра / Музыканты": "Музыканты"}),
    ("musicians_1896-97_MSK_p002", 50, 52, SCHOOL, {"Оркестръ Малаго театра / Капельмейстеръ": "Капельмейстеръ",
                                                     "Оркестръ Малаго театра / Музыканты": "Музыканты"}),
    ("musicians_1899-00_MSK_p003", 34, 38, SCHOOL, {"Оркестръ Малаго театра / Капельмейстеръ": "Капельмейстеръ",
                                                     "Оркестръ Малаго театра / Музыканты": "Музыканты"}),
    ("musicians_1905-06_MSK_p004", 23, 37, SCHOOL, {"Оркестръ Малаго театра. / Дирижеръ": "Дирижеръ",
                                                     "Оркестръ Малаго театра. / Музыканты:": "Музыканты:"}),
    ("musicians_1907-08_MSK_p003", 20, 31, SCHOOL, {"Оркестръ Малаго театра. / Музыканты": "Музыканты"}),
    ("musicians_1898-99_MSK_p004", 1, 15, "Оркестры.", {"Музыканты:": "Музыканты"}),
]
n = 0
for page, a, b, inst, heads in PLAN:
    name = f"{page}.raw.json"
    d = json.load(open(f"{src}/{name}", encoding="utf-8"))
    for i, e in enumerate(d["entries"], start=1):
        hit = a <= i <= b
        assert (e.get("institution") == inst) == hit or not hit, (page, i)
        if not hit:
            assert e.get("institution") != SCHOOL, (page, i, "school institution outside the planned run")
            continue
        assert e.get("institution") == inst, (page, i, e.get("institution"))
        assert e.get("heading_path") in heads, (page, i, e.get("heading_path"))
        e["institution"] = MALY
        e["heading_path"] = heads[e["heading_path"]]
        n += 1
    json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n)
