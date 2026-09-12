"""Splits a two-page-spread Repertoire scan (seasons 1890-91 through
1897-98) into two separate page-like images at the physical book fold, so
each half can be fed through the same column-wise extraction pipeline
already proven for single-page-format seasons (1898-99 on) instead of the
whole unsplit 5-column spread, which measured only 14-63% receipts
agreement (docs/eval/known_issues.md, 2026-09-08 addendum).

Uses `pipeline.flag_fold_damage`'s already-fitted `FoldGeometry`
(`outputs/fold_review/fold_geometry.json`, 91/97 pages) as a PRIOR for
where to search, not as the cut itself -- checking real sample crops
showed the fitted line sometimes runs through a row's own text, and on a
low-confidence page had locked onto an unrelated table rule ~430px from
the true physical seam. The actual cut is chosen from the row-darkness
profile (`pipeline.row_detect._row_darkness_profile` /
`_find_peaks`, the same page-geometry-agnostic primitives the table-rule
detector uses) as the midpoint of the largest gap between two darkness
peaks near the fold estimate (high confidence) or across the whole
plausible middle band (low confidence / no fold) -- i.e. the blank margin
between the bottom of one leaf's table and the top of the next, never a
printed rule itself.

Usage:
    python pipeline/split_spread_pages.py --images-dir outputs/<run>/images \
        --fold-geometry outputs/fold_review/fold_geometry.json \
        --out-dir outputs/<run>/split_pages
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
from flag_fold_damage import FoldGeometry, MIN_STRIPS_USED, MAX_FIT_RESIDUAL_PX, classify_page
from row_detect import _binarize, _table_x_bounds, _row_darkness_profile, _find_peaks

# Same constant flag_fold_damage.write_crops already validated for "how much
# context around the fold matters" -- reused here as the high-confidence
# search half-window, not re-tuned.
CONTEXT_PX = 260
# Low-confidence pages still carry a fold_geometry entry in this corpus --
# every one of the 91 spread pages does, none are true None -- and direct
# inspection of 3 low-confidence samples (1892-93_p002, 1895-96_p002,
# 1891-92_p000) found the raw fold-trace estimate consistently within a
# couple hundred px of the true seam, not the ~430px-off outlier that
# originally motivated ignoring it entirely. So low-confidence pages get a
# wider search band centered on the SAME estimate, not a blind scan of the
# whole middle third -- the blind band (below) is now only a true fallback
# for the (currently nonexistent, but defensively kept) fold-is-None case.
WIDE_FOLD_CONTEXT_PX = 500
# NOTE on this threshold: _row_darkness_profile's own docstring describes
# rule lines as "near-1.0" spikes, and _build_chains's default (0.35) reads
# the same way -- but that default is computed per NARROW STRIP (40 slices
# of the table width), where a rule line dominates the whole strip. Measured
# directly against these spread images (full x0:x1 width, per
# repertoire_1893-94_p006 and repertoire_1891-92_p001): the darkest row
# anywhere near the known-correct fold band tops out at 0.30-0.35, never
# near 1.0 -- these tables have 5-6 theater columns plus a date column, so
# even at a genuine full rule, other columns' antialiasing/hairline weight
# hold the whole-width average well below what a single narrow strip shows.
# Lowered again after direct inspection of repertoire_1895-96_p002: its
# true fold rule peaks at just 0.254, missed by an 0.25 cutoff. 0.15 catches
# it while still sitting well above ordinary text rows (well under 0.15 in
# the same scans).
_PEAK_HEIGHT = 0.15
_PEAK_MIN_GAP = 10
# Extra context each half-image keeps past the strict cut line, so a row
# whose content straddles the fold lands intact in at least one half
# instead of being clipped in both -- chosen after measuring 48% of pages
# straddle (see split_diagnostics.csv, 2026-09-11 run), far above the ~37%
# a small hand-sample suggested, so a non-overlapping split would leave a
# genuinely incomplete row on close to half the corpus, not a rare
# exception. Sized from actual row-height measurements on 3 sample pages
# (_row_darkness_profile peak spacing, height=0.15): ordinary multi-
# performance date rows commonly run 150-500px, occasionally more; 500px
# comfortably covers even the taller rows with margin, on either side of
# the cut. RG approved this approach 2026-09-11 with the explicit fallback
# that persistent unwieldiness (too much duplicate content to reconcile
# cleanly) means revisiting non-overlapping halves + a review queue
# instead (plan's original option 2).
OVERLAP_PX = 500
# Ink-density threshold for flagging a suspected row straddling the cut --
# same full-width-average regime as above, so recalibrated alongside it
# rather than left at a value tuned for a different profile shape. A
# genuinely blank inter-row gap scores near 0 in this measurement; content
# straddling the cut (confirmed directly on repertoire_1893-94_p006, where
# the binding thread visibly crosses an ordinary content row) scores well
# above the ordinary blank-gap floor.
_STRADDLE_DENSITY_THRESHOLD = 0.08
_STRADDLE_BAND_PX = 20


@dataclass
class SplitCut:
    page_id: str
    cut_y: int | None
    seed_source: str
    # one of: "single_leaf_no_split_needed" | "fold_high_confidence" |
    # "wide_band_search" | "fold_fallback" | "fold_fallback_low_confidence" |
    # "no_signal"
    fold_agreement_px: int | None
    straddle_suspected: bool
    gap_px: int | None


def _fold_confident(fold: FoldGeometry) -> bool:
    return fold.strips_used >= MIN_STRIPS_USED and fold.fit_residual_px <= MAX_FIT_RESIDUAL_PX


def find_split_cut(gray: np.ndarray, page_id: str, fold: FoldGeometry | None) -> SplitCut:
    h, w = gray.shape

    # A true single_leaf page (landscape, no fold -- classify_page's own
    # test) needs no cut at all; it goes straight into column-wise
    # extraction unmodified (plan Phase 4). Running the fold/cut search on
    # one anyway is a real bug, not a rare edge case -- confirmed directly:
    # repertoire_1890-91_p000, a known single_leaf page, was showing up in
    # this module's own "no_signal" bucket before this check existed.
    if classify_page(h, w) == "single_leaf":
        return SplitCut(page_id=page_id, cut_y=None, seed_source="single_leaf_no_split_needed",
                         fold_agreement_px=None, straddle_suspected=False, gap_px=None)

    binary = _binarize(gray)
    x0, x1 = _table_x_bounds(binary)
    profile = _row_darkness_profile(binary, x0, x1)

    confident = fold is not None and _fold_confident(fold)
    fold_y: int | None = None
    if fold is not None:
        mid_x = (fold.x_lo + fold.x_hi) // 2
        fold_y = int(round(fold.y_at(mid_x)))

    if confident:
        lo, hi = max(0, fold_y - CONTEXT_PX), min(h, fold_y + CONTEXT_PX)
        seed_source = "fold_high_confidence"
    elif fold_y is not None:
        lo, hi = max(0, fold_y - WIDE_FOLD_CONTEXT_PX), min(h, fold_y + WIDE_FOLD_CONTEXT_PX)
        seed_source = "wide_band_search"
    else:
        # True fallback for a page with no fold trace at all (fold is None)
        # -- doesn't currently occur in this corpus (all 91 spread pages
        # have a fold_geometry entry) but kept rather than assuming that
        # holds forever.
        lo, hi = int(h * 0.35), int(h * 0.65)
        seed_source = "wide_band_search"

    band = profile[lo:hi]
    peaks_local = _find_peaks(band, height=_PEAK_HEIGHT, min_gap=_PEAK_MIN_GAP)
    peaks = [lo + p for p in peaks_local]

    cut_y: int | None = None
    gap_px: int | None = None
    if len(peaks) >= 2:
        gaps = [(peaks[i + 1] - peaks[i], (peaks[i] + peaks[i + 1]) // 2)
                for i in range(len(peaks) - 1)]
        if fold_y is not None:
            # Prefer the gap nearest the fold estimate over the globally
            # widest one -- confirmed necessary on repertoire_1895-96_p002,
            # where the widest gap in the search band (a genuinely blank
            # run of dashed "no performance" cells elsewhere in the table)
            # sat ~550px from the true seam, while the correct gap (near a
            # tight cluster of rule-line peaks right at the fold) was only
            # the 3rd-widest candidate.
            gap_px, cut_y = min(gaps, key=lambda g: abs(g[1] - fold_y))
        else:
            gap_px, cut_y = max(gaps, key=lambda g: g[0])
    elif len(peaks) == 1:
        # A single dominant peak in the search band is very likely the
        # fold's own rule line (or the binding thread itself), not one
        # half of a gap that needs a second reference point -- confirmed on
        # repertoire_1891-92_p000, whose one clean peak sat within a few px
        # of the fold estimate and was, by direct inspection of the scan,
        # exactly the true seam. No `gap_px` here since there was no gap to
        # measure, just one strong line.
        cut_y = peaks[0]
    elif fold_y is not None:
        # No peak at all near the estimate -- confirmed on
        # repertoire_1892-93_p002, where the fold cuts straight through an
        # ordinary content row with no blank margin or rule line anywhere
        # nearby (max darkness in the whole band was 0.146). The raw fold
        # estimate is still the best available locator; straddle detection
        # below and the page-number verification pass (plan Phase 3) are
        # the intended backstop for the reduced precision here, not a
        # reason to withhold a cut entirely.
        cut_y = fold_y
        seed_source = "fold_fallback" if confident else "fold_fallback_low_confidence"
    else:
        # No fold trace and no peak signal at all: honest failure, matching
        # trace_fold's/detect_columns's own "wrong-but-plausible is worse
        # than no answer" convention.
        seed_source = "no_signal"

    fold_agreement_px = (abs(cut_y - fold_y) if cut_y is not None and fold_y is not None else None)

    straddle_suspected = False
    if cut_y is not None:
        t_lo = max(0, cut_y - _STRADDLE_BAND_PX)
        t_hi = min(h, cut_y + _STRADDLE_BAND_PX)
        tight_density = float(binary[t_lo:t_hi, x0:x1].mean() / 255.0)
        straddle_suspected = tight_density > _STRADDLE_DENSITY_THRESHOLD

    return SplitCut(page_id=page_id, cut_y=cut_y, seed_source=seed_source,
                     fold_agreement_px=fold_agreement_px,
                     straddle_suspected=straddle_suspected, gap_px=gap_px)


@dataclass
class SplitExtent:
    """Records exactly what split_page() cropped, in the SOURCE image's own
    y-coordinates -- the true (non-overlapping) `cut_y` plus each half's
    actual crop range. Downstream de-dup (plan Phase 5/6's cross-split
    date-continuity check) needs this to identify which rows fall in BOTH
    halves' overlap band (`top_y_end > cut_y` and `bottom_y_start < cut_y`)
    so it can reconcile the duplicate rather than double-count it -- e.g.
    keep whichever half has that row's date fully clear of ITS OWN crop
    edge, or merge column-by-column if both are clipped somewhere."""
    page_id: str
    cut_y: int
    overlap_px: int
    top_y_start: int
    top_y_end: int
    bottom_y_start: int
    bottom_y_end: int


# The top half's own top edge is the physical page's OUTER edge -- the
# scan captures a sliver of the book cover material there (dark, high-
# contrast, right at the crop's top). The bottom half has no equivalent
# problem: its top edge is the fold/gutter, plain paper. Confirmed as the
# root cause of a real Phase 5 failure (2026-09-11): every top-half
# date-only column that mis-read its dates (3 rows found out of ~13
# actually printed) showed this dark band at the crop's top; every
# succeeding bottom-half crop did not. Measured directly on the two
# failing pages: the band runs to ~100-200px (up to ~7.2% of image
# height, 2728-2775px tall in the samples checked) before the page's own
# paper color takes over -- true table content (the header row) doesn't
# start until roughly 17% down, so an 8% trim clears the artifact with a
# wide safety margin and loses nothing real. Bottom halves are left
# alone; the same trim there would cut into actual fold-adjacent content.
TOP_EDGE_TRIM_FRAC = 0.08


def split_page(image_path: Path, cut: SplitCut, out_dir: Path,
               page_id_top: str, page_id_bottom: str,
               overlap_px: int = OVERLAP_PX) -> tuple[Path, Path, SplitExtent]:
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"unreadable image: {image_path}")
    if cut.cut_y is None:
        raise ValueError(f"{cut.page_id} has no cut_y (seed_source={cut.seed_source}) -- "
                          f"needs manual review before splitting")
    h = img.shape[0]
    top_y_start = int(h * TOP_EDGE_TRIM_FRAC)
    top_y_end = min(h, cut.cut_y + overlap_px)
    bottom_y_start, bottom_y_end = max(0, cut.cut_y - overlap_px), h

    out_dir.mkdir(parents=True, exist_ok=True)
    top_path = out_dir / f"{page_id_top}.png"
    bottom_path = out_dir / f"{page_id_bottom}.png"
    cv2.imwrite(str(top_path), img[top_y_start:top_y_end])
    cv2.imwrite(str(bottom_path), img[bottom_y_start:bottom_y_end])

    extent = SplitExtent(page_id=cut.page_id, cut_y=cut.cut_y, overlap_px=overlap_px,
                          top_y_start=top_y_start, top_y_end=top_y_end,
                          bottom_y_start=bottom_y_start, bottom_y_end=bottom_y_end)
    return top_path, bottom_path, extent


def load_fold_geometry(path: Path) -> dict[str, FoldGeometry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {r["page_id"]: FoldGeometry(**r) for r in raw}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--fold-geometry", type=Path, required=True,
                     help="outputs/fold_review/fold_geometry.json")
    ap.add_argument("--out-dir", type=Path, required=True,
                     help="diagnostics CSV goes here; pass --split to also write image halves")
    ap.add_argument("--glob", default="repertoire_*.png")
    ap.add_argument("--split", action="store_true",
                     help="also write the two half-images (default: cut-finding only, for review)")
    ap.add_argument("--overlap-px", type=int, default=OVERLAP_PX,
                     help=f"context each half keeps past the cut, for straddling rows (default {OVERLAP_PX})")
    args = ap.parse_args()

    fold_geoms = load_fold_geometry(args.fold_geometry)
    images = sorted(args.images_dir.glob(args.glob))
    if not images:
        raise SystemExit(f"no images matched {args.glob} in {args.images_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    extents = []
    for path in images:
        page_id = path.stem
        img = cv2.imread(str(path))
        if img is None:
            rows.append({"page_id": page_id, "cut_y": "", "seed_source": "unreadable_image",
                         "fold_agreement_px": "", "straddle_suspected": "", "gap_px": ""})
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fold = fold_geoms.get(page_id)
        cut = find_split_cut(gray, page_id, fold)
        rows.append({
            "page_id": cut.page_id, "cut_y": cut.cut_y, "seed_source": cut.seed_source,
            "fold_agreement_px": cut.fold_agreement_px,
            "straddle_suspected": cut.straddle_suspected, "gap_px": cut.gap_px,
        })
        if args.split and cut.cut_y is not None:
            # Real page numbers aren't known until extract_split_page_numbers.py
            # runs (stage 3) -- placeholder halves named by source page + half
            # for now; renamed once page numbers are confirmed.
            _, _, extent = split_page(path, cut, args.out_dir / "images",
                                       f"{page_id}__top", f"{page_id}__bottom",
                                       overlap_px=args.overlap_px)
            extents.append(asdict(extent))

    csv_path = args.out_dir / "split_diagnostics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    if extents:
        # Downstream de-dup input (plan Phase 5/6): any row whose true y
        # falls between bottom_y_start and cut_y, or between cut_y and
        # top_y_end, was captured in BOTH halves -- reconcile by date-key,
        # don't double-count.
        extents_path = args.out_dir / "split_extents.csv"
        with extents_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(extents[0].keys()))
            w.writeheader()
            w.writerows(extents)
        print(f"{len(extents)} split half-image pairs -> {extents_path}")

    from collections import Counter
    counts = Counter(r["seed_source"] for r in rows)
    n_straddle = sum(1 for r in rows if r["straddle_suspected"] is True)
    print(f"{len(rows)} pages -> {csv_path}")
    print(f"  seed_source: {dict(counts)}")
    print(f"  straddle_suspected: {n_straddle}")


if __name__ == "__main__":
    main()
