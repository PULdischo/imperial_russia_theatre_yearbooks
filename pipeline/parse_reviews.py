"""Stage 3 of the season-reviews pipeline: parse the raw JSON responses,
validate against the pydantic contract, apply deterministic repairs, and
write flat CSVs.

Reads only files already on disk, so it is free to re-run. Every convention
change lands here rather than in the (paid, non-deterministic) extraction
step -- the flatten-boundary discipline from CLAUDE.md.

Deterministic repairs applied here, rather than by spending more prompt:

* Empty `figure` blocks are dropped. The model reliably sets
  `tailpiece_present` AND also emits a contentless figure block for a
  decorative ornament (known_issues_reviews.md #3). The block carries no
  text, but it inflates block counts, and block structure is compared
  separately in the eval (docs/season_reviews.md §11).

* Gap spans carrying text are contradictory -- a gap means no reading was
  offered. The text is kept and the gap flag cleared, since discarding a
  reading the model did produce would lose more than it gains.

Usage:
    python pipeline/parse_reviews.py --manifest outputs/reviews/manifest.csv \
        --raw-dir outputs/reviews/raw --out-dir outputs/reviews/parsed
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import ReviewPageLLM, flatten_review_page, page_plain_text

TABLES = ("review_page", "review_block", "review_span")


def repair(page: ReviewPageLLM) -> tuple[ReviewPageLLM, list[str]]:
    notes = []
    kept = []
    for b in page.blocks:
        if b.block_type == "figure" and not b.spans and not b.caption:
            notes.append("dropped_empty_figure_block")
            continue
        for s in b.spans + b.caption:
            if s.gap and s.text:
                s.gap = False
                notes.append("gap_span_had_text_kept_text")
        kept.append(b)
    page.blocks = kept
    return page, notes


def load_folio_corrections(path: Path) -> dict[str, str]:
    """Hand-verified printed_folio overrides, applied at PARSE time.

    raw/*.raw.json is the model's response and the reproducibility record --
    CLAUDE.md: "verbatim, never hand-edited". So corrections live in a CSV
    that is applied on the way out, exactly like the tabular pipeline puts
    fixes in `analysis` rather than `raw`. Re-parsing is free, so a
    correction costs nothing and can be withdrawn by deleting a row.

    An empty printed_folio column means "this page carries NO printed folio"
    -- which is a real and common answer: full-page plates are unpaginated,
    and the model sometimes invents a number from the caption instead.
    """
    if not path or not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["page_id"]: r["printed_folio"].strip()
                for r in csv.DictReader(f) if r.get("page_id")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--folio-corrections", type=Path,
                    default=Path("docs/review_folio_corrections.csv"),
                    help="hand-verified printed_folio overrides; applied at "
                         "parse time so raw/ is never edited. Pass a "
                         "nonexistent path to disable.")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    out = {t: [] for t in TABLES}
    folio_fixes = load_folio_corrections(args.folio_corrections)
    errors, repairs = [], []
    n_ok = n_missing = n_failed = n_folio_fixed = 0

    for r in rows:
        page_id = r["page_id"]
        raw_path = args.raw_dir / f"{page_id}.raw.json"
        if not raw_path.exists():
            n_missing += 1
            continue
        try:
            data = json.loads(raw_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            n_failed += 1
            errors.append({"page_id": page_id, "stage": "json",
                           "error": f"{type(e).__name__}: {e}"})
            continue
        try:
            page = ReviewPageLLM.model_validate(data)
        except ValidationError as e:
            n_failed += 1
            errors.append({"page_id": page_id, "stage": "schema",
                           "error": str(e).replace("\n", " | ")[:800]})
            continue

        page, notes = repair(page)
        for note in notes:
            repairs.append({"page_id": page_id, "repair": note})

        if page_id in folio_fixes:
            was = page.printed_folio
            page = page.model_copy(
                update={"printed_folio": folio_fixes[page_id] or None})
            repairs.append({"page_id": page_id,
                            "repair": f"folio_correction: {was!r} -> "
                                      f"{page.printed_folio!r}"})
            n_folio_fixed += 1

        flat = flatten_review_page(page_id, r["season"], r["city"], r["genre"], page)
        for t in TABLES:
            out[t].extend(flat[t])

        # the plain text, one file per page -- what the eval scores and what
        # the derived formats are built from
        text_dir = args.out_dir / "text"
        text_dir.mkdir(exist_ok=True)
        (text_dir / f"{page_id}.txt").write_text(page_plain_text(page),
                                                 encoding="utf-8")
        n_ok += 1

    for t in TABLES:
        path = args.out_dir / f"{t}.csv"
        if out[t]:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(out[t][0].keys()))
                w.writeheader()
                w.writerows(out[t])

    if errors:
        with open(args.out_dir / "validation_errors.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["page_id", "stage", "error"])
            w.writeheader()
            w.writerows(errors)
    if repairs:
        with open(args.out_dir / "repairs.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["page_id", "repair"])
            w.writeheader()
            w.writerows(repairs)

    print(f"parsed {n_ok} pages | not yet extracted {n_missing} | failed {n_failed}")
    if folio_fixes:
        print(f"  folio corrections applied: {n_folio_fixed} of {len(folio_fixes)} on file")
    for t in TABLES:
        print(f"  {t}: {len(out[t])} rows")
    if repairs:
        from collections import Counter
        for k, v in Counter(r["repair"] for r in repairs).items():
            print(f"  repair {k}: {v}")
    if errors:
        print(f"  -> {args.out_dir/'validation_errors.csv'}")


if __name__ == "__main__":
    main()
