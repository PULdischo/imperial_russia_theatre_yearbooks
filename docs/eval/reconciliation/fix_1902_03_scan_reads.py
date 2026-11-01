"""1902-03 Repertoire: extraction error found by the blind read of every column, both cities (2026-10-31,
docs/eval/scan_audit/1902-03_scan_reads.csv) and checked by Claude on ForUpload_1902-03_Repertoire.pdf (page index = pNNN).
Reconciliation ledger 1902-03-02. Applied on RG's ruling 2026-10-31 ("Yes, fix both").

Александринскій 14 Dec 1902 (p016), «Волки и овцы», charity for the Народный домъ имени А. Н. Островскаго: the cell
prints NO receipts. The stored «659 р. — к.» is the figure of the 15 Dec student matinée («Сонъ въ лѣтнюю ночь»)
directly below it in the same column. With it removed, every SP charity event without printed receipts is outside
the printed totals, as in other seasons.

The other fix of the same ruling, Новый 10 Jan 1903 «218 р. 42 е.» (е. printed for к.), is a kopeck-parse row in
pipeline/research_corrections/receipts_print_typos.csv: the raw text is the print and stays as it is.

uv run python docs/eval/reconciliation/fix_1902_03_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-31 (blind column read, 1902-03 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1902-03_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
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


p, d, f = load("p016")
alex = [S for S in d["sessions"] if S["theater"].startswith("Александрин")]
hits = [S for S in alex if S["date_text"].split()[0] == "14" and S["receipts_text"] == "659 р. — к."]
assert len(hits) == 1 and hits[0]["works"][0]["work_title"] == "Волки и овцы", hits
# the 15 Dec matinée below prints the same figure
assert [S for S in alex if S["date_text"].split()[0] == "15" and S.get("session") == "morning"
        and S["receipts_text"] == "659 р. — к."]
S = hits[0]
S["receipts_text"] = None
note(S, "receipts «659 р. — к.» removed: the charity cell prints none; the figure is the 15 Dec matinée's directly below")
save(p, d, f); print("p016", S["date_text"], S["theater"], "receipts -> None")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
