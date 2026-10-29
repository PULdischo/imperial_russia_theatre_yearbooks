"""1897-98: six Repertoire cells corrected from the scans, found by the blind column read of 2026-10-29
(docs/eval/scan_audit/1897-98_scan_reads.csv, 7 agents, every date x session x theatre incl. dashes) and each read again by
Claude on ForUpload_1897-98_Repertoire.pdf before any change. Ledger 1897-98.

1. 10 Sep 1897 Маріинскій «Спящая красавица»: «2158 р. 43 к.» -> «2158 р. 45 к.». The last kopeck digit has the flat,
   flagged top of the 5s in «3352 р. 55 к.» two rows above, not the round top of the 3 in «3604 р. 30 к.»
   (docs/eval/scan_audit/1897-98_mariinsky_10sep_kopecks.jpeg). With 45 the SP «Балетныхъ» line is exact (120,913.66).
2. 16 Nov 1897 Маріинскій «Дочь микадо»: the heading «Бенефисъ г-жи Куличевской.» was not captured. The season review
   (SP ballet, p014) names the benefit; footnote 4 of the stats page counts 3 ballet benefits (with it: 7 Jan, 8 Feb, 16 Nov).
3. 13 Nov 1897 Михайловскій: second work «Le Bésique chinois, com.» not captured (print: «Le Maître de Forges, pièce. /
   Le Bésique chinois, com.»). Appended after the first work, so no earlier work changes position.
4. 21 Nov 1897 Александринскій (Аполлонскій benefit): «Германи» -> «Гернани» (Hugo, Hernani; the Михайловскій prints the
   same title on 3 and 10 Dec).
5./6. 26 and 27 Jan 1898 Михайловскій: the print has «Margot, com. / Une Innocente, com.»; the 2026-09-25 reconstruction
   repeated the 19-22 Jan bill «Les 3 Filles de Mr. Dupont / Villégiature». Receipts were right and are unchanged.

uv run python docs/eval/reconciliation/fix_1897_98_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
WRITE = "--write" in sys.argv
NOTE = "scan 2026-10-29 (1897-98 blind column read, reconciliation): "


def load(page):
    p = RAW / f"repertoire_1897-98_{page}.raw.json"
    t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"cannot reproduce the formatting of {p}")


def note(S, text):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + NOTE + text


def save(p, d, fmt):
    if WRITE:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")


# 1. 10 Sep 1897, Маріинскій (pair002, p. 3)
p, d, f = load("pair002")
S = d["sessions"][90]
assert S["date_text"] == "10 Среда." and S["theater"].startswith("Маріин") and S["receipts_text"] == "2158 р. 43 к.", S
S["receipts_text"] = "2158 р. 45 к."
note(S, "receipts «2158 р. 43 к.» -> «2158 р. 45 к.» (kopeck 5 read as 3)")
save(p, d, f); print("pair002", S["date_text"], S["theater"], S["receipts_text"])

# 2.-4. pair010 (pp. 10-11)
p, d, f = load("pair010")
S = d["sessions"][55]
assert S["date_text"] == "16 Воскресенье" and S["theater"].startswith("Маріин") and S["annotation"] is None, S
assert [w["work_title"] for w in S["works"]] == ["Дочь микадо"], S
S["annotation"] = "Бенефисъ г-жи Куличевской."
note(S, "heading «Бенефисъ г-жи Куличевской.» added (not captured)")
print("pair010", S["date_text"], S["theater"], S["annotation"])

S = d["sessions"][63]
assert S["date_text"] == "13 Четверг." and S["theater"].startswith("Михайл"), S
assert [w["work_title"] for w in S["works"]] == ["Le Maître de Forges"], S
S["works"].append({"work_title": "Le Bésique chinois", "genre": "com."})
note(S, "second work «Le Bésique chinois, com.» added (not captured)")
print("pair010", S["date_text"], S["theater"], [w["work_title"] for w in S["works"]])

S = d["sessions"][23]
assert S["date_text"] == "21 Пятница." and S["theater"].startswith("Александ"), S
assert S["works"] == [{"work_title": "Германи", "genre": "др."}], S
S["works"][0]["work_title"] = "Гернани"
note(S, "title «Германи» -> «Гернани»")
save(p, d, f); print("pair010", S["date_text"], S["theater"], S["works"])

# 5.-6. pair016 (pp. 16-17)
p, d, f = load("pair016")
for i, dt in ((91, "26 Понед."), (95, "27 Вторникъ.")):
    S = d["sessions"][i]
    assert S["date_text"] == dt and S["theater"].startswith("Михайл"), S
    assert [w["work_title"] for w in S["works"]] == ["Les 3 Filles de Mr. Dupont", "Villégiature"], S
    S["works"] = [{"work_title": "Margot", "genre": "com."}, {"work_title": "Une Innocente", "genre": "com."}]
    note(S, "works «Les 3 Filles de Mr. Dupont / Villégiature» (copied from the previous bill) -> «Margot / Une Innocente»")
    print("pair016", S["date_text"], S["theater"], [w["work_title"] for w in S["works"]])
save(p, d, f)
print("WROTE" if WRITE else "DRY RUN", RAW)
