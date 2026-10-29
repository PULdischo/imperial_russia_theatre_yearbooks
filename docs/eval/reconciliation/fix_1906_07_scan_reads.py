"""1906-07 Repertoire: extraction errors found by the blind read of all six theater columns
(2026-10-29, docs/eval/scan_audit/1906-07_scan_reads.csv) and checked by Claude on ForUpload_1906-07_Repertoire.pdf
(page index = pNNN). Reconciliation ledger 1906-07-07 and -11. RG 2026-10-29: "Yes, apply both".

1. Александринскій, 19 Nov 1906 matinée (p014, idx 20), «Спектакль для учащейся молодежи.»: the cell prints
   «625 р. 75 к.» under «Карантинъ, опера-вод.»; the extraction stored no receipts.
2. Большой, 30 Dec 1906 (p023, idx 18-19): «Аида, оп.» «1420 р. 28 к.» is printed in the УТРО half and the ВЕЧЕРЪ half
   is a dash; the extraction put the dark row in the morning and «Аида» in the evening. Only the two session labels
   swap; both rows keep their places (event ids unchanged, no row shift).

uv run python docs/eval/reconciliation/fix_1906_07_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-29 (blind column read, 1906-07 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1906-07_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
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


# 1. Александринскій 19 Nov 1906 matinée
p, d, f = load("p014"); S = d["sessions"][20]
assert S["date_text"] == "19 Воскрес." and S["session"] == "morning" and S["theater"].startswith("Александр"), S
assert S["receipts_text"] is None and S["works"][-1]["work_title"] == "Карантинъ", S
S["receipts_text"] = "625 р. 75 к."; note(S, "receipts None -> «625 р. 75 к.» (printed under the last work; dropped)")
save(p, d, f); print("p014", S["date_text"], S["session"], S["receipts_text"])

# 2. Большой 30 Dec 1906
p, d, f = load("p023"); M, E = d["sessions"][18], d["sessions"][19]
for X in (M, E):
    assert X["date_text"] == "30 Суббота." and X["theater"].startswith("Большой"), X
assert M["session"] == "morning" and M["is_dark"] and not M["works"], M
assert E["session"] == "evening" and E["works"][0]["work_title"] == "Аида" and E["receipts_text"] == "1420 р. 28 к.", E
M["session"] = "evening"; note(M, "session morning -> evening (the ВЕЧЕРЪ half is the dash)")
E["session"] = "morning"; note(E, "session evening -> morning («Аида» is printed in the УТРО half)")
save(p, d, f); print("p023", M["session"], "dark;", E["session"], E["works"][0]["work_title"])

print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
