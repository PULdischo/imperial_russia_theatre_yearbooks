"""Detects a Repertoire page's table row boundaries (as curves, not single
y-values -- these are overhead scans of old bound books, and some pages are
measurably skewed or genuinely bowed, not just tilted) and crops/dewarps
each dated row into its own image with the theater-column header reattached
but with ZERO other row's content visible.

Why a row needs to be alone in the frame, not just cropped small: RG's
2026-08-25/26 investigation (known_issues.md #1) found that Repertoire
extraction sometimes misattributes one row's real content onto a neighboring
row's date -- confirmed reproducible byte-for-byte across 5 independent
samples in every multi-row context tested (full page, half-page chunks,
5-6-row crops). The failure disappeared completely (10/10 samples, exact
match to the scan) only when a row was isolated with no other dated row
visible in the image at all. This module automates the by-hand technique
that proved that (see docs/eval/known_issues.md #1's final addendum).

Dependency note: requires opencv-python-headless, version-pinned in
CLAUDE.md's Setup section -- see that pin's comment for why (a macOS
version constraint on the dev machine, unrelated to Python version).

Not yet wired into run_pilot.py -- this module only produces row-crop
images + a manifest describing them; pipeline/row_isolated_extract.py (to
be added) is what actually calls the model on each crop.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np


@dataclass
class RowCrop:
    """One dated row's isolated, header-reattached, dewarped image."""
    index: int  # 1-based, top to bottom
    image_path: str
    # y-range (in the ORIGINAL page image) this row was cut from, for
    # debugging/visualization -- not used by extraction itself.
    top_y_range: tuple[int, int]
    bottom_y_range: tuple[int, int]


@dataclass
class PageAnalysis:
    """Everything needed to review a page's detected boundaries, correct
    them by hand, and then crop/dewarp from the corrected set -- added
    2026-08-26 for the human-in-the-loop review workflow (RG: automated
    detection + a debug-visualize image RG checks against the scan, with
    misses/false-positives fixed by pointing at a curve index rather than
    redone from scratch). `curves` is the current, possibly-corrected
    list; `chains`/`strip_centers` are the full detection result
    (including chains presence-filtering rejected) so a correction can
    re-scan the real underlying signal instead of guessing a new one;
    `corrections` is an append-only log of what a human changed and why,
    written out alongside the row crops for the same audit-trail reason
    docs/query_log.md and the parse_and_validate.py fix-tables exist."""
    image_path: Path
    gray: np.ndarray
    binary: np.ndarray
    x0: int
    x1: int
    chains: list[dict[int, int]]
    strip_centers: list[int]
    curves: list[np.ndarray]
    corrections: list[dict] = None

    def __post_init__(self):
        if self.corrections is None:
            self.corrections = []


