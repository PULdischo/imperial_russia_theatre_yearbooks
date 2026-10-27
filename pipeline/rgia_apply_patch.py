"""Apply a consistency pass's tag/rating changes to the tracked page triage.

    uv run python pipeline/rgia_apply_patch.py --dela 160,161

Reads  outputs/rgia_dela/<delo>/consistency_patch.jsonl   {"page", "set": {...}, "reason"}
Edits  docs/rgia/dela/<delo>.jsonl in place

Only the tag and rating fields may be changed (see docs/rgia/consistency_rules.md);
a patch touching anything else, or naming a page that is not in the дело, is
refused whole. "editorial" is recomputed from the ed_* sub-tags afterwards.

Register дела (Д. 189, 190) also have entry-level items, patched with --items:

    uv run python pipeline/rgia_apply_patch.py --dela 189,190 --items

Reads  outputs/rgia_dela/<delo>/items_consistency_patch.jsonl
       {"page", "entry_no", "content_start", "set": {...}, "reason"}
Edits  docs/rgia/dela/<delo>_items.jsonl in place

Each line must match exactly one entry by page + entry_no + the opening of
content_ru (entry numbers repeat across the register's separate blocks). Only the
tags may change (no relevance at entry level); otherwise the patch is refused whole.
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


def apply_items(delo):
    f = ROOT / "docs" / "rgia" / "dela" / f"{delo}_items.jsonl"
    pf = ROOT / "outputs" / "rgia_dela" / delo / "items_consistency_patch.jsonl"
    rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    patch = [json.loads(l) for l in pf.read_text(encoding="utf-8").splitlines() if l.strip()]
    targets = []
    for p in patch:
        hits = [r for r in rows if str(r["page"]) == str(p["page"])
                and r["entry_no"] == p["entry_no"]
                and r["content_ru"].startswith(p["content_start"])]
        bad = set(p["set"]) - set(SUB) - {"ballet"}
        if len(hits) != 1 or bad:
            print(f"Д. {delo} items: patch REFUSED (page {p['page']} no. {p['entry_no']}: "
                  f"{len(hits)} matches, fields {sorted(bad)})")
            return False
        targets.append((hits[0], p["set"]))
    before = {k: sum(bool(r[k]) for r in rows) for k in ("ballet",) + SUB}
    for r, upd in targets:
        r.update(upd)
    for r in rows:
        r["editorial"] = any(r[k] for k in SUB)
    after = {k: sum(bool(r[k]) for r in rows) for k in ("ballet",) + SUB}
    with open(f, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    diff = ", ".join(f"{k} {before[k]}->{after[k]}" for k in before if before[k] != after[k])
    print(f"Д. {delo} items: {len(patch)} entries changed | {diff or 'no count changes'}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dela", required=True)
    ap.add_argument("--items", action="store_true", help="patch the entry-level register items")
    a = ap.parse_args()
    fn = apply_items if a.items else apply
    raise SystemExit(0 if all([fn(d.strip()) for d in a.dela.split(",")]) else 1)


if __name__ == "__main__":
    main()
