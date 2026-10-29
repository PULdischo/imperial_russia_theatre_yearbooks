"""1903-04 Repertoire: extraction errors found by the blind read of the Большой, Новый and Маріинскій columns
(2026-10-29, docs/eval/scan_audit/1903-04_scan_reads.csv) and checked by Claude on ForUpload_1903-04_Repertoire.pdf
(page index = pNNN). Reconciliation ledger 1903-04.

1. Маріинскій, 19 Apr 1904 (p034, idx 7): «Садко, оп.» «1520 р. 60 к.» -> «1530 р. 60 к.» (the third digit is a blotted 3;
   with it the SP opera line is exact to the kopeck).
2. Большой, 5 Feb 1904 matinée (p027, idx 17): «Золотая рыбка, бал.» «1705 р. 55 к.» -> «1705 р. 56 к.» (damaged last
   digit, closed round body of a 6; with it the Moscow ballet line is exact to the kopeck).
3. Новый, 17-18 Jan 1904 (p023, idx 29-30): 17 Jan is blank in the print; 18 Jan is divided, УТРО «Дѣвичій переполохъ, ком.»
   403 р. 33 к., ВЕЧ. «Травіата, оп.» 1206 р. 15 к. The extraction put the matinée on 17 Jan. The two rows keep their places
   (event ids unchanged) and take the right date/session; the dark 17 Jan is appended at the end of the array (no row shift).

uv run python docs/eval/reconciliation/fix_1903_04_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-29 (blind column read, 1903-04 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1903-04_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: {msg}"


def save(p, d, fmt):
    if "--write" in sys.argv:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")


# 1. Маріинскій 19 Apr 1904
p, d, f = load("p034"); S = d["sessions"][7]
assert S["date_text"] == "19 Понед." and S["theater"].startswith("Маріин") and S["receipts_text"] == "1520 р. 60 к.", S
assert S["works"][0]["work_title"] == "Садко", S
S["receipts_text"] = "1530 р. 60 к."; note(S, "receipts «1520 р. 60 к.» -> «1530 р. 60 к.» (blotted 3 read as 2)")
save(p, d, f); print("p034", S["date_text"], S["receipts_text"])

# 2. Большой 5 Feb 1904 matinée
p, d, f = load("p027"); S = d["sessions"][17]
assert S["date_text"] == "5 Четвергъ." and S["session"] == "morning" and S["theater"].startswith("Большой"), S
assert S["works"][0]["work_title"] == "Золотая рыбка" and S["receipts_text"] == "1705 р. 55 к.", S
S["receipts_text"] = "1705 р. 56 к."; note(S, "receipts «1705 р. 55 к.» -> «1705 р. 56 к.» (damaged 6 read as 5)")
save(p, d, f); print("p027", S["date_text"], S["receipts_text"])

# 3. Новый 17/18 Jan 1904
p, d, f = load("p023"); ss = d["sessions"]; M, E = ss[29], ss[30]
assert M["theater"].startswith("Новый") and E["theater"].startswith("Новый")
assert M["date_text"] == "17 Суббота." and M["works"][0]["work_title"] == "Дѣвичій переполохъ", M
assert M["receipts_text"] == "403 р. 33 к." and M["session"] == "unspecified", M
assert E["date_text"] == "18 Воскрес." and E["works"][0]["work_title"] == "Травіата", E
assert E["receipts_text"] == "1206 р. 15 к." and E["session"] == "unspecified", E
M.update(date_text="18 Воскрес.", session="morning"); note(M, "date «17 Суббота.» -> «18 Воскрес.», session -> morning (УТРО)")
E["session"] = "evening"; note(E, "session -> evening (ВЕЧ.)")
assert not [S for S in ss if S["date_text"] == "17 Суббота." and S["theater"].startswith("Новый")]
ss.append({"date_text": "17 Суббота.", "month_text": None, "year_text": None, "session": "unspecified",
           "theater": M["theater"], "is_dark": True, "receipts_text": None, "annotation": None, "works": [],
           "_fix_note": f"{TAG}: blank cell in the print; added at the end of the array (no row shift)"})
save(p, d, f); print("p023", len(ss), "sessions")

print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
