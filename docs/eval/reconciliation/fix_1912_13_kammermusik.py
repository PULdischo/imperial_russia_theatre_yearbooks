"""1912-13 Repertoire, Михайловскій 4 Apr 1913 (p049, printed p. 50): the print has «Kammermusiк, Lustspied.» -- the last
letter of Kammermusik is an x-height, Cyrillic-shaped к (wrong fount; the 3 Apr printing in the same column has a Latin k).
Found by the D3 blind column reads (zoom: docs/eval/scan_audit/1912-13_kammermusik_for_RG.png, checked by Claude).
RG 2026-11-26: "store cyrillic к in raw, use latin in research". Raw edited only; production is rebuilt by the 1912-13 C build. Raw stores the Cyrillic к verbatim;
pipeline/entity_curation/work_title_aliases.csv matches it to «Kammermusik» (same work, Latin title in research).

uv run python docs/eval/reconciliation/fix_1912_13_kammermusik.py [--write]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = [ROOT / "outputs/full_run/raw/repertoire_1912-13_p049.raw.json",
         ROOT / "outputs/repertoire_1912-13/raw_columnwise_repaired/repertoire_1912-13_p049.raw.json",
         ROOT / "outputs/integration_1912-13/raw/repertoire_1912-13_p049.raw.json"]
OLD, NEW = "Kammermusik", "Kammermusiк"  # final letter U+043A CYRILLIC SMALL LETTER KA
NOTE = "scan 2026-11-26 (D3): printed «Kammermusiк» with a wrong-fount Cyrillic к (RG: Cyrillic in raw, Latin in research); was «Kammermusik»"
for f in FILES:
    d = json.loads(f.read_text(encoding="utf-8"))
    hits = [(s, w) for s in d["sessions"] if s["date_text"].startswith("4 ") and s["theater"].startswith("Михайловскій")
            for w in s["works"] if w["work_title"] == OLD]
    assert len(hits) == 1, (f, len(hits))
    s, w = hits[0]
    w["work_title"] = NEW
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + NOTE
    print(f.name, "->", w)
    if "--write" in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")  # same compact form as the file on disk
print("written" if "--write" in sys.argv else "dry run")
