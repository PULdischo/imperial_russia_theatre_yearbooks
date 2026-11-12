"""1911-12 Repertoire, Большой 15 Dec 1911 (p024, printed p. 25): the print has «Псковитяака, оп.» -- a printed а where н
belongs (zoom: docs/eval/scan_audit/1911-12_uncertain_readings_for_RG.png #4). RG 2026-11-12: "yes, it's def a printed а, so
store as typo". Stored verbatim; pipeline/entity_curation/work_title_aliases.csv matches it to «Псковитянка» (same work).

uv run python docs/eval/reconciliation/fix_1911_12_pskovityaaka.py [--write]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = [ROOT / "outputs/full_run/raw/repertoire_1911-12_p024.raw.json",
         ROOT / "outputs/repertoire_1911-12/raw_columnwise_repaired/repertoire_1911-12_p024.raw.json"]
NOTE = "scan 2026-11-12: printed «Псковитяака» (print typo, RG); was «Псковитянка»"
for f in FILES:
    d = json.loads(f.read_text(encoding="utf-8"))
    hits = [(s, w) for s in d["sessions"] if s["date_text"].startswith("15 ") and s["theater"].startswith("Большой")
            for w in s["works"] if w["work_title"] == "Псковитянка"]
    assert len(hits) == 1, (f, len(hits))
    s, w = hits[0]
    w["work_title"] = "Псковитяака"
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + NOTE
    print(f.name, "->", w)
    if "--write" in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written" if "--write" in sys.argv else "dry run")
