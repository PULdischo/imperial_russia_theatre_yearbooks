"""Apply a consistency pass's tag/rating changes to the tracked page triage.

    uv run python pipeline/rgia_apply_patch.py --dela 160,161

Reads  outputs/rgia_dela/<delo>/consistency_patch.jsonl   {"page", "set": {...}, "reason"}
Edits  docs/rgia/dela/<delo>.jsonl in place

Only the tag and rating fields may be changed (see docs/rgia/consistency_rules.md);
a patch touching anything else, or naming a page that is not in the дело, is
refused whole. "editorial" is recomputed from the ed_* sub-tags afterwards.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ("ed_contributors", "ed_illustrations", "ed_print_finance", "ed_editors")
ALLOWED = set(SUB) | {"ballet", "relevance"}


def counts(rows):
    c = {k: sum(bool(r[k]) for r in rows) for k in ("ballet",) + SUB}
    c.update(Counter(r["relevance"] for r in rows))
    return c


def apply(delo):
    tri = ROOT / "docs" / "rgia" / "dela" / f"{delo}.jsonl"
    pf = ROOT / "outputs" / "rgia_dela" / delo / "consistency_patch.jsonl"
    rows = [json.loads(l) for l in tri.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = {r["page"]: r for r in rows}
    patch = [json.loads(l) for l in pf.read_text(encoding="utf-8").splitlines() if l.strip()]
    for p in patch:
        bad = set(p["set"]) - ALLOWED
        if bad or p["page"] not in by:
            print(f"Д. {delo}: patch REFUSED (page {p['page']}, fields {sorted(bad)})")
            return False
        if "relevance" in p["set"] and p["set"]["relevance"] not in ("high", "medium", "low"):
            print(f"Д. {delo}: patch REFUSED (page {p['page']} relevance)")
            return False
    before = counts(rows)
    for p in patch:
        by[p["page"]].update(p["set"])
    for r in rows:
        r["editorial"] = any(r[k] for k in SUB)
    after = counts(rows)
    with open(tri, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    diff = ", ".join(f"{k} {before.get(k, 0)}->{after.get(k, 0)}" for k in
                     ("ballet",) + SUB + ("high", "medium", "low") if before.get(k, 0) != after.get(k, 0))
    print(f"Д. {delo}: {len(patch)} pages changed | {diff or 'no count changes'}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dela", required=True)
    a = ap.parse_args()
    raise SystemExit(0 if all([apply(d.strip()) for d in a.dela.split(",")]) else 1)


if __name__ == "__main__":
    main()
