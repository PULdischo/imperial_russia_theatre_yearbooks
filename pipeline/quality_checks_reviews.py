"""Stage 4 of the season-reviews pipeline: gold-free structural checks over
every parsed page (docs/season_reviews.md §10).

This is what scales past the twelve gold pages. The gold set measures worst
case on a deliberately hard sample; these checks cover all 1,024 pages and
catch the failures that are invisible to a character-accuracy score.

Checks
------
missing_page          A break in the printed-folio run within a file.
folio_gap_unverifiable  Two folios with scan pages between them that are
                      absent from this input -- the sequence cannot be
                      checked there. Expected on any partial run.
duplicate_folio       The same folio twice in one file.
letter_spacing_leak   Literal letter-spacing in span text that was NOT
                      flagged as разрядка (flagged ones are repaired at parse
                      time; unflagged ones cannot be safely auto-repaired
                      because we cannot tell them from spaced initials).
no_text_but_inked     A page declared textless whose image carries a lot of
                      ink. The single most likely false positive in the whole
                      design, because plate captions are often set sideways.
thin_page             Far less text than the ink on the page suggests.
no_folio              No printed folio captured.
zero_uncertainty      A whole file with no uncertainty flags at all -- across
                      hundreds of pages that means confabulation, not success.

Usage:
    python pipeline/quality_checks_reviews.py --parsed-dir outputs/reviews/parsed \
        --manifest outputs/reviews/manifest.csv --images-dir outputs/reviews/images \
        --out outputs/reviews/quality_flags.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import LETTER_SPACING_LEAK_RE

FOLIO_RE = re.compile(r"\d+")


def ink_fraction(path: Path, thumb: int = 200) -> float:
    """Fraction of the page that is non-white, at thumbnail scale. Cheap
    proxy for 'how much is printed here'."""
    from PIL import Image
    im = Image.open(path).convert("L").resize((thumb, thumb))
    px = im.tobytes()
    return sum(1 for v in px if v < 200) / float(len(px))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", type=Path, default=None,
                    help="enables the ink-based checks; skipped if omitted")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    manifest = {r["page_id"]: r
                for r in csv.DictReader(open(args.manifest, encoding="utf-8"))}
    pages = list(csv.DictReader(open(args.parsed_dir / "review_page.csv",
                                     encoding="utf-8")))
    spans = list(csv.DictReader(open(args.parsed_dir / "review_span.csv",
                                     encoding="utf-8")))

    flags = []

    def flag(page_id, kind, detail):
        flags.append({"page_id": page_id, "check": kind, "detail": detail})

    # ---- unflagged letter-spacing ---------------------------------------
    for s in spans:
        if s["razryadka"] == "True":
            continue
        if LETTER_SPACING_LEAK_RE.search(s["text"]):
            flag(s["block_id"].split("__")[0], "letter_spacing_leak",
                 s["text"][:80])

    # ---- folio sequence, per source file --------------------------------
    by_file = defaultdict(list)
    for p in pages:
        src = manifest.get(p["page_id"], {}).get("source_file", "?")
        idx = int(manifest.get(p["page_id"], {}).get("source_page_index", -1))
        by_file[src].append((idx, p))

    for src, items in sorted(by_file.items()):
        items.sort(key=lambda t: t[0])
        seen = {}
        prev = None            # (folio, page_id, source_page_index)
        unpaginated_since = 0
        for idx, p in items:
            m = FOLIO_RE.search(p["printed_folio"] or "")
            if not m:
                flag(p["page_id"], "no_folio", "no printed folio captured")
                unpaginated_since += 1
                continue
            folio = int(m.group(0))
            if folio in seen:
                flag(p["page_id"], "duplicate_folio",
                     f"folio {folio} also on {seen[folio]}")
            seen[folio] = p["page_id"]
            if prev is not None:
                # Only compare pages we can actually account for. Between
                # two folios there are (idx - prev_idx - 1) scan pages; we
                # saw `unpaginated_since` of them without a folio. Any
                # others are simply NOT IN THIS INPUT, and then the folio
                # gap says nothing.
                #
                # 2026-09-25: without this the check fires on any partial
                # input. On a 200-page stratified pilot it reported
                # "194 -> 117" as a missing page, when the two were nine
                # scan pages apart and everything between was unsampled --
                # a false positive that would have buried a real one. It
                # also matters on the full run, where a render failure or a
                # skipped page leaves the same hole.
                absent = (idx - prev[2] - 1) - unpaginated_since
                if absent > 0:
                    flag(p["page_id"], "folio_gap_unverifiable",
                         f"{src}: folio {prev[0]} ({prev[1]}) -> {folio}, but "
                         f"{absent} scan page(s) between are absent from this "
                         f"input; sequence not checkable here")
                else:
                    gap = folio - prev[0] - 1
                    # docs/season_reviews.md §10: the gap must be exactly the
                    # number of unpaginated scan pages sitting between them.
                    if gap != unpaginated_since:
                        flag(p["page_id"], "missing_page",
                             f"{src}: folio {prev[0]} ({prev[1]}) -> {folio}; "
                             f"gap of {gap} with {unpaginated_since} "
                             f"unpaginated page(s) between")
            prev = (folio, p["page_id"], idx)
            unpaginated_since = 0

    # ---- zero uncertainty across a whole file ---------------------------
    unc_by_file = defaultdict(int)
    pages_by_file = defaultdict(int)
    span_page = {}
    for s in spans:
        span_page[s["block_id"].split("__")[0]] = s
    for p in pages:
        src = manifest.get(p["page_id"], {}).get("source_file", "?")
        pages_by_file[src] += 1
    for s in spans:
        if s["uncertain"] == "True" or s["gap"] == "True":
            pid = s["block_id"].split("__")[0]
            unc_by_file[manifest.get(pid, {}).get("source_file", "?")] += 1
    for src, n in sorted(pages_by_file.items()):
        if n >= 15 and unc_by_file.get(src, 0) == 0:
            flag(f"[file] {src}", "zero_uncertainty",
                 f"{n} pages, not one uncertainty or gap flag")

    # ---- ink-based checks ------------------------------------------------
    if args.images_dir:
        for p in pages:
            img = args.images_dir / Path(
                manifest.get(p["page_id"], {}).get("image_file", "")).name
            if not img.exists():
                continue
            ink = ink_fraction(img)
            n_chars = int(p["n_chars"] or 0)
            if p["no_text"] == "True" and ink > 0.02:
                flag(p["page_id"], "no_text_but_inked",
                     f"declared textless but ink={ink:.3f} -- check for a "
                     f"sideways caption")
            elif n_chars < 200 and ink > 0.10:
                flag(p["page_id"], "thin_page",
                     f"{n_chars} chars but ink={ink:.3f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id", "check", "detail"])
        w.writeheader()
        w.writerows(flags)

    from collections import Counter
    print(f"{len(pages)} pages checked, {len(flags)} flags -> {args.out}")
    for k, v in sorted(Counter(f["check"] for f in flags).items()):
        print(f"  {k:22} {v}")


if __name__ == "__main__":
    main()
