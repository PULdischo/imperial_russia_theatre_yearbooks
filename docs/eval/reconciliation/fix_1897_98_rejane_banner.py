"""1897-98, Александринскій, p. 8 (repertoire_1897-98_pair008): 25 Oct 1897 and 26 Oct 1897 (morning). The cells print a
banner «Représentation de M-me Réjane.» above the work (blind column read 2026-10-29, docs/eval/scan_audit/1897-98_scan_reads.csv:
headings «Représentation de M-me Réjane.», works «La Douloureuse, com.» / «Sapho, pièce.»), but the extraction ran the banner
into the title. Moved to the annotation; the visiting-troupe rule for this French wording is in build_research_model.py
(VISITING_ANNOTATION_RULES). The 1897-98 SP season statistics give the two nights their own line, «Спектаклей г-жи Режанъ 2».
RG 2026-10-29: "Yes, relabel". Ledger 1897-98-03.
uv run python docs/eval/reconciliation/fix_1897_98_rejane_banner.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
p = RAW / "repertoire_1897-98_pair008.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
BANNER = "Représentation de M-me Réjane."
for i, dt, sess, title in ((17, "25 Суббота.", "unspecified", "La Douloureuse"), (23, "26 Воскрес.", "morning", "Sapho")):
    S = d["sessions"][i]
    assert S["date_text"] == dt and S["session"] == sess and S["theater"].startswith("Александ"), S
    assert S["annotation"] is None and S["receipts_text"] is None, S
    assert len(S["works"]) == 1 and S["works"][0]["work_title"] == BANNER + " " + title, S["works"]
    S["annotation"] = BANNER
    S["works"][0]["work_title"] = title
    note = f"scan 2026-10-29: banner «{BANNER}» moved from the title to the annotation (RG: relabel as Réjane's troupe)"
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + note
    print(S["date_text"], S["session"], S["annotation"], S["works"])
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
