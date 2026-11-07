"""Raw fix, 2026-11-06: «Und Pippa tanzt! ein Glasettenmärchen» -> «... Glassettenmärchen» (repertoire_1905-06_p034).

The print (Александринскій, 2 and 3 Mar 1906, printed p. 118) reads «Und Pippa tanzt! ein Glassetten-märchen.» in both
cells: double «s», the word broken at the line end. The extraction dropped one «s». Scan read by Claude 2026-11-06 (full-res
image embedded in ForUpload_1905-06_Repertoire.pdf, page index 34). The print's own «Glassetten» for Hauptmann's
«Glashüttenmärchen» stays verbatim here; RG ruled it a print slip for the research layer only (genuine_print_typos.md).

Usage: uv run python docs/eval/raw_fix_pippa_glassetten_2026-11-06.py <raw_dir> [--dry-run]
"""
import json
import sys
from pathlib import Path

OLD, NEW = "Und Pippa tanzt! ein Glasettenmärchen", "Und Pippa tanzt! ein Glassettenmärchen"
NOTE = ("2026-11-06: «Glasettenmärchen» -> «Glassettenmärchen», the print has double s («Glassetten-märchen»); "
        "scan read by Claude, RG's Pippa ruling")

raw_dir, dry = Path(sys.argv[1]), "--dry-run" in sys.argv
path = raw_dir / "repertoire_1905-06_p034.raw.json"
data = json.loads(path.read_text(encoding="utf-8"))
n = 0
for ev in data["sessions"]:
    for w in ev.get("works") or []:
        if w.get("work_title") == OLD:
            w["work_title"] = NEW
            ev["_fix_note"] = (ev["_fix_note"] + "; " if ev.get("_fix_note") else "") + NOTE
            n += 1
            print(f"  {ev.get('date_text')!r}: {OLD!r} -> {NEW!r}")
if n != 2:
    raise SystemExit(f"expected 2 rows, found {n}; nothing written")
if not dry:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{n} rows {'(dry run, not written)' if dry else 'written'}: {path}")
