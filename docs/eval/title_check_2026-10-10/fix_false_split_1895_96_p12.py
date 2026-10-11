"""Merge a falsely split cell (issue #151 follow-up 13): repertoire_1895-96_pair012 s88 (morning, «Вава») + s89 (evening, «Взаимное обученіе», 1653 р. 40 к.),
Александринскій, 27 Среда (Dec 1895). The printed cell is ONE undivided cell with both lines and one figure (two blind readers, rcpt_107 and rcpt_138
readings of the same cell). Both sessions had been created by the issue #73 manual recovery. s88 becomes the single `unspecified` session with
both works and the figure; s89 is removed (later session ids on this page shift down by one).
uv run python docs/eval/title_check_2026-10-10/fix_false_split_1895_96_p12.py [--write]"""
import json, sys
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw" / "repertoire_1895-96_pair012.raw.json"
t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
for ind in (2, 4, 1, None):
    for ea in (False, True):
        for tr in ("", "\n"):
            if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
assert fmt
S = d["sessions"]; a, b = S[87], S[88]
assert a["works"] == [{"work_title": "Вава", "genre": "ком."}] and a["session"] == "morning" and not a["receipts_text"]
assert b["works"] == [{"work_title": "Взаимное обученіе", "genre": "вод."}] and b["session"] == "evening" and b["receipts_text"] == "1653 р. 40 к."
assert a["date_text"] == b["date_text"] and a["theater"] == b["theater"]
a["works"] = a["works"] + b["works"]; a["receipts_text"] = b["receipts_text"]; a["session"] = "unspecified"
a["_source"] = a["_source"] + "; merged with the following evening session 2026-10-11 (one undivided cell, issue #151 follow-up 13)"
del S[88]
print("merged:", json.dumps(a, ensure_ascii=False)[:300], "| sessions now", len(S))
if "--write" in sys.argv: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8"); print("WROTE")
