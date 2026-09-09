"""Renders the header band `detect_rows` would paste onto every row crop,
for both `outer_top_border` settings side by side, so the correct one can
be read off by eye and recorded per season.

Why this is not auto-detected: three discriminators were tried on
2026-09-08 and all failed on real pages (known_issues.md #69).
  * distance of the first curve from the crop's top edge -- cannot tell
    "curve0 is the outer border" from "curve0 is the header-bottom rule",
    since both sit near the top;
  * ink density above the first curve -- a page's own date caption
    ("9 октября ... 1903 г.") reads as densely as column headings, and
    letting a caption into the header band leaks into date_text (#50);
  * counting column blocks above the first curve -- headings on
    `1895-96_p002` merge into a single block, scoring the same as a caption.
The header band's structure is a property of the printed format, so it is
configured per season and verified here, exactly as the crop bounds are.

A correct band shows the COLUMN HEADINGS ("Маріинскій | Александринскій |
..." or "Большой театръ. | Малый театръ. | ..."). A wrong one shows row
content (work titles and receipts) or a bare caption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
from row_detect import detect_rows                     # noqa: E402
from crop_to_table import load_config, season_of       # noqa: E402


def header_band(image_path: Path, outer_top_border: bool,
                header_line_count: int, tmp: Path) -> np.ndarray | None:
    """The band `detect_rows` reattaches -- read back off its first row crop,
    which is header-on-top by construction, rather than recomputed here, so
    what is shown is exactly what extraction receives."""
    try:
        crops = detect_rows(image_path, tmp, header_line_count=header_line_count,
                            outer_top_border=outer_top_border)
    except Exception:
        return None
    if not crops:
        return None
    img = cv2.imread(crops[0].image_path)
    return None if img is None else img


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images-dir", type=Path, required=True)
    ap.add_argument("--season", required=True)
    ap.add_argument("--config", type=Path, default=Path("docs/repertoire_crop_bounds.json"),
                    help="crop bounds; the season's crop is applied before checking")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--header-line-count", type=int, default=1)
    ap.add_argument("--band-px", type=int, default=300,
                    help="how much of the row crop's top to show")
    args = ap.parse_args()

    crops_cfg = load_config(args.config)
    crop = crops_cfg.get(args.season)
    images = [p for p in sorted(args.images_dir.glob("repertoire_*.png"))
              if season_of(p.stem) == args.season]
    if not images:
        raise SystemExit(f"no images for season {args.season}")
    step = max(1, len(images)//args.pages)
    images = images[::step][:args.pages]

    tmp = Path(".header_check_tmp"); tmp.mkdir(exist_ok=True)
    tiles = []
    for p in images:
        src = p
        if crop is not None:
            im = cv2.imread(str(p))
            cropped = crop.apply(im)
            src = tmp / f"c_{p.name}"
            cv2.imwrite(str(src), cropped)
        for otb in (True, False):
            band = header_band(src, otb, args.header_line_count, tmp / f"o{otb}")
            label = f"{p.stem[11:]}  outer_top_border={otb}"
            if band is None:
                t = np.full((90, 1500, 3), 255, np.uint8)
                cv2.putText(t, label + "   (detect_rows failed)", (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                h, w = band.shape[:2]
                t = cv2.resize(band[:args.band_px], (1500, int(min(args.band_px, h)*1500/w)),
                               interpolation=cv2.INTER_AREA)
                t = cv2.copyMakeBorder(t, 30, 8, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                cv2.putText(t, label, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 200), 2)
            tiles.append(t)
    W = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, 0, 0, W-t.shape[1], cv2.BORDER_CONSTANT,
                                value=(255, 255, 255)) for t in tiles]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 92])
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
    print(f"{args.season}: {len(images)} page(s) x both settings -> {args.out}")
    print("  correct band shows COLUMN HEADINGS; wrong band shows row content or a caption")


if __name__ == "__main__":
    main()
