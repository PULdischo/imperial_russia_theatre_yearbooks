"""1911-12 Repertoire, Малый 19 Apr 1912 (p050, printed p. 51): «Герцсгиня Паддуанскяя, др.» -- the letter after ц is a
broken о (zoom: docs/eval/scan_audit/1911-12_uncertain_readings_for_RG.png #5). RG 2026-11-12: "looks like a broken o to
me" -> «Герцогиня»; «Паддуанскяя» is a genuine print typo and stays. Same ruling as #2 («кэм.» = broken о).

uv run python docs/eval/reconciliation/fix_1911_12_gertsoginya.py [--write]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = [ROOT / "outputs/full_run/raw/repertoire_1911-12_p050.raw.json",
         ROOT / "outputs/repertoire_1911-12/raw_columnwise_repaired/repertoire_1911-12_p050.raw.json"]
NOTE = "scan 2026-11-12: «Герцсгиня» is a broken о (RG) -> «Герцогиня»"
for f in FILES:
    d = json.loads(f.read_text(encoding="utf-8"))
    hits = [(s, w) for s in d["sessions"] for w in s["works"] if w["work_title"] == "Герцсгиня Паддуанскяя"]
    assert len(hits) == 1, (f, len(hits))
    s, w = hits[0]
    w["work_title"] = "Герцогиня Паддуанскяя"
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + NOTE
    print(f.name, "->", w)
    if "--write" in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written" if "--write" in sys.argv else "dry run")
