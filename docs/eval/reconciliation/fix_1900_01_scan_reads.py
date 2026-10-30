"""1900-01 Repertoire: the one extraction error found by the blind read of every column, both cities (2026-10-30,
docs/eval/scan_audit/1900-01_scan_reads.csv), checked by Claude on ForUpload_1900-01_Repertoire.pdf (image index = pNNN).

Александринскій 10 Dec 1900 evening (p016), «Правда хорошо, а счастье лучше, ком.» + «Красный цвѣтокъ, драм. эт.»:
stored «1337 р. 37 к.», which is the next row's figure (11 Dec «Волшебная сказка»); the print reads «1284 р. 34 к.».
RG 2026-10-30: "Yes, correct it". Crop: docs/eval/scan_audit/1900-01_rg_alex_10dec.png.

Not here (kept as stored, medium-confidence readings of damaged type): Александринскій 12 Sep 1900 «16?7 р. 46 к.»
(stored 1617.46; Claude at 4x reads 1, a reader 4), 19 Nov 1900 morning «458 р. 5? к.» (stored 458.51, a reader 54).

uv run python docs/eval/reconciliation/fix_1900_01_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-30 (blind column read, 1900-01 reconciliation; RG)"


def load(pg):
    p = RAW / f"repertoire_1900-01_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: {msg}"


p, d, fmt = load("p016")
hits = [S for S in d["sessions"] if S["date_text"].split()[0] == "10" and S["theater"].startswith("Александрин")
        and S["session"] == "evening" and S["receipts_text"] == "1337 р. 37 к."]
assert len(hits) == 1, len(hits)
S = hits[0]
assert S["works"][0]["work_title"].startswith("Правда хорошо"), S
S["receipts_text"] = "1284 р. 34 к."
note(S, "receipts «1337 р. 37 к.» -> «1284 р. 34 к.» (the next row's figure had been copied)")
print("p016", S["date_text"], S["theater"], S["session"], S["receipts_text"])
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
