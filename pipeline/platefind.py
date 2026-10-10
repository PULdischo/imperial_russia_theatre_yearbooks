"""Locate halftone plates, then the text band directly beneath each.

The plate is the one thing on these pages that is reliably findable.
Measured on the scans: within a 24px block, the fraction of near-paper
pixels is ~0.99 for blank margin, ~0.86 for body text (sparse black
strokes on paper) and ~0.21-0.27 inside a halftone photo, which covers
its whole area in tone. So `paper fraction < 0.5` separates plate from
everything else with a wide margin, and -- unlike a direct text-line
finder -- it is not fooled by the scan border or the gutter shadow,
because those are dark but narrow.

Paper is ~195 grey on these scans, not white; the threshold is set from
the measured histogram, not assumed.
"""
import numpy as np
from PIL import Image

PAPER = 175      # >= this is paper; measured paper mean is 195-197
BLOCK = 24


def plates(path, min_blocks_frac=0.015):
    im = Image.open(path).convert("L")
    a = np.asarray(im, dtype=np.uint8)
    H, W = a.shape
    gh, gw = H // BLOCK, W // BLOCK
    paper = (a[:gh * BLOCK, :gw * BLOCK] >= PAPER)
    frac = paper.reshape(gh, BLOCK, gw, BLOCK).mean(axis=(1, 3))
    dense = frac < 0.5
    m = max(1, int(0.015 * min(gh, gw)))          # trim border/gutter
    dense[:m] = dense[-m:] = False
    dense[:, :m] = dense[:, -m:] = False

    seen = np.zeros_like(dense, bool)
    out = []
    for y in range(gh):
        for x in range(gw):
            if not dense[y, x] or seen[y, x]:
                continue
            stack, cells = [(y, x)], []
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                    if 0 <= ny < gh and 0 <= nx < gw and dense[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx] = True
                        stack.append((ny,nx))
            if len(cells) < min_blocks_frac * gh * gw:
                continue
            ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
            h = (max(ys)-min(ys)+1); w = (max(xs)-min(xs)+1)
            # a plate is a solid rectangle; a column of dense text is not
            if len(cells) / (h * w) < 0.75:
                continue
            out.append((min(ys)*BLOCK, (max(ys)+1)*BLOCK,
                        min(xs)*BLOCK, (max(xs)+1)*BLOCK))
    out.sort(key=lambda r: (r[0], r[2]))
    return im, out


def caption_band(im, plate, gap=4, height=200, left=40, right=520):
    """The band just under a plate: where this volume prints its captions."""
    y0, y1, x0, x1 = plate
    top = min(im.height, y1 + gap)
    return (max(0, x0 - left), top,
            min(im.width, x1 + right), min(im.height, top + height))
