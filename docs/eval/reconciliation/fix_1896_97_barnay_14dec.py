"""1896-97, Маріинскій, p. 13 (repertoire_1896-97_pair012): 14 Dec 1896, Barnay and Dumont guest performance («Uriel
Acosta, Trauerspiel.»), stored «3711 р.», print «3741 р. — к.». The third digit is a damaged sort (diagonal and stem, the
crossbar not inked), the same damage as Александринскій 26 Jan 1897 «646 р. 61 к.» (stored as a 4). Found by the blind
column read of 2026-10-29 (docs/eval/scan_audit/1896-97_scan_reads.csv); read on ForUpload_1896-97_Repertoire.pdf index 5
by Claude; RG 2026-10-29: "It's a 4". Ledger 1896-97.
uv run python docs/eval/reconciliation/fix_1896_97_barnay_14dec.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1896-97_pair012.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"][74]  # 0-based; event_id repertoire_1896-97_pair012__s075
old, new = "3711 р.", "3741 р. — к."
assert S["date_text"] == "14 Суббота." and S["theater"].startswith("Маріин") and S["receipts_text"] == old, S
assert S["annotation"].startswith("Gastspiel-Vorstellung des Herrn Ludwig Barnay"), S["annotation"]
S["receipts_text"] = new
note = f"scan 2026-10-29: receipts «{old}» -> «{new}» (damaged 4 read as 1 in extraction; blind column read; RG: a 4)"
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
print(S["date_text"], S["theater"], S["receipts_text"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
