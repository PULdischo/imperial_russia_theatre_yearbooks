"""St Petersburg Musicians, 16 seasons (1891-92..1909-10, not 1902-03/1903-04/1907-08):
rows printed under the orchestra heading («Оперный оркестръ.» 1891-93, «Оркестръ оперы и
балета.» after) but stored without it get the season's own root, as on its p000 (RG
2026-11-27 "Yes, fix all 16"; layout scan-read by Claude on every season's first page;
docs/eval/gold_refresh_2026-11-27.md). heading_path only.

Targets come from raw.person_entry (institution «Оркестры.»/«Оркестры», heading one of
TARGETS); entry_id NNN = position NNN-1 in the page's raw `entries` array, checked
against family_name and heading before any edit.

usage: fix_...py <db> <src_raw_dir> <dst_raw_dir>"""
import json, sys, re
import duckdb
db, src, dst = sys.argv[1:4]
ROOT = {"1891-92": "Оперный оркестръ", "1892-93": "Оперный оркестръ", "1909-10": "Оркестръ оперы и балета."}
SEASONS = ["1891-92", "1892-93", "1893-94", "1894-95", "1895-96", "1896-97", "1897-98", "1898-99",
           "1899-00", "1900-01", "1901-02", "1904-05", "1905-06", "1906-07", "1908-09", "1909-10"]
TARGETS = {"Музыканты", "Музыканты:", "Капельмейстеръ военной музыки",
           "Второй капельмейстеръ оперы", "Капельмейстеръ балета",
           "И. об. помощника капельмейстера балета", "Репетиторы балета", "Репетиторы балета:",
           "Аккомпаніаторъ"}
c = duckdb.connect(db, read_only=True)
rows = c.execute(f"""select entry_id, page_id, family_name, heading_path from raw.person_entry
    where page_id like 'musicians_%_SP_%' and institution in ('Оркестры.', 'Оркестры')
    and regexp_extract(page_id, 'musicians_([0-9-]+)_', 1) in ({",".join("'"+s+"'" for s in SEASONS)})
    and heading_path in ({",".join("'"+t+"'" for t in TARGETS)})
    order by entry_id""").fetchall()
by_page = {}
for eid, pid, fam, h in rows:
    by_page.setdefault(pid, []).append((int(eid.rsplit("__e", 1)[1]) - 1, fam, h))
n = 0
per_season = {}
for pid, items in sorted(by_page.items()):
    season = re.search(r"musicians_([0-9-]+)_", pid).group(1)
    root = ROOT.get(season, "Оркестръ оперы и балета")
    name = f"{pid}.raw.json"
    d = json.load(open(f"{src}/{name}", encoding="utf-8"))
    for i, fam, h in items:
        e = d["entries"][i]
        assert (e.get("family_name") or "").strip() == (fam or "").strip(), (pid, i, e.get("family_name"), fam)
        assert e.get("heading_path") == h, (pid, i, e.get("heading_path"), h)
        e["heading_path"] = f"{root} / {h}"
        n += 1
        per_season[season] = per_season.get(season, 0) + 1
    json.dump(d, open(f"{dst}/{name}", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("edited", n, "rows on", len(by_page), "pages")
for s in SEASONS: print(" ", s, per_season.get(s, 0))
