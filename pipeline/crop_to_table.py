"""Crops rendered Repertoire scans to the printed table before row
detection, using ONE hand-set crop per season.

Why per-season and not automatic
--------------------------------
Automatic table-bound detection was attempted four ways this session and
none held up: the near-black backing board reads as ink under `_binarize`,
the page's own dark edge line dominates any max-relative threshold, the
low-ink gaps BETWEEN table columns break a widest-contiguous-run search,
and the holder's fingers are solid ink blobs carrying more mass than the
print. This is the same wall `row_detect._table_x_bounds` documents in its
own docstring -- "physical-scan edge artifacts... dominate a raw
column-darkness scan far more than the actual thin table border does" --
which is why that function does not detect anything at all: it trims a
fixed 8% margin off each edge and always returns 8%-92%.

A season is one book photographed in one sitting, so its geometry is
stable. One crop read by eye off a contact sheet covers the whole season,
which is exactly what ScanTailor's "Apply to All Pages" was doing, without
needing ScanTailor.

Why it matters (measured 2026-09-08, known_issues.md #69): row detection
keeps a line only if it chains across `presence_frac` of the strips
spanning x0..x1. Margin strips that cannot contain a rule drag every real
rule below the threshold. On 1906-07, one hand-set crop applied to all 50
pages took zero-detection pages from 45 to 0 and median detected rows from
0 to 10.

Cropping is NOT universally good and must be validated per season
(`--evaluate`) before adoption:
  1906-07  zero 45 -> 0,  median  0 -> 10   adopt
  1892-93  zero  1 -> 0,  median 10 -> 18   adopt
  1898-99  zero  0 -> 0,  median 12 -> 10   SKIP (already healthy; the
           crop costs the table's outer top/bottom borders, which
           `detect_rows` counts as boundaries)
  1902-03  zero  2 -> 4                     SKIP until bounds are re-read
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

SEASON_RE = re.compile(r"_(\d{4}-\d{2})_")


@dataclass(frozen=True)
class Crop:
    """Fractions of image width/height. Fractions, not pixels, because page
    pixel dimensions vary within a season while the framing does not."""
    x0: float
    x1: float
    y0: float
    y1: float

    def pixels(self, h: int, w: int) -> tuple[int, int, int, int]:
        return (max(0, int(w * self.x0)), min(w, int(w * self.x1)),
                max(0, int(h * self.y0)), min(h, int(h * self.y1)))

    def apply(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        x0, x1, y0, y1 = self.pixels(h, w)
        return img[y0:y1, x0:x1]


def parity_of(page_id: str) -> int | None:
    """Page index parity. Single-page seasons alternate recto/verso, which
    shifts the table sideways within a season crop (RG, 2026-09-08: the
    table sits nearer the gutter, so the wide margin swaps sides), so their
    column positions are keyed by parity."""
    m = re.search(r"_p(\d+)", page_id)
    return int(m.group(1)) % 2 if m else None


def load_column_config(path: Path) -> dict:
    """Column divider positions, keyed "<season>" (spread seasons) or
    "<season>:<parity>" (single-page seasons). Underscore keys are notes."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def column_group_for(page_id: str, columns: dict) -> dict | None:
    """Resolves a page to its column group, preferring the parity-specific
    entry and falling back to a season-wide one."""
    season = season_of(page_id)
    if season is None:
        return None
    par = parity_of(page_id)
    if par is not None and f"{season}:{par}" in columns:
        return columns[f"{season}:{par}"]
    return columns.get(season)


def season_of(page_id: str) -> str | None:
    m = SEASON_RE.search(page_id)
    return m.group(1) if m else None


def crop_for(page_id: str, crops: dict) -> "Crop | None":
    """Resolves a page to its crop, preferring a parity-specific entry.

    Single-page seasons can shift the table sideways between recto and verso
    far enough that one crop per season fits only half the pages. Measured on
    1906-07 (2026-09-08): the season crop x 0.04-0.78 contains the whole
    table on odd pages but slices the third theater off entirely on even
    ones, which scored 80% and 0% column reconciliation respectively. Not all
    seasons need this -- 1898-99 and 1899-00 shift too little to matter -- so
    a parity key is added only where it is needed and the season key remains
    the default.
    """
    season = season_of(page_id)
    if season is None:
        return None
    par = parity_of(page_id)
    if par is not None and f"{season}:{par}" in crops:
        return crops[f"{season}:{par}"]
    return crops.get(season)


