"""1898-99 Repertoire: eight receipts cells that differ from the print, found by the blind read of all six columns
(2026-10-28, four agents read the scans before seeing the data) and each confirmed by Claude at full resolution on
ForUpload_1898-99_Repertoire.pdf. Ledger 1898-99.
uv run python docs/eval/reconciliation/fix_1898_99_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
FIXES = [  # (page, 1-based session index, date_text, theater prefix, first work, stored, print, why)
    ("p004", 6, "29 Вторн.", "Михайлов", "Le Docteur Jojo", "1010 р. 85 к.", "1010 р. 55 к.", "kopecks misread"),
    ("p010", 33, "12 Четвергъ", "Маріин", "Карменъ", "3502 р. 50 к.", "3602 р. 50 к.", "damaged 6 read as 5"),
    ("p017", 6, "6 Воскрес.", "Новый", "Трубадуръ", "1743 р. 13 к.", "1243 р. 13 к.", "damaged 2 read as 7"),
    ("p020", 25, "7 Четвергъ", "Маріин", "Снѣгурочка", "3502 р. 50 к.", "3602 р. 50 к.", "damaged 6 read as 5"),
    ("p022", 14, "16 Суббота.", "Александрин", "Женитьба Бѣлугина", "2778 р. 50 к.", None,
     "charity performance prints no figure; the stored figure was copied from the Михайловскій cell beside it"),
    ("p024", 39, "4 Четвергъ", "Михайлов", "Fanny Lear", "723 р. 60 к.", "723 р. 80 к.", "broken 8 read as 6"),
    ("p026", 35, "15 Понед.", "Маріин", "Сказки Гофмана", "2475 р. 30 к.", "3475 р. 30 к.", "thousands digit misread"),
    ("p031", 5, "27 Суббота.", "Новый", "Дитя", "663 р. 31 к.", "668 р. 31 к.", "S-shaped 8 read as 3"),
]
pages = {}
def load(page):
    p = RAW / f"repertoire_1898-99_{page}.raw.json"
    if p not in pages:
        t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
        for ind in (2, 4, 1, None):
            for ea in (False, True):
                for tr in ("", "\n"):
                    if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
        assert fmt, p
        pages[p] = (d, fmt)
    return pages[p][0]

def add_note(S, note):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note

for page, i, date_text, th, work, old, new, why in FIXES:
    S = load(page)["sessions"][i - 1]
    assert S["date_text"] == date_text and S["theater"].startswith(th) and S["receipts_text"] == old, S
    assert S["works"][0]["work_title"] == work, S["works"]
    S["receipts_text"] = new
    add_note(S, f"scan 2026-10-28: receipts «{old}» -> «{new if new else 'none printed'}» ({why}; blind column read)")
    print(page, date_text, S["theater"], old, "->", new)

# Новый, p. 21 (p019), 28 Dec 1898: the print has «Василиса Мелентьева, др.» in the morning (272 р. 18 к.) and «Вій, др. сказка»
# in the evening (1019 р. 82 к.); the extraction put «Риголетто, оп.» (the 27th's evening work) in the morning and both plays
# in the evening. The receipts were right. Also the title «Вій» (і, not ѣ) on 17, 28 and 30 Dec, as printed on this page and on
# every later date. Found when the Новый drama line came out exactly 272.18 р. short; read on the scan by Claude.
P = load("p019")["sessions"]
m, e = P[31], P[32]  # s032 morning, s033 evening
assert m["date_text"].startswith("28 ") and m["session"] == "morning" and m["theater"].startswith("Новый") and m["receipts_text"] == "272 р. 18 к."
assert [w["work_title"] for w in m["works"]] == ["Риголетто"]
assert e["session"] == "evening" and [w["work_title"] for w in e["works"]] == ["Василиса Мелентьева", "Вѣй"]
m["works"] = [e["works"][0]]
e["works"] = [e["works"][1]]
add_note(m, "scan 2026-10-28: works «Риголетто, оп.» -> «Василиса Мелентьева, др.» (works shifted down one row in extraction)")
add_note(e, "scan 2026-10-28: «Василиса Мелентьева» moved to the morning, where it is printed")
for S in P:
    for w in S["works"]:
        if S["theater"].startswith("Новый") and w["work_title"] == "Вѣй":
            w["work_title"] = "Вій"
            add_note(S, "scan 2026-10-28: title «Вѣй» -> «Вій» (as printed)")
            print("p019", S["date_text"], S["session"], "Вѣй -> Вій")
print("p019 28 Dec Новый works:", [w["work_title"] for w in m["works"]], "/", [w["work_title"] for w in e["works"]])
if "--write" in sys.argv:
    for p, (d, fmt) in pages.items():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
