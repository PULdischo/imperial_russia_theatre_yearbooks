"""Prepare one RGIA дело (a PDF of photographed pages) for reading and triage.

    uv run python pipeline/rgia_delo_intake.py --pdf ~/Downloads/497-18-159.pdf --delo 159
    uv run python pipeline/rgia_delo_intake.py --pdf ... --delo 159 --enhanced-pdf ~/Downloads/497-18-159_enhanced.pdf

Writes, under outputs/rgia_dela/<delo>/ (gitignored, regenerable from the PDF):
  pages/oNNN.<ext>   the largest embedded image of each PDF page, untouched
  pages/eNNN.jpg     a greyscale, moiré-softened, lighting-flattened copy
  thumbs/pNNN.jpg    520px-wide colour thumbnails, NNN = 1-based PDF page

The page-by-page triage (what each page is about, ballet/editorial flags) is
done afterwards by reading these images and lands in docs/rgia/dela/<delo>.jsonl,
which IS tracked -- it is the durable record; everything here can be rebuilt.

The enhancement is for a human reader at normal zoom. It drops colour (red
ruling, blue pencil, different inks), so letter-level and layer questions
should always go back to the original image.
"""
import argparse
import os
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parent.parent


def enhance(path, out):
    """Photos of a monitor: soften the screen moiré, flatten uneven lighting,
    whiten the paper and darken faint ink without crushing it to black."""
    img = cv2.imread(str(path))
    g = (np.min(img, axis=2).astype(np.float32) * 0.5
         + cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) * 0.5)
    g8 = np.clip(g, 0, 255).astype(np.uint8)
    # moiré is fine texture: non-local means smooths it while keeping stroke edges
    d = cv2.fastNlMeansDenoising(g8, None, h=12, templateWindowSize=7,
                                 searchWindowSize=21).astype(np.float32)
    bg = cv2.morphologyEx(d, cv2.MORPH_CLOSE, np.ones((35, 35), np.uint8))
    bg = cv2.GaussianBlur(bg, (0, 0), 20)
    flat = np.clip(d / np.maximum(bg, 1), 0, 1)  # 1.0 = paper
    lo = np.percentile(flat, 0.5)
    st = np.clip((flat - lo) / (0.97 - lo), 0, 1) ** 1.6
    out8 = (st * 255).astype(np.uint8)
    out8 = cv2.addWeighted(out8, 1.3, cv2.GaussianBlur(out8, (0, 0), 1.5), -0.3, 0)
    cv2.imwrite(str(out), out8, [cv2.IMWRITE_JPEG_QUALITY, 88])


def _page(args):
    pdf, i, outdir = args
    doc = pymupdf.open(pdf)
    ims = doc[i].get_images(full=True)
    if not ims:
        return i, None
    big = max(ims, key=lambda t: t[2] * t[3])  # skip the small viewer-logo image
    x = doc.extract_image(big[0])
    orig = outdir / "pages" / f"o{i:03d}.{x['ext']}"
    orig.write_bytes(x["image"])
    enhance(orig, outdir / "pages" / f"e{i:03d}.jpg")
    im = cv2.imread(str(orig))
    s = 520 / im.shape[1]
    cv2.imwrite(str(outdir / "thumbs" / f"p{i + 1:03d}.jpg"),
                cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 70])
    return i, orig.name


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--delo", required=True)
    ap.add_argument("--out-root", default=str(ROOT / "outputs" / "rgia_dela"))
    ap.add_argument("--enhanced-pdf", help="also assemble the enhanced pages into this PDF")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    pdf = os.path.expanduser(a.pdf)
    outdir = Path(a.out_root) / str(a.delo)
    (outdir / "pages").mkdir(parents=True, exist_ok=True)
    (outdir / "thumbs").mkdir(parents=True, exist_ok=True)
    n = len(pymupdf.open(pdf))
    with Pool(a.workers) as pool:
        done = list(pool.imap(_page, [(pdf, i, outdir) for i in range(n)]))
    blank = [i + 1 for i, name in done if name is None]
    print(f"Д. {a.delo}: {n} PDF pages -> {outdir}")
    if blank:
        print(f"  no image on PDF pages {blank}")

    if a.enhanced_pdf:
        out = pymupdf.open()
        for i in range(n):
            p = outdir / "pages" / f"e{i:03d}.jpg"
            if not p.exists():
                continue
            h, w = cv2.imread(str(p), 0).shape
            pg = out.new_page(width=w * 72 / 300, height=h * 72 / 300)
            pg.insert_image(pg.rect, filename=str(p))
        out.save(os.path.expanduser(a.enhanced_pdf), deflate=True)
        print(f"  enhanced PDF -> {a.enhanced_pdf}")


if __name__ == "__main__":
    main()
