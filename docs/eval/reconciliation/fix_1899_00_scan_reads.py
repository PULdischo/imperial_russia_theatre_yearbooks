"""1899-00 Repertoire: the one extraction error found by the blind read of every column, both cities (2026-10-30,
docs/eval/scan_audit/1899-00_scan_reads.csv), checked by Claude on ForUpload_1899-00_Repertoire.pdf (image index = pNNN).
Reconciliation ledger 1899-00-08.

Новый 2 Dec 1899 (p015), «Другъ Фритцъ, ком.» + «Лолотта, ком.»: «332 р. 36 к.» -> «333 р. 36 к.». The third digit is a
heavier 3 (rounded lower bowl, not a 2's flat base); with it the Новый drama line equals the printed 55,768.65 exactly.
RG 2026-10-30: "Yes, correct it". Crop: docs/eval/scan_audit/1899-00_rg_novyi_2dec.png.

Not here (kept as stored; both ballet lines are exact with them): Маріинскій 2 Feb 1900 «28?9 р. 70 к.» (stored 2839.70),
Большой 26 Dec 1899 «14?1 р. 38 к.» (stored 1401.38).

uv run python docs/eval/reconciliation/fix_1899_00_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (blind column read, 1899-00 reconciliation; RG)"


def load(pg):
    p = RAW / f"repertoire_1899-00_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: {msg}"


p, d, fmt = load("p015")
hits = [S for S in d["sessions"] if S["date_text"].split()[0] == "2" and S["theater"].startswith("Новый")
        and S["receipts_text"] == "332 р. 36 к."]
assert len(hits) == 1, len(hits)
S = hits[0]
assert S["works"][0]["work_title"].startswith("Другъ Фритцъ"), S
S["receipts_text"] = "333 р. 36 к."
note(S, "receipts «332 р. 36 к.» -> «333 р. 36 к.» (heavier third 3 read as 2)")
print("p015", S["date_text"], S["theater"], S["receipts_text"])
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