def _binarize(gray: np.ndarray) -> np.ndarray:
    """Global Otsu threshold -- deliberately NOT adaptive/local. Option B's
    darkness-fraction profiling (below) needs one globally-consistent
    definition of "ink" across the whole page; a locally-adaptive
    threshold would let each small neighborhood's contrast drift, which
    would corrupt the width-fraction comparison the whole approach rests
    on. A slight Gaussian blur first suppresses paper-grain speckle so
    Otsu's histogram split isn't thrown off by it."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def _table_x_bounds(binary: np.ndarray, margin_frac: float = 0.08) -> tuple[int, int]:
    """Approximates the table's left/right extent by trimming a fixed
    margin off each edge, rather than precisely detecting the table's own
    border rules. Precise vertical-divider detection turned out to be its
    own hard problem (physical-scan edge artifacts -- binding shadow, page
    curl, background outside the page -- dominate a raw column-darkness
    scan far more than the actual thin table border does, see
    docs/eval/known_issues.md #1 pilot notes). A generous fixed trim is
    good enough for the row-boundary detector below, which only needs an
    x-range that avoids those edge artifacts, not the table's exact pixel
    boundary -- real horizontal grid lines still show up as strong,
    unambiguous peaks well within a roughly-right window."""
    W = binary.shape[1]
    margin = int(W * margin_frac)
    return margin, W - margin


def _row_darkness_profile(binary: np.ndarray, x0: int, x1: int) -> np.ndarray:
    """Fraction of dark pixels at each y, restricted to [x0, x1]. A real
    printed table rule darkens nearly the entire table width -- a sharp,
    narrow, near-1.0 spike -- while even dense text only darkens scattered
    patches at any single y, staying well below that. This is the core
    signal Option B relies on instead of assembling broken line segments
    (which is what went wrong with the Hough-based first attempt -- see
    docs/eval/known_issues.md #1 pilot notes)."""
    return binary[:, x0:x1].mean(axis=1) / 255.0


def _find_peaks(profile: np.ndarray, height: float, min_gap: int) -> list[int]:
    """Local maxima above `height`, at least `min_gap` apart (keeping the
    taller peak when two are closer than that -- collapses a rule's few-
    pixel thickness down to one y per line)."""
    candidates = [y for y in range(1, len(profile) - 1)
                  if profile[y] >= height and profile[y] >= profile[y - 1] and profile[y] >= profile[y + 1]]
    peaks: list[int] = []
    for y in candidates:
        if peaks and y - peaks[-1] < min_gap:
            if profile[y] > profile[peaks[-1]]:
                peaks[-1] = y
        else:
            peaks.append(y)
    return peaks


def _build_chains(gray: np.ndarray, peak_height: float = 0.35, min_row_gap: int = 100,
                   n_strips: int = 40, step_window: int = 30
                   ) -> tuple[list[dict[int, int]], list[int], np.ndarray, int, int]:
    """Everything `_detect_line_curves` needs before its presence-filter /
    merge / gap-fill decisions: per-strip peaks chained into candidate
    lines, both kept and rejected. Factored out (2026-08-26) so a manual
    correction (RG pointing at a specific missing/spurious boundary on the
    debug-visualize image) can re-scan the SAME already-computed chains
    the automatic gap-fill pass uses, instead of a fresh ad hoc search --
    one detection mechanism, two ways of choosing what to keep from it.

    Returns (chains, strip_centers, binary, x0, x1)."""
    binary = _binarize(gray)
    x0, x1 = _table_x_bounds(binary)

    strip_edges = np.linspace(x0, x1, n_strips + 1).astype(int)
    strip_centers = [(strip_edges[i] + strip_edges[i + 1]) // 2 for i in range(n_strips)]
    strip_peaks: list[list[int]] = []
    for i in range(n_strips):
        sx0, sx1 = strip_edges[i], strip_edges[i + 1]
        profile = binary[:, sx0:sx1].mean(axis=1) / 255.0
        strip_peaks.append(_find_peaks(profile, height=peak_height, min_gap=min_row_gap))

    def _grow_chain(seed_i: int, seed_y: int) -> dict[int, int]:
        chain = {seed_i: seed_y}
        for direction in (+1, -1):
            cur_y = seed_y
            i = seed_i
            while True:
                nxt = i + direction
                if nxt < 0 or nxt >= n_strips:
                    break
                candidates = strip_peaks[nxt]
                if candidates:
                    closest = min(candidates, key=lambda y: abs(y - cur_y))
                    if abs(closest - cur_y) <= step_window:
                        chain[nxt] = closest
                        cur_y = closest
                    # else: no close-enough candidate -- skip this strip,
                    # keep searching from the last known cur_y so one
                    # noisy/text-covered strip doesn't kill the chain
                i = nxt
        return chain

    def _already_covered(strip_i: int, y: int, tol: int = 15) -> bool:
        return any(strip_i in chain and abs(chain[strip_i] - y) <= tol for chain in chains)

    # Seed a chain from every strip's peaks, busiest strip first (see
    # _detect_line_curves' docstring point 2) -- not just whichever single
    # strip has the most peaks overall, which was found to silently drop
    # real lines a busier strip's own peak list simply didn't include.
    chains: list[dict[int, int]] = []
    for seed_i in sorted(range(n_strips), key=lambda i: -len(strip_peaks[i])):
        for seed_y in strip_peaks[seed_i]:
            if _already_covered(seed_i, seed_y):
                continue
            chains.append(_grow_chain(seed_i, seed_y))

    return chains, strip_centers, binary, x0, x1


def _smooth_curve(curve: np.ndarray, window: int = 121) -> np.ndarray:
    """Light moving-average smoothing across a curve's columns. Flagged
    2026-08-27 during RG's manual review of p004: the piecewise-linear
    interpolation between per-strip peak positions can visibly zig-zag
    even when the real printed rule is straight, because each strip's own
    peak y-value has a pixel or two of independent noise. `window`
    (~121px, roughly 1.5-2 strip-widths on a typical page at these
    settings -- same kind of fixed-constant heuristic as `min_row_gap`
    elsewhere in this module, not computed per-page) is wide enough to
    average that single-strip jitter out while staying narrow enough to
    still track genuine gradual bowing/skew, which varies over a much
    wider span than one strip's noise does. Edge-padded so the curve's
    endpoints aren't pulled inward by the window running off the array."""
    if window < 3 or window >= len(curve):
        return curve
    if window % 2 == 0:
        window += 1
    kernel = np.ones(window) / window
    pad = window // 2
    padded = np.pad(curve, pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def _chain_to_curve(chain: dict[int, int], strip_centers: list[int], W: int) -> np.ndarray:
    xs = [strip_centers[i] for i in sorted(chain)]
    ys = [chain[i] for i in sorted(chain)]
    return _smooth_curve(np.interp(np.arange(W), xs, ys))


def _detect_line_curves(gray: np.ndarray, peak_height: float = 0.35,
                         min_row_gap: int = 100, n_strips: int = 40,
                         step_window: int = 30, presence_frac: float = 0.7,
                         drop_edge_artifacts: bool = True
                         ) -> list[np.ndarray]:
    """Detects the page's horizontal table rules as curves (one y-value per
    x-column across the full width), tolerant of genuine bowing/skew, not
    just simple tilt.

    A whole-table-width darkness-fraction profile (averaging over the full
    width at each y) does NOT work for this -- a curved line's y-position
    drifts with x, so at any single fixed y only part of the width is
    actually on the line, diluting the peak below any usable threshold
    (confirmed: measured drift of ~175px over a ~1200px span on a real
    page during the 2026-08 pilot). Real per-strip peaks stayed sharp and
    consistent across strips even with that much drift, so the detector is
    built around that instead:

    1. Find every local darkness peak independently in each of `n_strips`
       narrow vertical bands across the table width (each strip is narrow
       enough that curvature within it is negligible).
    2. Seed a chain from EVERY strip's peaks, not just the single busiest
       strip -- processed busiest-strip-first so a chain grows to its full
       extent before weaker strips get a turn, but every strip still gets
       one. A first version seeded only from the single strip with the
       most total peaks, on the theory that it was most likely to be a
       clean, text-light sample -- confirmed via direct measurement
       (2026-08 pilot) that this silently drops real lines: one page had a
       genuine boundary independently detected by 30+ of 40 strips, but
       the single busiest strip (busiest overall, not necessarily at that
       specific y) happened to be one of the few that missed it, so no
       chain was ever created for it at all. Multi-seeding fixes this --
       any strip that sees a line gets a chance to start its chain, and a
       peak already covered by an existing chain doesn't spawn a
       redundant one (checked at each strip position, not just at the
       seed).
    3. Walk each chain strip by strip (left to right, then right to left
       from its seed) chaining each peak to the closest peak in the next
       strip, within `step_window` px -- small enough to reject jumping to
       an unrelated line, large enough to follow real curvature
       accumulating gradually strip to strip (as opposed to needing one
       big window from a single fixed reference point, which is what
       actually failed here first).
    4. Keep only chains present in at least `presence_frac` of strips --
       a real table rule should be traceable across most of the page; a
       stray peak from text baselines/underlines will not chain
       consistently.
    5. Gap-fill: a global `presence_frac=0.7` was found (2026-08-26,
       second pilot page) to sometimes reject genuine lines -- a chunk of
       strips near the table's left edge (possibly a shadow or margin
       artifact specific to that page's crop) failed to detect peaks for
       the bottom half of the table specifically, pulling two real,
       evenly-spaced, otherwise-well-detected lines' presence below 0.7
       even though most strips across the width saw them clearly. Simply
       lowering presence_frac globally fixed that page but broke a
       DIFFERENT already-working page (26 spurious rows appeared on the
       first pilot page instead of the correct 20) -- so instead, after
       the strict pass above, gaps between the surviving curves that are
       conspicuously larger than the page's own median row spacing
       (>1.6x) get a second, targeted look: chains already rejected by
       the strict threshold are re-checked, at a looser presence floor,
       but ONLY if they fall inside one of those specific oversized gaps.
       A large gap is itself the evidence something's missing there --
       relaxing precision only in the region that evidence points to
       recovers real lines without reopening the door to noise on pages
       that don't have this problem.

       Presence-percentage alone turned out not to be enough to keep this
       precise, though: measured directly (2026-08-26) on a confirmed
       false split -- a spurious boundary the gap-fill pass inserted
       inside one row's own legitimately tall, multi-line content -- it
       was seen by 62% of strips, which sits BETWEEN two genuine missed
       lines on a different page (60% and 68%). Those ranges overlap, so
       no presence threshold can cleanly separate a real missing line from
       this kind of false one.

       Tried and rejected (2026-08-26): gating gap-fill candidates on
       whether column 1 (the date column) shows ink just below the
       candidate y, on the theory that every real row starts with a
       printed date there while a mid-paragraph false split wouldn't.
       Measured directly, it came out BACKWARDS -- the false split showed
       MORE ink there (0.05-0.14) than the genuine misses did (0.01-0.03)
       -- because `_table_x_bounds` only gives a rough margin-trimmed
       table extent, not real column boundaries, so that slice was partly
       landing on a vertical grid-line's shadow rather than actual date
       text. Pinning down real column boundaries precisely enough to fix
       this is the same hard sub-problem `_table_x_bounds` already
       documents abandoning, and doing it per-page would fight this
       module's goal of generalizing to scans added later without manual
       recalibration each time. Not pursued further -- the accepted
       tradeoff instead (see docs/eval/known_issues.md #1) is that an
       occasional false split like this is low-cost (it only fragments
       one date's own content across two API calls, no cross-date mixing)
       and can be caught downstream by a cheap QC check rather than
       prevented upstream.

    Returns curves sorted top to bottom, each an array of length
    gray.shape[1] (one y per column, linearly interpolated across strips;
    a strip a chain didn't reach has its y filled by interpolation, not
    left blank).
    """
    chains, strip_centers, _binary, _x0, _x1 = _build_chains(
        gray, peak_height=peak_height, min_row_gap=min_row_gap,
        n_strips=n_strips, step_window=step_window)
    W = gray.shape[1]

    min_presence = int(n_strips * presence_frac)
    kept_chains = [c for c in chains if len(c) >= min_presence]
    kept_chains.sort(key=lambda c: np.mean(list(c.values())))

    # Merge near-duplicate chains -- two chains whose mean y lands within
    # min_row_gap of each other cannot both be real, distinct row
    # boundaries (min_row_gap already means exactly that everywhere else
    # in this function, via _find_peaks' per-strip collapsing). Found
    # 2026-08-26 testing a whole season rather than the 2 hand-picked
    # pilot pages: the same real line sometimes produces two separate
    # surviving chains a few pixels apart (4.8px, 10px seen in practice)
    # when two nearby seed strips' chain-walks drift apart slightly
    # instead of converging onto the same peaks. Keep whichever chain has
    # wider strip coverage (more strips agreeing on it -- more reliable),
    # drop the other.
    merged: list[dict[int, int]] = []
    for c in kept_chains:
        c_mean = np.mean(list(c.values()))
        dup_idx = next((i for i, m in enumerate(merged)
                         if abs(np.mean(list(m.values())) - c_mean) < min_row_gap), None)
        if dup_idx is None:
            merged.append(c)
        elif len(c) > len(merged[dup_idx]):
            merged[dup_idx] = c
    kept_chains = sorted(merged, key=lambda c: np.mean(list(c.values())))
    curves = [_chain_to_curve(c, strip_centers, W) for c in kept_chains]

    # Gap-fill pass: `presence_frac` rejects real lines a chunk of strips
    # (often near a page edge -- shadow, margin artifact) failed to see,
    # confirmed 2026-08-26 on a second pilot page (see docstring point 4).
    # Rather than lowering presence_frac globally, which recovers those
    # but also lets real noise through elsewhere on other pages, only
    # relax it inside gaps that are themselves the evidence something's
    # missing: a gap conspicuously larger than the page's own typical row
    # spacing. Chains already rejected above are still sitting in `chains`
    # -- re-scan those (not a fresh detection pass) for any whose mean y
    # falls inside such a gap, at a looser presence floor.
    if len(curves) >= 3:
        gaps = [b.mean() - a.mean() for a, b in zip(curves, curves[1:])]
        median_gap = float(np.median(gaps))
        relaxed_presence = max(3, int(n_strips * presence_frac * 0.5))
        for idx in range(len(gaps) - 1, -1, -1):
            if gaps[idx] < median_gap * 1.6:
                continue
            lo, hi = curves[idx].mean(), curves[idx + 1].mean()
            candidates = [c for c in chains
                          if len(c) >= relaxed_presence and lo + step_window < np.mean(list(c.values())) < hi - step_window]
            for c in candidates:
                if not any(abs(np.mean(list(c.values())) - existing.mean()) < min_row_gap for existing in curves):
                    curves.insert(idx + 1, _chain_to_curve(c, strip_centers, W))

    curves.sort(key=lambda c: c.mean())

    # Drop scan-boundary artifacts -- a chain sitting right at the image's
    # own top/bottom edge is the photographed book cover/binding, not a
    # printed table line, confirmed 2026-08-27 on a raw (non-ScanTailor)
    # scan: a 40/40-strip-presence chain at y=1 turned out to be the book
    # cover material visible above the actual page, and having it stand in
    # as the header's top boundary pulled the page's own date-range
    # caption ("30 августа...15 сентября") into the header block reattached
    # to every row crop -- which then leaked into a few rows' date_text
    # ("30"/"15" showing up as wrong dates on unrelated rows). A margin
    # this tight (near-zero, not just "small") is never real printed
    # content given these scans' generous margins, so it's safe to drop
    # outright rather than trying to relax/adjust it.
    # `drop_edge_artifacts=False` (2026-09-01, docs/eval/known_issues.md
    # #68 addendum) -- `_detect_vertical_dividers` reuses this function on
    # a transposed image, where "near y=0/H" means "near the crop's own
    # left/right pixel edge", not "near the photographed book's top/bottom
    # edge". Those are NOT the same kind of artifact: a horizontal row
    # line photographed right at the top/bottom of a scan really is almost
    # always book-cover material (confirmed 2026-08-27, see above), but a
    # vertical table's own left/right border can legitimately sit within a
    # few pixels of the crop's edge on a tightly-cropped page -- confirmed
    # directly on repertoire_1898-99_p012: the real left border chained
    # with 33/40 strip presence (stronger than either divider the page DID
    # keep) at x=1, and dropping it here is what caused
    # `_detect_vertical_dividers` to fall one short of the 3-divider
    # minimum. `_detect_vertical_dividers` has its own, separate margin
    # filter (via `_table_x_bounds`) for the vertical case, so it opts out
    # of this block entirely rather than needing a second edge-margin
    # constant tuned for a different axis.
    if drop_edge_artifacts:
        H = gray.shape[0]
        edge_margin = max(10, int(H * 0.01))
        curves = [c for c in curves if edge_margin <= c.mean() <= H - edge_margin]

    return curves


#: Every genuine date column measured directly across the whole test set
#: (2026-09-01, docs/eval/known_issues.md #68 addendum) came out 175-185px
#: wide -- repertoire_1898-99_p029: 182px, p008: 176px, p014: 176px, p024:
#: 176px -- while every genuine theater column measured 508-598px, a clean,
#: non-overlapping split. Density (ink-fraction) turned out NOT to separate
#: reliably here: a margin segment contaminated by a photographed fingertip
#: or the book's own dark spine can read as dense as, or denser than, real
#: text (p008's true-margin segment measured 16.45% ink, well inside the
#: range real date/theater columns occupy on other pages), so no single
#: density ratio -- tried from 1.2 to 2.5 -- separated every confirmed case
#: without also misclassifying another one. Column width doesn't have this
#: problem: it's what the table's own typesetting fixes, not a function of
#: what a camera or thumb happened to catch.
_DATE_COLUMN_WIDTH_RANGE = (100, 300)


def _prune_edge_artifact_dividers(binary: np.ndarray, dividers: list[np.ndarray],
                                   W: int, density_ratio: float = 1.8
                                   ) -> list[np.ndarray]:
    """Drops a leading divider that's actually the table's own outer-left
    border (not a real date/theater-1 boundary), and a trailing divider
    whose adjacent edge segment is a density outlier -- two different
    tests for two different failure shapes, confirmed directly on real
    pages (2026-09-01, docs/eval/known_issues.md #68 addendum).

    LEFT: if the segment right after the first divider is a plausible
    date-column width (`_DATE_COLUMN_WIDTH_RANGE`), the first divider is
    almost certainly the true outer-left border rather than the
    date/theater-1 boundary -- a real date column only ever appears
    immediately after the true left border, never after an internal
    divider (which is always followed by a full theater column instead).
    Density was tried first here and rejected: it can't tell a
    contaminated-but-blank margin from real text (see
    `_DATE_COLUMN_WIDTH_RANGE`'s docstring), but a date column's width is
    fixed by the table's own typesetting and isn't affected by a
    fingertip or spine shadow landing in the margin next to it.

    RIGHT: no analogous "next segment looks like X" test applies -- past
    the table's real right border there's just margin or the photographed
    book spine, not a second predictably-sized column -- so this side
    keeps the density-outlier test: repertoire_1898-99_p029's and
    repertoire_1898-99_p037's rightmost segment, independently, both read
    ~31-33% ink (photographed spine), far above the ~4-9% band every
    genuine column segment on those pages sits in; compared against the
    MEDIAN of the page's own middle segments, not a fixed global
    percentage, since ink density varies with how text-dense a given
    season's typesetting is.

    Drops at most one divider per side, both decided from state computed
    up front rather than a loop that re-merges a pruned edge into its
    neighbor and re-tests the growing segment -- an earlier version did
    exactly that re-merge-and-recheck on the right side, and it cascaded
    on both p029 and p037: once the true binding-artifact segment got
    merged into its neighbor after one prune, the merged segment's
    average was still pulled high enough to re-trigger "outlier" on the
    next pass too, eating a second, genuinely real divider along with it
    (confirmed by tracing both pages by hand)."""
    xs = sorted(float(d.mean()) for d in dividers)
    bounds = [0.0] + xs + [float(W)]
    n_seg = len(bounds) - 1
    if n_seg <= 2:
        return dividers

    if _DATE_COLUMN_WIDTH_RANGE[0] <= (bounds[2] - bounds[1]) <= _DATE_COLUMN_WIDTH_RANGE[1]:
        xs = xs[1:]
        bounds = [0.0] + xs + [float(W)]
        n_seg = len(bounds) - 1
        if n_seg <= 2:
            return [d for d in dividers if float(d.mean()) in set(xs)]

    def _density(a: float, b: float) -> float:
        return binary[:, int(a):int(b)].mean() / 255.0

    mid_densities = [_density(bounds[i], bounds[i + 1]) for i in range(1, n_seg - 1)]
    median_mid = float(np.median(mid_densities))
    lo, hi = median_mid / density_ratio, median_mid * density_ratio

    if not (lo <= _density(bounds[-2], bounds[-1]) <= hi) and xs:
        xs = xs[:-1]

    kept = set(xs)
    return [d for d in dividers if float(d.mean()) in kept]


def _detect_vertical_dividers(gray: np.ndarray, presence_frac: float = 0.45,
                               **detect_kwargs) -> list[np.ndarray]:
    """Detects the table's vertical column-divider rules (date column |
    theater 1 | theater 2 | ...), as curves in y rather than fixed
    x-positions -- these scans have the same fold-proximity sway
    vertical lines as horizontal ones, confirmed directly (2026-09-01):
    a naive fixed-x column-darkness sum tops out around 45% coverage
    even for the strongest real divider, far short of a continuous
    line, because the line's x-position drifts as y varies and a single
    x-column only catches part of it.

    Reuses `_detect_line_curves` on a *transposed* image rather than a
    separate implementation -- a vertical line's x-sway as a function of
    y becomes a horizontal line's y-sway as a function of x once
    transposed, exactly the shape that function already handles. The
    caller is responsible for transposing back (a curve's index i here
    is the divider's x-position at original-image row i).

    `presence_frac=0.45` is deliberately lower than `_detect_line_curves`'s
    own 0.7 default (passed only for the vertical case, row detection is
    untouched) -- confirmed directly (2026-09-01) that a genuine internal
    divider can chain as low as 19/40 (47.5%) strip presence
    (repertoire_1898-99_p024's date/theater-1 boundary, missed entirely
    at the first value tried, 0.55/28-of-40, and only found by directly
    inspecting the raw chain list under `_build_chains` when p024's
    resulting date crop turned out to silently contain a whole extra
    theater's content -- docs/eval/known_issues.md #68 addendum), while
    every noise candidate measured across the pages checked tops out at
    11/40 (27.5%) -- still a comfortable gap below 0.45. 0.7 was tuned for
    HORIZONTAL row lines, which run through mostly-open table cells;
    vertical dividers cut through print-dense columns instead, so more
    strips get their peak-finding thrown off by nearby text and a lower
    floor is needed for the same underlying confidence level.

    2026-09-01 redesign (docs/eval/known_issues.md #68 addendum): only
    INTERNAL column dividers (date|theater-1, theater-1|theater-2, ...)
    are wanted here -- deliberately NOT the table's own outer left/right
    border. Detecting the true outer border reliably turned out to be
    the fragile part, not a detail to tune around: on
    repertoire_1898-99_p012/p008/p014 (whole-season test) the real left
    border was undetectable under any fixed-fraction-of-width tolerance,
    because its crop margin is essentially zero (~1px) versus ~200px on
    repertoire_1898-99_p029/p037 -- column margins vary across pages the
    same way row heights do (RG, 2026-09-01), so no single tolerance
    constant covers both regimes. On repertoire_1898-99_p024, the same
    fragility went further than a raised-ValueError failure: the wrong
    divider pair got treated as the outer border, and `detect_columns`
    silently produced a THEATER column (visually confirmed:
    "Александринскій театръ." full of works/receipts) where the
    date-only crop was supposed to be -- a wrong-but-plausible-looking
    result, worse than an honest failure.

    Internal dividers don't have this fragility: each sits between two
    printed columns with strong contrast on both sides, and every page
    checked so far (including all three "column_detect_failed" pages)
    detects them with high confidence. `detect_columns` no longer needs
    the outer border precisely located at all -- like its existing
    date_pad/theater_pad padding, it now just crops out to the image's
    own left/right edge for the outermost boundary, which is harmless
    slack rather than a precision requirement.

    Two filtering passes, in order: (1) `_table_x_bounds`'s plain [x0,
    x1] estimate drops gross margin/binding-edge noise (confirmed 2026-
    09-01: raw detection on a 3-theater page finds spurious candidates
    just past x1, ~100px apart vs. ~500px+ between real dividers --
    consistent with a single physical feature, not genuine columns); (2)
    `_prune_edge_artifact_dividers` catches what survives pass 1 anyway
    -- on repertoire_1898-99_p029/p037, BOTH the true outer-left border
    (a real, strongly-detected line, just not one this function wants)
    and a binding-shadow artifact on the right land comfortably inside
    [x0, x1] and need the density-outlier check, not a position cutoff,
    to be told apart from real columns."""
    gray_t = gray.T.copy()
    curves_t = _detect_line_curves(gray_t, drop_edge_artifacts=False,
                                    presence_frac=presence_frac, **detect_kwargs)
    binary = _binarize(gray)
    x0, x1 = _table_x_bounds(binary)
    bounded = [c for c in curves_t if x0 <= c.mean() <= x1]
    return _prune_edge_artifact_dividers(binary, bounded, gray.shape[1])


@dataclass
class ColumnCrop:
    """One theater's isolated column, paired with the date column (no gap
    between them -- RG's fix, 2026-09-01, for the off-by-one date-
    boundary shift a composite crop with an intervening theater skipped
    over was found to cause: date_crop and theater_crop are written
    SEPARATELY here rather than composited, specifically so a caller can
    read them as two independent extractions and match rows by list
    position rather than asking the model to re-attribute a date to
    theater content that's visually far from its own date label."""
    theater_index: int  # 0-based, left to right
    date_image_path: str
    theater_image_path: str


def detect_columns(image_path: Path, out_dir: Path,
                    date_pad: int = 120, theater_pad: int = 15,
                    dividers_frac: list[float] | None = None,
                    date_side: str = "left") -> list[ColumnCrop]:
    """Detects the table's vertical column dividers and writes one
    (date_column_image, theater_column_image) pair per theater column --
    see `ColumnCrop`'s docstring for why these are separate files, not
    one composited image. The SAME date-column crop is reused for every
    theater (real vertical dividers only need detecting once per page).

    `date_pad` is generous by default and asymmetric from `theater_pad`
    on purpose: the date column's own right edge needs enough padding to
    fully include the sideways-printed УТРО/ВЕЧ session-label sub-column
    sitting just inside it. A first attempt at date_pad=15 (matching
    theater_pad) clipped that label almost entirely, and a date-only
    extraction silently undercounted every compound row as a result
    (found and fixed 2026-09-01, docs/eval/known_issues.md #68 addendum)
    -- this default carries that fix forward rather than reintroducing
    the same bug at the next page tested.

    Does not itself call the model -- pairs with a caller (RG's
    date/theater-split extraction design) that reads `date_image_path`
    once for the date sequence and `theater_image_path` once per theater
    for that theater's content, then matches the two by list position.

    2026-09-01 redesign (docs/eval/known_issues.md #68 addendum): only
    the INTERNAL dividers (date|theater-1, theater-1|theater-2, ...) are
    detected now -- the table's own outer left/right border is no longer
    needed at all. The date crop's left edge and the last theater crop's
    right edge simply extend to the image's own edge instead, exactly
    the same generous-padding tolerance already used for date_pad/
    theater_pad on every other boundary here. See
    `_detect_vertical_dividers`'s docstring for why: detecting the true
    outer border reliably was the fragile part (column margins vary
    across pages the same way row heights do -- RG, 2026-09-01), and on
    one page (repertoire_1898-99_p024) that fragility didn't just fail
    loudly, it silently produced a THEATER column where the date crop
    should have been.

    2026-09-08: `dividers_frac` supplies divider positions directly, as
    fractions of image width, instead of detecting them per page -- see
    docs/repertoire_column_bounds.json. Within a season (and, for
    single-page seasons, a page parity) positions vary by only 1-2% of
    width against columns 17-25% wide, so a measured per-group constant
    is steadier than per-page detection, which finds the right divider
    count on only 31/40 pages of a season. Detection stays the default.

    `date_side` exists because the two formats put the date column on
    opposite sides: RIGHT on the two-page-spread seasons (1890-91..
    1897-98), LEFT from 1898-99 on. This function previously assumed
    left unconditionally, which silently mis-sliced every spread page --
    its date crop would have held a theater's content."""
    out_dir.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    W = img.shape[1]
    if date_side not in ("left", "right"):
        raise ValueError(f"date_side must be 'left' or 'right', got {date_side!r}")

    if dividers_frac is not None:
        if len(dividers_frac) < 2:
            raise ValueError(
                f"{image_path.name}: dividers_frac needs at least 2 positions, "
                f"got {len(dividers_frac)}")
        xs = [int(round(f * W)) for f in sorted(dividers_frac)]
        lo = hi = xs                  # a constant divider has no min/max spread
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        dividers = _detect_vertical_dividers(gray)
        if len(dividers) < 2:
            raise ValueError(
                f"{image_path.name}: only found {len(dividers)} internal column "
                f"divider(s), need at least 2 (date/theater-1 boundary plus at "
                f"least one theater/theater boundary) -- detection likely failed "
                f"on this page, inspect before trusting output"
            )
        lo = [int(d.min()) for d in dividers]
        hi = [int(d.max()) for d in dividers]

    n_div = len(lo)
    if date_side == "left":
        date_span = (0, min(W, hi[0] + date_pad))
        bounds = [(max(0, lo[i] - theater_pad),
                   min(W, hi[i + 1] + theater_pad) if i + 1 < n_div else W)
                  for i in range(n_div)]
    else:
        date_span = (max(0, lo[-1] - date_pad), W)
        bounds = [(0 if i == 0 else max(0, lo[i - 1] - theater_pad),
                   min(W, hi[i] + theater_pad))
                  for i in range(n_div)]

    date_crop = img[:, date_span[0]:date_span[1]]
    date_path = out_dir / f"{image_path.stem}__dateonly.png"
    cv2.imwrite(str(date_path), date_crop)

    results = []
    for i, (x0_th, x1_th) in enumerate(bounds):
        theater_crop = img[:, x0_th:x1_th]
        theater_path = out_dir / f"{image_path.stem}__theateronly_{i}.png"
        cv2.imwrite(str(theater_path), theater_crop)
        results.append(ColumnCrop(
            theater_index=i,
            date_image_path=str(date_path),
            theater_image_path=str(theater_path),
        ))

    manifest_path = out_dir / f"{image_path.stem}__columns_manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def analyze_page(image_path: Path, **detect_kwargs) -> PageAnalysis:
    """Runs full automatic detection and keeps the underlying chains
    around for a possible human correction pass. This is the entry point
    for the review workflow: `debug_visualize(analysis=...)` to show RG
    the numbered curves against the scan, `insert_row_boundary`/
    `delete_row_boundary` to apply what RG finds, then
    `detect_rows(analysis=...)` to crop from the corrected result."""
    gray = cv2.cvtColor(cv2.imread(str(image_path)), cv2.COLOR_BGR2GRAY)
    if gray is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    chains, strip_centers, binary, x0, x1 = _build_chains(gray, **{
        k: v for k, v in detect_kwargs.items()
        if k in ("peak_height", "min_row_gap", "n_strips", "step_window")
    })
    curves = _detect_line_curves(gray, **detect_kwargs)
    return PageAnalysis(image_path=image_path, gray=gray, binary=binary, x0=x0, x1=x1,
                         chains=chains, strip_centers=strip_centers, curves=curves)


def insert_row_boundary(analysis: PageAnalysis, after_index: int,
                         relaxed_presence_frac: float = 0.35, min_row_gap: int = 100,
                         step_window: int = 30) -> PageAnalysis:
    """Applies a human-reported missing boundary: re-scans the SAME
    chains `_detect_line_curves` already built (including ones its
    presence-filter rejected) for the best candidate strictly between
    `curves[after_index]` and `curves[after_index + 1]`, at a relaxed
    presence floor -- the identical mechanism the automatic gap-fill pass
    uses for an oversized gap, just triggered by a human pointing at the
    debug-visualize image instead of the gap-size heuristic. Raises if
    nothing crosses even the relaxed floor in that range -- that means
    the real line is either genuinely not there or too faint for this
    mechanism at all, not something to silently paper over.

    `after_index=-1` looks above `curves[0]`; `after_index` at the last
    curve's index looks below it."""
    curves = analysis.curves
    lo = curves[after_index].mean() if after_index >= 0 else -1.0
    hi = curves[after_index + 1].mean() if after_index + 1 < len(curves) else float(analysis.gray.shape[0]) + 1.0
    n_strips = len(analysis.strip_centers)
    relaxed_presence = max(3, int(n_strips * relaxed_presence_frac))
    candidates = [c for c in analysis.chains
                  if len(c) >= relaxed_presence
                  and lo + step_window < np.mean(list(c.values())) < hi - step_window]
    if not candidates:
        raise ValueError(
            f"no candidate line found between curve {after_index} (y={lo:.0f}) and "
            f"curve {after_index + 1} (y={hi:.0f}) even at a relaxed presence floor of "
            f"{relaxed_presence}/{n_strips} strips -- inspect this range directly before "
            f"assuming the fix is just a looser threshold"
        )
    best = max(candidates, key=len)
    new_curve = _chain_to_curve(best, analysis.strip_centers, analysis.gray.shape[1])
    new_curves = sorted(curves + [new_curve], key=lambda c: c.mean())
    corrections = analysis.corrections + [{
        "action": "insert", "after_index": after_index,
        "y": float(new_curve.mean()), "strip_presence": len(best),
    }]
    return PageAnalysis(image_path=analysis.image_path, gray=analysis.gray, binary=analysis.binary,
                         x0=analysis.x0, x1=analysis.x1, chains=analysis.chains,
                         strip_centers=analysis.strip_centers, curves=new_curves,
                         corrections=corrections)


def delete_row_boundary(analysis: PageAnalysis, index: int) -> PageAnalysis:
    """Applies a human-reported false-positive boundary (e.g. a
    mid-paragraph false split like the one documented in
    _detect_line_curves' docstring) -- just drops `curves[index]`."""
    removed_y = float(analysis.curves[index].mean())
    new_curves = [c for i, c in enumerate(analysis.curves) if i != index]
    corrections = analysis.corrections + [{"action": "delete", "index": index, "y": removed_y}]
    return PageAnalysis(image_path=analysis.image_path, gray=analysis.gray, binary=analysis.binary,
                         x0=analysis.x0, x1=analysis.x1, chains=analysis.chains,
                         strip_centers=analysis.strip_centers, curves=new_curves,
                         corrections=corrections)


def _dewarp_band(img: np.ndarray, top_curve: np.ndarray, bottom_curve: np.ndarray,
                  pad_top: int = 0, pad_bottom: int = 0) -> np.ndarray:
    """Straightens the (possibly bowed) band between two curves into a
    rectangular image, by resampling each column independently along the
    local curve height -- not a full 2D perspective transform, since the
    distortion observed on these scans is vertical bowing that varies with
    x, not horizontal shear."""
    H, W = img.shape[:2]
    top = np.clip(top_curve - pad_top, 0, H - 1)
    bottom = np.clip(bottom_curve + pad_bottom, 0, H - 1)
    band_height = int(np.median(bottom - top))
    band_height = max(band_height, 10)

    map_x = np.tile(np.arange(W, dtype=np.float32), (band_height, 1))
    map_y = np.empty((band_height, W), dtype=np.float32)
    row_frac = np.linspace(0, 1, band_height)
    for x in range(W):
        map_y[:, x] = top[x] + row_frac * (bottom[x] - top[x])

    return cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_REPLICATE)


def _adaptive_pads(row_boundaries: list[np.ndarray], row_pad: int,
                    min_row_pad: int = 4, adaptive_pad_frac: float = 0.12) -> list[float]:
    """One padding amount per boundary line (length = len(row_boundaries)),
    used symmetrically as pad_bottom for the row above a line and pad_top
    for the row below it -- both sides of a shared line always agree on
    how far it's extended.

    A flat `row_pad` on every boundary was tested 2026-08-27 (RG's
    request, after a boundary-adjacent receipts figure got clipped between
    two crops) and found unsafe: on a page's shortest row (95px, well
    under 2x a 25px flat pad), the padding pulled in several full title
    lines from the neighboring row -- real cross-date content in frame,
    exactly what row isolation exists to prevent, not just a harmless
    trailing fragment. Fixed by scaling each boundary's padding down when
    either row it touches is short: capped at `adaptive_pad_frac` (12%) of
    the SHORTER of the two adjacent row heights, floored at `min_row_pad`
    so even a very short row still gets a little safety margin. The two
    outer boundaries (top of the first row, bottom of the last) have no
    real neighboring row to intrude on -- header/page margin only -- so
    they always get the full `row_pad`."""
    n_bounds = len(row_boundaries)
    heights = [float(row_boundaries[i + 1].mean() - row_boundaries[i].mean())
               for i in range(n_bounds - 1)]
    pads = [float(row_pad)] * n_bounds
    for i in range(1, n_bounds - 1):
        shorter = min(heights[i - 1], heights[i])
        pads[i] = max(min_row_pad, min(row_pad, adaptive_pad_frac * shorter))
    return pads


def detect_rows(image_path: Path, out_dir: Path, header_line_count: int = 1,
                 row_pad: int = 25, analysis: PageAnalysis | None = None,
                 presence_frac: float = 0.5,
                 outer_top_border: bool = True) -> list[RowCrop]:
    """Main entry point. Detects grid lines on the page (or uses an
    already-reviewed/corrected `analysis` from `analyze_page` +
    `insert_row_boundary`/`delete_row_boundary` -- pass one in to crop
    from a human-confirmed boundary set instead of the raw automatic one),
    treats the first `header_line_count` interior lines below the outer
    top border as the theater-column header block, and every line after
    that as a row boundary. Writes one dewarped, header-reattached image
    per row to out_dir, named f"{image_path.stem}__row{N:03d}.png". If
    `analysis.corrections` is non-empty, also writes
    f"{image_path.stem}__corrections.json" alongside the manifest -- an
    audit trail of what a human changed and why, same rationale as
    docs/query_log.md and the parse_and_validate.py fix-tables.

    `row_pad` is now an adaptive CEILING, not a flat amount applied
    everywhere -- see `_adaptive_pads`. Default raised from 4 to 25
    (2026-08-27) after a real boundary-adjacent receipts figure was found
    clipped between two crops with the old thin padding; a flat 25px
    fixed that case but was then found unsafe on a page's shortest row
    (95px) -- pulled in several full title lines from the neighboring
    row. `_adaptive_pads` scales the padding down on short rows instead.

    `header_line_count=1` is the default confirmed against the pilot page
    (2026-08-26, docs/eval/known_issues.md #1): the header is just the
    single rule below the theater-name row (curves[0]->curves[1]) -- the
    lighter divider between the city-group title line ("С.-Петербургскіе
    театры.") and the theater-name line often isn't strong enough to
    register as its own detected curve, so it doesn't get counted
    separately here. This was originally miscalibrated at 2 (assuming
    that divider always registers) before `_detect_line_curves`'s
    missed-line bug was fixed -- with lines actually missing, 1 vs 2
    couldn't be told apart from the symptoms alone. Still NOT confirmed
    universal across every page layout/era -- pass a different value, or
    extend this function to auto-detect the header boundary (e.g. by
    locating the title-line/theater-name divider directly when it IS
    detected), if a future pilot page finds 1 doesn't hold.

    `presence_frac=0.5` is deliberately lower than `_detect_line_curves`'s
    own 0.7 default (2026-09-01, docs/eval/known_issues.md #68 addendum)
    -- the same class of bug already found and fixed for
    `_detect_vertical_dividers` this session, on the other axis. Confirmed
    directly: on `repertoire_1898-99_p012`, real row boundaries at 42.5%,
    52.5%, and 57.5% strip presence were all being dropped at 0.7, leaving
    only 2 detected row crops for the whole page -- one spanning 1,245px,
    covering roughly ten real dated rows in a single crop. That's the
    EXACT failure mode row isolation exists to prevent (see this module's
    own top-of-file docstring): a fresh whole-season row-level extraction
    run against that oversized crop reproduced the original misattribution
    bug, with several dates' receipts duplicated and shifted one row
    against the page baseline, caught via `quality_checks.py`'s
    cross-extraction check. Confirmed noise stays under ~22.5% presence on
    every page checked (`repertoire_1898-99_p012`, `p014`, `p029`, `p037`),
    so 0.5 leaves a comfortable margin on both sides. Re-verified directly
    against the two already-validated pages, `p029` and `p037`: both
    detect the EXACT SAME curves at 0.5 as at 0.7 -- this lowers the floor
    only where it was already too strict, it doesn't loosen anything on
    pages that were already working."""
    out_dir.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    if analysis is not None:
        curves = analysis.curves
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        curves = _detect_line_curves(gray, presence_frac=presence_frac)
    # `outer_top_border=False` means the table's own outer top rule is not in
    # frame -- which is exactly what pipeline/crop_to_table.py produces, since
    # a crop tight enough to exclude fingers and the fore-edge also cuts the
    # table's border. Without this flag a cropped page silently mis-slices:
    # curves[0] is then the HEADER-BOTTOM rule, so the band pasted onto every
    # row crop as "the header" is actually the first row's content, and every
    # row shifts up by one. That is a correctness bug, not just an off-by-one
    # in the row count. Same principle as detect_columns' 2026-09-01 redesign
    # (known_issues.md #68): depend on interior rules, let the outer edge be
    # the image's own edge.
    if outer_top_border:
        min_curves = header_line_count + 2
    else:
        if header_line_count < 1:
            raise ValueError("outer_top_border=False requires header_line_count >= 1")
        min_curves = header_line_count + 1
    if len(curves) < min_curves:
        raise ValueError(
            f"{image_path.name}: only found {len(curves)} grid line(s), "
            f"need at least {min_curves} (header lines + at "
            f"least one row's top/bottom boundary) -- detection likely "
            f"failed on this page, inspect before trusting output"
        )

    if outer_top_border:
        header_bottom_curve = curves[header_line_count]
        header_top_curve = curves[0]
    else:
        header_bottom_curve = curves[header_line_count - 1]
        header_top_curve = np.zeros(img.shape[1], dtype=curves[0].dtype)
    header_img = _dewarp_band(img, header_top_curve, header_bottom_curve, pad_top=2, pad_bottom=2)

    results = []
    row_boundaries = (curves[header_line_count:] if outer_top_border
                      else curves[header_line_count - 1:])
    boundary_pads = _adaptive_pads(row_boundaries, row_pad)
    for i in range(len(row_boundaries) - 1):
        top_curve = row_boundaries[i]
        bottom_curve = row_boundaries[i + 1]
        row_img = _dewarp_band(img, top_curve, bottom_curve,
                                pad_top=boundary_pads[i], pad_bottom=boundary_pads[i + 1])

        combined = np.vstack([
            cv2.resize(header_img, (row_img.shape[1], header_img.shape[0])),
            row_img,
        ])
        out_path = out_dir / f"{image_path.stem}__row{i+1:03d}.png"
        cv2.imwrite(str(out_path), combined)
        results.append(RowCrop(
            index=i + 1, image_path=str(out_path),
            top_y_range=(int(top_curve.min()), int(top_curve.max())),
            bottom_y_range=(int(bottom_curve.min()), int(bottom_curve.max())),
        ))

    manifest_path = out_dir / f"{image_path.stem}__rows_manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if analysis is not None and analysis.corrections:
        corrections_path = out_dir / f"{image_path.stem}__corrections.json"
        corrections_path.write_text(
            json.dumps(analysis.corrections, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def debug_visualize(image_path: Path, out_path: Path,
                     analysis: PageAnalysis | None = None) -> PageAnalysis:
    """Draws every detected curve on top of the original page image, in a
    distinct color per curve with its index labeled -- this IS the human
    review step of the correction workflow (2026-08-26): RG checks this
    image against the scan and reports any fix by curve index ("missing
    row between curve 8 and 9", "curve 14 is spurious"), which
    `insert_row_boundary`/`delete_row_boundary` then apply. Pass an
    already-corrected `analysis` back in to re-render after a correction
    and confirm it landed right, instead of only ever showing the raw
    automatic result. Also writes f"{image_path.stem}__curves.json" (each
    curve's index and mean y) alongside the image, so a correction can be
    specified/logged by index without re-deriving y-values by eye.

    Returns the PageAnalysis used (freshly built if none was passed in),
    so a caller doing `debug_visualize` as the first step of a review can
    chain straight into `insert_row_boundary`/`delete_row_boundary`
    without a redundant re-analysis."""
    if analysis is None:
        analysis = analyze_page(image_path)
    img = cv2.imread(str(image_path))
    W = analysis.gray.shape[1]
    curves = analysis.curves
    colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255),
              (255, 0, 255), (255, 255, 0), (128, 0, 255), (0, 128, 255)]
    for i, curve in enumerate(curves):
        color = colors[i % len(colors)]
        pts = np.stack([np.arange(W), curve.astype(np.int32)], axis=1)
        cv2.polylines(img, [pts], False, color, thickness=3)
        cv2.putText(img, str(i), (10, int(curve[5])), cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, color, 3)
    cv2.imwrite(str(out_path), img)
    curves_json_path = out_path.parent / f"{image_path.stem}__curves.json"
    curves_json_path.write_text(
        json.dumps([{"index": i, "y": float(c.mean())} for i, c in enumerate(curves)],
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(curves)} curve(s) -> {out_path} (index/y list -> {curves_json_path})")
    return analysis


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--header-line-count", type=int, default=1)
    ap.add_argument("--debug-visualize", action="store_true",
                     help="write an annotated copy of the page showing every "
                          "detected curve, instead of extracting rows")
    args = ap.parse_args()
    if args.debug_visualize:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        debug_visualize(args.image, args.out_dir / f"{args.image.stem}__curves.png")
        return
    rows = detect_rows(args.image, args.out_dir, header_line_count=args.header_line_count)
    print(f"{len(rows)} row(s) detected -> {args.out_dir}")
    for r in rows:
        print(f"  row {r.index}: {r.image_path}")


if __name__ == "__main__":
    main()
