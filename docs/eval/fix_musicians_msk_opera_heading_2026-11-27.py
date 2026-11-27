"""Moscow Musicians, 11 seasons: rows printed under «Оркестръ оперы и балета.» but stored
without it get the root in the season's own p000 form (RG 2026-11-27 "Yes, fix the 1,109";
first scan pages read by Claude; docs/eval/gold_refresh_2026-11-27.md). heading_path only.
1906-07..1910-11 print no such heading and are left alone. Lost/garbled headings, the
1900-01 nesting «Капельмейстеръ балета / И. об. …» and misfiled Малый rows are NOT touched.

entry_id NNN = position NNN-1 in the page's raw `entries`, checked against family_name and
heading before editing. usage: fix_...py <db> <src_raw_dir> <dst_raw_dir>"""
import json, sys, re
import duckdb
db, src, dst = sys.argv[1:4]
MIL, TUN = "Капельмейстеръ военной музыки", "Настройщикъ"
# season -> (root prefix incl. separator, [(institution, page suffix or None, headings)])
SPEC = {
    "1894-95": ("Оркестръ оперы и балета. ", [("Оркестры.", "p002", {"Музыканты"})]),
    "1896-97": ("Оркестръ оперы и балета. ", [("Оркестры.", "p001", {"Музыканты:"})]),
    "1898-99": ("Оркестръ оперы и балета / ", [("Оркестры", None, {"Репетиторы", MIL, "Музыканты"})]),
    "1899-00": ("Оркестръ оперы и балета / ", [("Оркестры.", "p003", {"Музыканты"})]),
    "1900-01": ("Оркестръ оперы и балета / ", [("Оркестры.", None, {"Капельмейстеръ балета",
                "Капельмейстеръ балета / И. об. 2-го капельмейстера балета", "Репетиторы", MIL, "Музыканты"})]),
    "1901-02": ("Оркестръ оперы и балета / ", [("Оркестры.", None, {"Капельмейстеры оперы",
                "Главный капельмейстеръ балета", "И. об. 2-го капельмейстера балета", "Репетиторы", MIL, "Музыканты"})]),
    "1902-03": ("Оркестръ оперы и балета / ", [("Оркестры.", None, {"Репетиторы", MIL, TUN, "Музыканты"})]),
    "1903-04": ("Оркестръ оперы и балета / ", [("Оркестры", None, {MIL, TUN, "Музыканты"})]),
    "1904-05": ("Оркестръ оперы и балета / ", [("Оркестры", None, {"Репетиторы:", MIL, TUN, "Музыканты:"}),
                                               ("Оркестры.", "p002", {"Музыканты"})]),
    "1905-06": ("Оркестръ оперы и балета / ", [("Оркестры.", None, {"Капельмейстеры оперы",
                "Главный капельмейстеръ балета", "Репетиторы", "Аккомпаніаторы", MIL, TUN, "Музыканты",
                "И. сб. 2-го капельмейстера балета"})]),
    "1911-12": ("Оркестръ оперы и балета. / ", [("МОСКОВСКІЕ ОРКЕСТРЫ.", None, {"Музыканты:"})]),
}
EXPECTED = {"1894-95": 46, "1896-97": 52, "1898-99": 129, "1899-00": 33, "1900-01": 127, "1901-02": 89,
            "1902-03": 130, "1903-04": 94, "1904-05": 133, "1905-06": 140, "1911-12": 136}
c = duckdb.connect(db, read_only=True)
by_page, per = {}, {}
for season, (root, groups) in SPEC.items():
    for inst, page, heads in groups:
        q = """select entry_id, page_id, family_name, heading_path from raw.person_entry
               where page_id like ? and institution = ? and heading_path in (select unnest(?))"""
        pat = f"musicians_{season}_MSK_{page or '%'}"
        for eid, pid, fam, h in c.execute(q, [pat, inst, sorted(heads)]).fetchall():
            by_page.setdefault(pid, []).append((int(eid.rsplit("__e", 1)[1]) - 1, fam, h, root))
            per[season] = per.get(season, 0) + 1
assert per == EXPECTED, per
n = 0
for pid, items in sorted(by_page.items()):
    name = f"{pid}.raw.json"
    d = json.load(open(f"{src}/{name}", encoding="utf-8"))
    for i, fam, h, root in items:
        e = d["entries"][i]
        assert (e.get("family_name") or "").strip() == (fam or "").strip(), (pid, i, e.get("family_name"), fam)
        assert e.get("heading_path") == h, (pid, i, e.get("heading_path"), h)
        e["heading_path"] = root + h
        n += 1
    json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n, "rows on", len(by_page), "pages;", per)
