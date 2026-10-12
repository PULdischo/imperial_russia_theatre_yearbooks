#!/usr/bin/env python3
"""Apply scan-verified transcription corrections to the merged review text.

Why this exists as a re-runnable step rather than a hand-edit
-------------------------------------------------------------
The 2026-10-07 mixed-script repairs were applied directly to
`merged_full/review_block.csv` after the merge, which meant a re-merge
silently discarded them -- the lesson recorded at the time was "a re-merge
will NOT reproduce it, always diff a rebuild". This script closes that gap:
the corrections live in a CSV under docs/eval/, and rebuilding the review
text layer is `merge, then run this`. Running it twice is a no-op.

These are NOT rules and NOT a character mapping. Every row was taken by
looking at the page -- see the `evidence` column, and
docs/eval/review_caption_quality.md for why the caption layer needs them.
A correction here restores what the volume actually prints; it never
normalises away a spelling the print really carries. (`Талорачва` in a
p005 caption against `Толорагва` in the p020 body is genuine source
variation and is deliberately absent from the table.)

It also restores the hand-verified `printed_folio` values, for the same
reason and from the same kind of table. `parse_reviews.py` already applies
docs/review_folio_corrections.csv at parse time, but the merged page table
is assembled from several views after that, and the view that can actually
see the folio is not always the one the selector keeps -- so the correction
has to be re-asserted here too.

    uv run python pipeline/apply_review_text_corrections.py \
        --blocks outputs/reviews/merged_full/review_block.csv \
        --pages  outputs/reviews/merged_full/review_page.csv
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

csv.field_size_limit(10 ** 9)

CORRECTIONS = Path("docs/eval/review_text_corrections.csv")
# Same file parse_reviews.py reads, so a folio is stated in exactly one place.
FOLIOS = Path("docs/review_folio_corrections.csv")
FIELDS = ("text", "caption_text")


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def apply_folios(pages: Path, corrections: Path, dry_run: bool) -> int:
    """Re-assert scan-verified printed_folio values on the merged page table.

    An empty `printed_folio` in the CSV is a real value meaning "this leaf
    carries no printed folio", so it is applied like any other -- that is the
    correction for a plate whose number the model invented from a caption.
    """
    rules = {r["page_id"]: r["printed_folio"].strip() for r in load(corrections)}
    with open(pages, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)

    changed, already, missing = 0, 0, sorted(rules)
    for r in rows:
        want = rules.get(r["page_id"])
        if want is None:
            continue
        missing.remove(r["page_id"])
        have = (r.get("printed_folio") or "").strip()
        if have == want:
            already += 1
            continue
        print(f"  {r['page_id']}  {have or '(blank)'!r} -> {want or '(blank)'!r}")
        if not dry_run:
            r["printed_folio"] = want
        changed += 1

    for page_id in missing:
        print(f"  WARNING: {page_id} is not in {pages} -- correction unused")

    print(f"  folios: {changed} changed, {already} already correct, "
          f"{len(missing)} unmatched")
    if changed and not dry_run:
        shutil.copy2(pages, pages.with_suffix(".csv.bak"))
        with open(pages, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"  written to {pages} (previous copy at {pages.with_suffix('.csv.bak')})")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=Path)
    ap.add_argument("--pages", type=Path,
                    help="merged review_page.csv; re-asserts printed_folio")
    ap.add_argument("--corrections", default=CORRECTIONS, type=Path)
    ap.add_argument("--folio-corrections", default=FOLIOS, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.blocks and not a.pages:
        ap.error("pass --blocks, --pages, or both")

    if a.pages:
        print(f"folio corrections -> {a.pages}")
        apply_folios(a.pages, a.folio_corrections, a.dry_run)
        if not a.blocks:
            return 0
        print()

    rules = load(a.corrections)
    with open(a.blocks, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)

    total, failures = 0, []
    for rule in rules:
        find, repl = rule["find"], rule["replace"]
        prefix, expected = rule["scope_page_prefix"], int(rule["expected"])
        n, pages = 0, set()
        for r in rows:
            if not r["page_id"].startswith(prefix):
                continue
            for fld in FIELDS:
                v = r.get(fld) or ""
                if find in v:
                    n += v.count(find)
                    pages.add(r["page_id"])
                    if not a.dry_run:
                        r[fld] = v.replace(find, repl)
        total += n
        status = "ok" if n == expected else ("ALREADY APPLIED" if n == 0 else "COUNT MISMATCH")
        # A mismatch means the text moved under the correction: re-check the
        # scan before forcing it through, never just update `expected`.
        if n not in (expected, 0):
            failures.append((find, repl, expected, n))
        print(f"  {find!r} -> {repl!r}  [{prefix}]  {n}/{expected} on "
              f"{len(pages)} page(s)  {status}")

    if failures:
        print("\nCOUNT MISMATCH -- nothing written. Re-check the scan:", file=sys.stderr)
        for find, repl, exp, got in failures:
            print(f"  {find!r} -> {repl!r}: expected {exp}, found {got}", file=sys.stderr)
        return 1

    if a.dry_run:
        print(f"\ndry run: {total} replacement(s) would be made")
        return 0

    if total:
        shutil.copy2(a.blocks, a.blocks.with_suffix(".csv.bak"))
        with open(a.blocks, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"\n{total} replacement(s) written to {a.blocks} "
              f"(previous copy at {a.blocks.with_suffix('.csv.bak')})")
    else:
        print("\nnothing to do -- every correction is already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
