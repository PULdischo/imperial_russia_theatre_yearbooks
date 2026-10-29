"""1897-98, Маріинскій: two kinds of fix found by the blind column read of 2026-10-29 (docs/eval/scan_audit/1897-98_scan_reads.csv,
1897-98_title_diffs.csv) and checked on the scan by Claude. RG 2026-10-29: "go ahead".

1. 1 Feb 1898 (pair018, p. 18): the Русское Театральное Общество gala is printed in the morning half of a split cell, labelled
   «утро» in the Маріинскій column (the evening half, «веч.», is a dash and already stored as such). Session «unspecified» ->
   «morning».
2. The visiting German opera troupe's opera acts, printed as the second line of the bill but stored only in the annotation
   (the same fix as 23 Mar, fix_1897_98_hugenotten_23mar.py): 12 Mar «2-ter Akt aus der Oper Der fliegende Holländer.»,
   19 Mar «1-ter Akt aus der Oper Die Walküre.», 20 Mar «3-ter Akt (1-es Bild) aus der Oper Die Meistersinger von Nürnberg.»,
   22 Mar evening «3-ter Akt aus der Oper Die Walküre.». Each moved to a work after the opera (printed order); the annotation
   held nothing else. The 15 Mar and 22 Mar morning charity matinées are NOT changed (their acts and «Concert-Abtheilung.»
   stay in the annotation; event_labels.csv, RG #141, labels them German opera).
uv run python docs/eval/reconciliation/fix_1897_98_german_acts_and_1feb.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
WRITE = "--write" in sys.argv


def load(page):
    p = RAW / f"repertoire_1897-98_{page}.raw.json"
    t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"cannot reproduce the formatting of {p}")


def note(S, text):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + "scan 2026-10-29: " + text


def save(p, d, f):
    if WRITE:
        p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")


p, d, f = load("pair018")
S = d["sessions"][15]
assert S["date_text"] == "1 Воскресенье." and S["theater"].startswith("Маріин") and S["session"] == "unspecified", S
assert S["annotation"] == "Въ пользу Русскаго Театральнаго Общества.", S
E = d["sessions"][59]
assert E["date_text"] == "1 Воскресенье." and E["theater"].startswith("Маріин") and E["session"] == "evening" and not E["works"], E
S["session"] = "morning"
note(S, "session «unspecified» -> «morning» (cell labelled «утро»; the «веч.» half is a dash)")
save(p, d, f); print("pair018", S["date_text"], S["session"])


def move(S, dt, sess, opera, act):
    assert S["date_text"] == dt and S["theater"].startswith("Маріин") and S["session"] == sess, S
    assert S["annotation"] == act, S["annotation"]
    assert [w["work_title"] for w in S["works"]] == [opera], S["works"]
    S["annotation"] = None
    S["works"].append({"work_title": act, "genre": None})
    note(S, f"«{act}» moved from the annotation to a work (printed as the bill's second line)")
    print(dt, sess, [w["work_title"] for w in S["works"]])


p, d, f = load("pair020")
move(d["sessions"][30], "12 Четвергъ.", "unspecified", "Das Heimchen am Herd", "2-ter Akt aus der Oper Der fliegende Holländer.")
save(p, d, f)
p, d, f = load("pair022")
move(d["sessions"][13], "19 Четвергъ.", "unspecified", "A basso Porto", "1-ter Akt aus der Oper Die Walküre.")
move(d["sessions"][15], "20 Пятница.", "unspecified", "Das Heimchen am Herd",
     "3-ter Akt (1-es Bild) aus der Oper Die Meistersinger von Nürnberg.")
move(d["sessions"][19], "22 Воскресенье.", "evening", "A basso Porto", "3-ter Akt aus der Oper Die Walküre.")
save(p, d, f)
print("WROTE" if WRITE else "DRY RUN", RAW)
