"""1906-07 Repertoire, Маріинскій 29 Apr 1907 (p044, idx 21): the cell prints ONE item,
«Очарованный лѣсъ, изъ бал. Корсаръ (Le jardin animé).» (blind column read 2026-10-29,
docs/eval/scan_audit/1906-07_scan_reads.csv; the SP ballet review's closing-night paragraph agrees). The extraction
split it into two works, «Очарованный лѣсъ» [изъ бал.] and «Корсаръ (Le jardin animé)» [no genre], and the research
layer then counted the first as a scene of the separate ballet «Очарованный лѣсъ». RG 2026-10-30: "This is an excerpt
of Corsaire". Ledger 1906-07-20.

The two items become one (genre none, as for «Сцена изъ бал. Корсаръ»); the bill's later items move up one place
(performance ids __w3/__w4 -> __w2/__w3; nothing refers to them by id).

uv run python docs/eval/reconciliation/fix_1906_07_corsaire_29apr.py [--raw-dir DIR] [--write]"""
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


p, d, fmt = load("p044"); S = d["sessions"][21]
assert S["date_text"] == "29 Воскрес." and S["theater"].startswith("Маріин") and S["receipts_text"] == "3443 р. 80 к.", S
w = S["works"]
assert [(x["work_title"], x["genre"]) for x in w[:2]] == [("Очарованный лѣсъ", "изъ бал."), ("Корсаръ (Le jardin animé)", None)], w
S["works"] = [{"work_title": "Очарованный лѣсъ, изъ бал. Корсаръ (Le jardin animé)", "genre": None}] + w[2:]
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + (
    f"{TAG}: works 1-2 «Очарованный лѣсъ» [изъ бал.] + «Корсаръ (Le jardin animé)» -> one item "
    "«Очарованный лѣсъ, изъ бал. Корсаръ (Le jardin animé)» (printed as one)")
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print([x["work_title"] for x in S["works"]])
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
