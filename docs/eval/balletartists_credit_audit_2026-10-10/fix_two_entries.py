"""Credit-row fixes for two entries whose TEXT is right as printed but whose rows are not (issue #150 follow-up).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_two_entries.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_two_entries.py --write

Both read on the scan by me (2026-10-10), summary text unchanged:
  * balletartists_1897-98_MSK_p005__e010 (no. 16 Воронцовъ): printed «Въ 14 балетахъ — 48; въ 13 балетахъ — 60;
    въ 1 драмѣ--1. Всего — 109 разъ.» Two «балетахъ» sentences (the second is very likely a printer's slip for
    «операхъ», but it is printed so). The model merged them into ONE row of 108; they become two rows, 48 and 60.
  * balletartists_1895-96_MSK_p003__e021 (no. 95 Рославлева): printed «Въ 7 балетахъ—20; въ 2 операхъ—3. Кромѣ того,
    въ С.-Петербургѣ въ 3 балетахъ—9. Всего — 32 раза.» The rows omitted the second city's block; a row of 9 is added
    before «Всего» (20 + 3 + 9 = 32).
Rows are changed in place on the ordered-pair view of the file (rawjson_pairs.py); no entry is added or removed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402

RAW = HERE.parent.parent.parent / "outputs" / "full_run" / "raw"


def counts(rows):
    return [(r.get("credit_type"), r.get("label"), r.get("count")) for r in rows if r.get("credit_type") == "category_totals"]


def edit(eid, fn, write):
    page = eid.split("__e")[0]
    path = RAW / f"{page}.raw.json"
    doc = rp.loads(path.read_text(encoding="utf-8"))
    e = doc.get("entries")[int(eid.split("__e")[1]) - 1]
    before = counts(e.get("credits"))
    fn(e)
    after = counts(e.get("credits"))
    print(eid[-28:], "\n   before:", before, "\n   after: ", after)
    if write:
        path.write_text(rp.dumps(doc), encoding="utf-8")


def fix_voroncov(e):
    rows = e.get("credits")
    i = next(k for k, r in enumerate(rows) if r.get("label") == "балетахъ" and r.get("count") == 108)
    second = rp.Obj(list(rows[i]))
    rows[i].set("count", 48)
    second.set("count", 60)
    rows.insert(i + 1, second)


def fix_roslavleva(e):
    rows = e.get("credits")
    assert not any(r.get("credit_type") == "category_totals" and r.get("label") == "балетахъ" and r.get("count") == 9 for r in rows)
    i = next(k for k, r in enumerate(rows) if r.get("label") == "Всего")
    first_ballet = next(r for r in rows if r.get("credit_type") == "category_totals" and r.get("label") == "балетахъ")
    new = rp.Obj(list(first_ballet))
    new.set("count", 9)
    rows.insert(i, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    edit("balletartists_1897-98_MSK_p005__e010", fix_voroncov, a.write)
    edit("balletartists_1895-96_MSK_p003__e021", fix_roslavleva, a.write)
    print("WROTE" if a.write else "DRY RUN (nothing written)")


if __name__ == "__main__":
    main()
