"""1911-12 Repertoire, Маріинскій 13 Nov 1911 morning (p015, printed p. 16): the print has «Морякъ скиталецъ, оп.» with a
space (and a faint raised speck), no hyphen. The sweep checker had kept «Морякъ-скиталецъ» to match the other 1911-12
printings (its report: "same form as p011"); the blind column read (docs/eval/scan_audit/1911-12_scan_reads.csv) reads it
without the hyphen, the other eight 1911-12 printings with one. Zoom: docs/eval/scan_audit/1911-12_uncertain_readings_for_RG.png
#3. RG 2026-11-12: "yes no hyphen for this one". Same work either way (raw text only).

uv run python docs/eval/reconciliation/fix_1911_12_moryak_hyphen.py [--write]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = [ROOT / "outputs/full_run/raw/repertoire_1911-12_p015.raw.json",
         ROOT / "outputs/repertoire_1911-12/raw_columnwise_repaired/repertoire_1911-12_p015.raw.json"]
NOTE = "scan 2026-11-12: printed «Морякъ скиталецъ» without hyphen (RG); was «Морякъ-скиталецъ»"
for f in FILES:
    d = json.loads(f.read_text(encoding="utf-8"))
    hits = [(s, w) for s in d["sessions"] if s["date_text"].startswith("13 ") and s["theater"].startswith("Маріинскій")
            and s["session"] == "morning" for w in s["works"] if w["work_title"] == "Морякъ-скиталецъ"]
    assert len(hits) == 1, (f, len(hits))
    s, w = hits[0]
    w["work_title"] = "Морякъ скиталецъ"
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + NOTE
    print(f.name, "->", w)
    if "--write" in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written" if "--write" in sys.argv else "dry run")
