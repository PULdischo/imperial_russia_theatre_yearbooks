"""1902-03 Repertoire, Михайловскій 2 Dec 1902 (p014, event repertoire_1902-03_p014__s032): «Джентльменъ» -> «Джентльмэнъ».
The title audit's blind reader read «Джентльмэнъ, ком.» (docs/eval/scan_audit/1902-03_title_reads.csv n26; crop
1902-03_rg_mikh_2dec_dzhentlmen.png); the cell is soft on the scan, the letter after м has a closed right side and a short bar.
The season's four other Михайловскій cells print «Джентльмэнъ». RG 2026-10-31: «э (store «Джентльмэнъ»)». Title only.

uv run python docs/eval/reconciliation/fix_1902_03_dzhentlmen_2dec.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1902-03_p014.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt, p
S = d["sessions"][31]
assert S["date_text"].split()[0] == "2" and S["theater"].startswith("Михайлов"), S
w = S["works"][0]; assert (w["work_title"], w["genre"]) == ("Джентльменъ", "ком."), w
w["work_title"] = "Джентльмэнъ"
S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + \
    "scan 2026-10-31 (1902-03 title audit n26): «Джентльменъ» -> «Джентльмэнъ» (RG: э)"
if "--write" in sys.argv:
    p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(S["date_text"], S["theater"], [x["work_title"] for x in S["works"]], "WROTE" if "--write" in sys.argv else "DRY RUN")