def load_config(path: Path) -> dict[str, Crop]:
    """Keys beginning with "_" are notes, not seasons -- the config lives in
    docs/ and is version-controlled, so it documents itself."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: Crop(**v) for k, v in raw.items() if not k.startswith("_")}


def contact_sheet(images: list[Path], out: Path, cols: int = 4,
                  tile_w: int = 620, grid_step: int = 10) -> None:
    """Writes a grid-overlaid contact sheet for reading crop bounds by eye.
    Percentage gridlines are labelled so bounds can be read straight off."""
    tiles = []
    for p in images:
        im = cv2.imread(str(p))
        if im is None:
            continue
        h, w = im.shape[:2]
        t = cv2.resize(im, (tile_w, int(h * tile_w / w)), interpolation=cv2.INTER_AREA)
        H = t.shape[0]
        for pct in range(grid_step, 100, grid_step):
            x, y = int(tile_w * pct / 100), int(H * pct / 100)
            cv2.line(t, (x, 0), (x, H), (0, 0, 255), 1)
            cv2.putText(t, str(pct), (x + 2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1)
            cv2.line(t, (0, y), (tile_w, y), (255, 0, 0), 1)
            cv2.putText(t, str(pct), (3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 0, 0), 1)
        t = cv2.copyMakeBorder(t, 26, 6, 6, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(t, p.stem, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
        tiles.append(t)
    if not tiles:
        raise SystemExit("no readable images for contact sheet")
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0, cv2.BORDER_CONSTANT,
                                value=(255, 255, 255)) for t in tiles]
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    W = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 0, 0, W - r.shape[1], cv2.BORDER_CONSTANT,
                               value=(255, 255, 255)) for r in rows]
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])


def detected_rows(gray: np.ndarray, presence_frac: float = 0.5,
                  outer_top_border: bool = True) -> int:
    """Rows implied by row detection.

    `outer_top_border=False` for a CROPPED page: the crop cuts the table's
    own outer top rule, so one fewer curve bounds the same number of rows.
    Scoring both sides as curves-2 biased every cropped page down by one and
    produced SKIP verdicts that were an artifact of the metric rather than a
    real loss (see detect_rows' matching flag).
    """
    from row_detect import _detect_line_curves
    try:
        n = len(_detect_line_curves(gray, presence_frac=presence_frac))
        return max(0, n - (2 if outer_top_border else 1))
    except Exception:
        return 0


def evaluate(images: list[Path], crop: Crop) -> dict:
    """Compares row detection with and without the crop. This is the gate a
    crop must pass before being adopted -- cropping is not universally
    beneficial (see module docstring)."""
    before, after = [], []
    for p in images:
        im = cv2.imread(str(p))
        if im is None:
            continue
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        before.append(detected_rows(g, outer_top_border=True))
        after.append(detected_rows(cv2.cvtColor(crop.apply(im), cv2.COLOR_BGR2GRAY),
                                    outer_top_border=False))
    b, a = np.array(before), np.array(after)
    return {
        "pages": len(b),
        "zero_before": int((b <= 0).sum()), "zero_after": int((a <= 0).sum()),
        "lt5_before": int((b < 5).sum()), "lt5_after": int((a < 5).sum()),
        "median_before": float(np.median(b)) if len(b) else 0.0,
        "median_after": float(np.median(a)) if len(a) else 0.0,
        "verdict": ("adopt" if (a <= 0).sum() < (b <= 0).sum()
                    or ((a < 5).sum() < (b < 5).sum() and (a <= 0).sum() <= (b <= 0).sum())
                    else "skip"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--season", default=None, help="restrict to one season, e.g. 1906-07")
    ap.add_argument("--config", type=Path, default=None,
                    help="season -> crop bounds JSON; the read-in set for this "
                         "corpus is docs/repertoire_crop_bounds.json")
    ap.add_argument("--contact-sheet", type=Path, default=None,
                    help="write a grid-overlaid sheet for reading bounds by eye, then exit")
    ap.add_argument("--sheet-pages", type=int, default=4)
    ap.add_argument("--evaluate", action="store_true",
                    help="report row detection with/without the crop; adopt nothing")
    ap.add_argument("--out-dir", type=Path, default=None, help="write cropped images here")
    args = ap.parse_args()

    images = sorted(args.images_dir.glob("repertoire_*.png"))
    if args.season:
        images = [p for p in images if season_of(p.stem) == args.season]
    if not images:
        raise SystemExit("no matching images")

    if args.contact_sheet:
        step = max(1, len(images) // args.sheet_pages)
        contact_sheet(images[::step][:args.sheet_pages], args.contact_sheet)
        print(f"contact sheet -> {args.contact_sheet}  "
              f"({min(args.sheet_pages, len(images))} pages; read bounds off the grid)")
        return

    if not args.config:
        raise SystemExit("--config required (or use --contact-sheet first)")
    crops = load_config(args.config)

    by_season: dict[str, list[Path]] = {}
    for p in images:
        by_season.setdefault(season_of(p.stem) or "?", []).append(p)

    for season, pages in sorted(by_season.items()):
        crop = crops.get(season)
        if crop is None:
            print(f"{season:<10} no crop configured -- {len(pages)} page(s) left uncropped")
            continue
        if args.evaluate:
            r = evaluate(pages, crop)
            print(f"{season:<10}{r['pages']:>4}pp  zero {r['zero_before']:>3}->{r['zero_after']:<3} "
                  f"<5rows {r['lt5_before']:>3}->{r['lt5_after']:<3} "
                  f"median {r['median_before']:.0f}->{r['median_after']:.0f}   {r['verdict'].upper()}")
            continue
        if args.out_dir:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            for p in pages:
                im = cv2.imread(str(p))
                cv2.imwrite(str(args.out_dir / p.name), crop.apply(im))
            print(f"{season:<10}cropped {len(pages)} page(s) -> {args.out_dir}")


if __name__ == "__main__":
    main()
