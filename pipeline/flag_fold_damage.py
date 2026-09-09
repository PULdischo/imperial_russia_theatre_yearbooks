"""Flags text obscured by the binding fold on two-page-spread Repertoire
scans (seasons 1890-91 through 1897-98).

Why this exists: those seasons print one Repertoire table across a two-leaf
spread, and `render_pages.py` renders the spread as a single portrait image
with the two leaves stacked vertically. The binding fold runs across the
middle, and its dark core physically obscures part of one table row --
measured at ~11px median (300dpi) on the 1893-94 season, i.e. roughly the
lower third of a line of type. Character tops survive; descenders and the
receipts figures under them often do not.

This is source damage, not an extraction bug: no preprocessing recovers
ink the binding is covering. So rather than let the model silently misread
it, this stage locates the fold, crops the band at native resolution, and
emits a worksheet for hand-transcription against the physical volume.

The fold is distinguished from a printed table rule by two properties used
in `trace_fold`: it runs the full page width uninterrupted (a rule stops at
the table border), and it sits near the page's vertical centre. Measured
across the 1893-94 season (12/12 pages traced): position 48.0-49.3% of page
height, tilt 27-89px left-to-right, straight-line fit residual 2.5-5.7px.
The tilt varies per page, which is why the fold is modelled as a fitted
line rather than a constant y.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np


@dataclass
class FoldGeometry:
    """A fitted fold line, in the coordinates of the full page image."""
    page_id: str
    image_width: int
    image_height: int
    slope: float                # dy/dx
    intercept: float            # y at x=0
    y_at_left: int              # y where the trace starts (x_lo)
    y_at_right: int             # y where the trace ends (x_hi)
    x_lo: int
    x_hi: int
    tilt_px: int                # y_at_right - y_at_left
    band_px_median: int         # width of the fully-dark core
    band_px_max: int
    strips_used: int
    strips_total: int
    fit_residual_px: float

    def y_at(self, x: float) -> float:
        return self.slope * x + self.intercept


# Quality gate, calibrated against the 1893-94 season -- the only season
# whose fold trace has been confirmed correct by direct inspection of the
# scan. There, all 12 pages traced with 29-32 of 32 strips agreeing and a
# straight-line residual of 2.5-5.7px. Anything materially looser than that
# is reported as low_confidence rather than emitted as a fold line: the
# robust fit will happily put a line through 8 noise points, and a
# wrong-but-plausible fold sends a hand-transcriber to the wrong row.
MIN_STRIPS_USED = 20
MAX_FIT_RESIDUAL_PX = 8.0


def classify_page(height: int, width: int) -> str:
    """A full two-leaf spread renders portrait (two leaves stacked, aspect
    ~0.54-0.70 across these seasons); a lone leaf renders landscape (aspect
    ~1.16-1.30). A lone leaf has no binding fold crossing it, so there is
    nothing here to flag -- confirmed by direct inspection of
    repertoire_1890-91_p000, a single landscape leaf on which an earlier
    version of this module nonetheless "found" a fold."""
    return "spread" if height > width else "single_leaf"


def trace_fold(gray: np.ndarray, n_strips: int = 32, search_window: int = 140,
               min_dip: float = 6.0, max_resid: float = 12.0) -> FoldGeometry | None:
    """Locates the binding fold and fits a straight line to it.

    Returns None if the fold can't be traced -- an honest failure is better
    than a wrong-but-plausible line, the same principle `detect_columns`
    settled on (known_issues.md #68).
    """
    h, w = gray.shape
    x_lo, x_hi = int(w * 0.12), int(w * 0.88)

    # Seed: the darkest full-width row in the middle 30% of the page. Table
    # rules don't span this range uninterrupted; the fold does.
    lo, hi = int(h * 0.35), int(h * 0.65)
    prof = gray[lo:hi, x_lo:x_hi].mean(axis=1)
    prof = cv2.GaussianBlur(prof.reshape(-1, 1), (1, 15), 0).ravel()
    seed = lo + int(np.argmin(prof))

    edges = np.linspace(x_lo, x_hi, n_strips + 1).astype(int)

    def scan(centre_at) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Finds the darkest run in each vertical strip, searching a window
        around `centre_at(x)`. Passing a per-x centre (rather than one flat
        seed) is what makes a steeply tilted fold traceable: on a page with
        ~245px of tilt the end strips sit outside a flat window entirely and
        lock onto whatever other dark line is in range."""
        xs, ys, widths = [], [], []
        for i in range(n_strips):
            xm = (edges[i] + edges[i + 1]) // 2
            c = int(centre_at(xm))
            a, b = max(0, c - search_window), min(h, c + search_window)
            if b - a < 20:
                continue
            strip = gray[a:b, edges[i]:edges[i + 1]]
            pr = cv2.GaussianBlur(strip.mean(axis=1).reshape(-1, 1), (1, 7), 0).ravel()
            j = int(np.argmin(pr))
            median = float(np.median(pr))
            dip = median - float(pr[j])
            if dip < min_dip:
                continue
            thr = median - dip * 0.5
            u = j
            while u > 0 and pr[u] < thr:
                u -= 1
            v = j
            while v < len(pr) - 1 and pr[v] < thr:
                v += 1
            xs.append(xm)
            ys.append(a + j)
            widths.append(v - u)
        return np.array(xs), np.array(ys), np.array(widths)

    # Pass 1: flat window around the seed, to estimate the slope at all.
    xs, ys, widths = scan(lambda _x: seed)
    if len(xs) >= 8:
        keep = np.ones(len(xs), bool)
        for _ in range(len(xs)):
            m0, c0 = np.polyfit(xs[keep], ys[keep], 1)
            r = np.abs(ys - (m0 * xs + c0))
            worst = int(np.where(keep, r, -1).argmax())
            if r[worst] <= max_resid or keep.sum() <= 8:
                break
            keep[worst] = False
        m0, c0 = np.polyfit(xs[keep], ys[keep], 1)
        # Pass 2: re-scan along the estimated line, so every strip searches
        # a window centred on where the fold is actually predicted to be.
        xs, ys, widths = scan(lambda x: m0 * x + c0)

    if len(xs) < 8:
        return None

    # Robust fit: drop the worst outlier until the rest lie on one line.
    # Strips that locked onto a table rule instead of the fold get rejected
    # here -- without this, 5 of 12 pages fit residuals of 500-770px.
    keep = np.ones(len(xs), bool)
    for _ in range(len(xs)):
        m, c = np.polyfit(xs[keep], ys[keep], 1)
        resid = np.abs(ys - (m * xs + c))
        worst = int(np.where(keep, resid, -1).argmax())
        if resid[worst] <= max_resid or keep.sum() <= 8:
            break
        keep[worst] = False

    m, c = np.polyfit(xs[keep], ys[keep], 1)
    resid = np.abs(ys[keep] - (m * xs[keep] + c))
    return FoldGeometry(
        page_id="", image_width=int(w), image_height=int(h),
        slope=float(m), intercept=float(c),
        y_at_left=int(round(m * xs.min() + c)), y_at_right=int(round(m * xs.max() + c)),
        x_lo=int(xs.min()), x_hi=int(xs.max()),
        tilt_px=int(round(m * (xs.max() - xs.min()))),
        band_px_median=int(np.median(widths[keep])), band_px_max=int(widths[keep].max()),
        strips_used=int(keep.sum()), strips_total=int(len(xs)),
        fit_residual_px=round(float(resid.max()), 1),
    )


def write_crops(img: np.ndarray, fold: FoldGeometry, out_dir: Path,
                context_px: int = 260) -> tuple[Path, Path, int]:
    """Writes a clean native-resolution crop of the fold band (for reading
    against the physical volume) and a marked copy (showing exactly what is
    flagged). `context_px` above/below keeps a full neighbouring row visible
    so the damaged row can be identified by its neighbours and its date."""
    out_dir.mkdir(parents=True, exist_ok=True)
    y_top = max(0, min(fold.y_at_left, fold.y_at_right) - context_px)
    y_bot = min(fold.image_height, max(fold.y_at_left, fold.y_at_right) + context_px)
    crop = img[y_top:y_bot].copy()

    clean_path = out_dir / f"{fold.page_id}__fold.png"
    cv2.imwrite(str(clean_path), crop)

    marked = crop.copy()
    half = max(2, fold.band_px_max // 2)
    xs = np.arange(0, fold.image_width)
    ys = (fold.slope * xs + fold.intercept - y_top).astype(int)
    for x, y in zip(xs, ys):
        for yy in (y - half, y + half):
            if 0 <= yy < marked.shape[0]:
                marked[yy, x] = (0, 0, 255)
    marked_path = out_dir / f"{fold.page_id}__fold_marked.png"
    cv2.imwrite(str(marked_path), marked)
    return clean_path, marked_path, y_top


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--glob", default="repertoire_*.png",
                    help="which images to process (default: all repertoire pages)")
    ap.add_argument("--context-px", type=int, default=260,
                    help="pixels of context above/below the fold in the crop")
    args = ap.parse_args()

    images = sorted(args.images_dir.glob(args.glob))
    if not images:
        raise SystemExit(f"no images matched {args.glob} in {args.images_dir}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = args.out_dir / "fold_crops"
    rows, geoms, failures = [], [], []

    for path in images:
        img = cv2.imread(str(path))
        if img is None:
            failures.append((path.stem, "unreadable image"))
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kind = classify_page(*gray.shape[:2])
        if kind == "single_leaf":
            failures.append((path.stem, "no_fold_expected (single landscape leaf)"))
            continue
        fold = trace_fold(gray)
        if fold is None:
            failures.append((path.stem, "fold_not_traced"))
            continue
        confident = (fold.strips_used >= MIN_STRIPS_USED
                     and fold.fit_residual_px <= MAX_FIT_RESIDUAL_PX)
        if not confident:
            failures.append((path.stem,
                             f"low_confidence (strips {fold.strips_used}/"
                             f"{fold.strips_total}, residual "
                             f"{fold.fit_residual_px}px)"))
        fold.page_id = path.stem
        # A low-confidence trace still locates the right REGION even when the
        # exact line is uncertain, so the crop is widened rather than withheld
        # -- it serves as a locator for hand-transcription against the
        # physical volume, not as evidence in itself.
        context = args.context_px if confident else args.context_px * 3
        clean, marked, y_top = write_crops(img, fold, crops_dir, context)
        geoms.append(asdict(fold))
        rows.append({
            "page_id": fold.page_id,
            "trace_confidence": "high" if confident else "low",
            "fold_y_left": fold.y_at_left,
            "fold_y_right": fold.y_at_right,
            "tilt_px": fold.tilt_px,
            "obscured_band_px": fold.band_px_max,
            "fit_residual_px": fold.fit_residual_px,
            "crop_image": str(clean.relative_to(args.out_dir)),
            "crop_marked": str(marked.relative_to(args.out_dir)),
            "crop_y_offset": y_top,
            "obscured_date": "",
            "theater": "",
            "obscured_text": "",
            "notes": "",
        })

    csv_path = args.out_dir / "fold_damage_worksheet.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (args.out_dir / "fold_geometry.json").write_text(
        json.dumps(geoms, ensure_ascii=False, indent=1), encoding="utf-8")

    if failures:
        rej = args.out_dir / "fold_needs_review.csv"
        with rej.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["page_id", "reason"])
            w.writerows(failures)

    n_hi = sum(1 for r in rows if r["trace_confidence"] == "high")
    print(f"{len(rows)}/{len(images)} spread pages emitted -> {csv_path}")
    print(f"  trace confidence: {n_hi} high, {len(rows)-n_hi} low "
          f"(low = wider crop, fold line approximate)")
    if rows:
        bands = [r["obscured_band_px"] for r in rows]
        tilts = [abs(r["tilt_px"]) for r in rows]
        print(f"  obscured band: {min(bands)}-{max(bands)}px   "
              f"tilt: {min(tilts)}-{max(tilts)}px")
    if failures:
        from collections import Counter
        kinds = Counter(w.split(" ")[0] for _, w in failures)
        print(f"  {len(failures)} page(s) NOT emitted -> fold_needs_review.csv")
        for k, n in kinds.most_common():
            print(f"    {k}: {n}")


if __name__ == "__main__":
    main()
