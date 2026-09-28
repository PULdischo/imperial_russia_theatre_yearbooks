"""Cut page images into horizontal bands, for a second and third extraction view.

Two samples of the SAME view reproduce 95% of each other's errors; a banded
view reproduces 54% (docs/eval/chunking_test_2026-09-26.md). That decorrelation
is the whole point -- bands are a worse reader on their own (a single banded
pass scores below a full page) and earn their place only as another opinion
for `merge_views.py` to choose among.

Cuts land on the quietest ink row within +-40% of a band height of each
target, so a cut falls in the gutter between printed lines rather than
through one. Each band is padded by a quarter of a band height on the
inward side, so text sitting on a seam appears whole in at least one band.

Usage:
    uv run python pipeline/make_bands.py --manifest outputs/reviews/manifest.csv \
        --images-dir outputs/reviews/images --out-dir outputs/reviews/bands2 --bands 2
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def cut_rows(ink: np.ndarray, height: int, bands: int) -> list[int]:
    """Quietest row near each band boundary -- a gutter, not a line of type."""
    band_h = height / bands
    window = int(0.40 * band_h)
    lo, hi = int(0.04 * height), int(0.96 * height)
    cuts = []
    for b in range(1, bands):
        target = int(height * b / bands)
        span = range(max(lo, target - window), min(hi, target + window))
        cuts.append(min(span, key=lambda y: ink[y]) if len(span) else target)
    return cuts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--bands", type=int, required=True)
    ap.add_argument("--only", nargs="*", default=None, help="page_id(s) only")
    ap.add_argument("--quality", type=int, default=88)
    a = ap.parse_args()

    with open(a.manifest, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if a.only:
        wanted = set(a.only)
        rows = [r for r in rows if r["page_id"] in wanted]

    img_dir = a.out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    out_rows, missing = [], 0

    for n, r in enumerate(rows, 1):
        pid = r["page_id"]
        src = a.images_dir / Path(r["image_file"]).name
        if not src.exists():
            missing += 1
            continue
        im = Image.open(src)
        width, height = im.size
        ink = (255.0 - np.asarray(im.convert("L"), dtype=np.float32)).mean(axis=1)
        bounds = [0] + cut_rows(ink, height, a.bands) + [height]
        pad = int(0.25 * height / a.bands)

        for b in range(a.bands):
            y0 = max(0, bounds[b] - (pad if b else 0))
            y1 = min(height, bounds[b + 1] + (pad if b < a.bands - 1 else 0))
            bid = f"{pid}__band{b}"
            im.crop((0, y0, width, y1)).save(img_dir / f"{bid}.jpg", quality=a.quality)
            out_rows.append({**r, "page_id": bid,
                             "image_file": f"images/{bid}.jpg"})
        im.close()
        if n % 200 == 0:
            print(f"  {n}/{len(rows)} pages banded", flush=True)

    with open(a.out_dir / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    print(f"{len(rows) - missing} pages -> {len(out_rows)} band images "
          f"({a.bands} per page) in {a.out_dir}")
    if missing:
        print(f"{missing} page image(s) missing, skipped", file=sys.stderr)


if __name__ == "__main__":
    main()
