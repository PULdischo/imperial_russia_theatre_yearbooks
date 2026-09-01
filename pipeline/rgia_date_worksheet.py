"""Cut each опись opening down to just the two columns needed to verify a date
-- «Порядковый №» and «крайние даты» -- so they can be transcribed by hand
without reading a whole spread.

Why by hand: scan-derived dates scored 60.6% exact / 29% wrong against RGIA's
own (rgia_dates_merge.py), so the 720 дела RGIA leaves undated cannot be dated
by model. They can be read by a person in a fraction of the time a full
transcription would take, because only two narrow columns matter.

Each opening is two pages; each page contributes a (numbers | dates) pair.
Output is one tall JPEG per opening, upscaled, plus a CSV stub to type into.

Usage:
    python pipeline/rgia_date_worksheet.py --pages 21,22,23,24,25 \
        --out-dir outputs/rgia_worksheet
"""
from __future__ import annotations

import argparse, csv, re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# fractions of full-spread width, validated against img024/img047 rule lines;
# generous on purpose so page-to-page drift never clips a digit
BANDS = {
    # L_num starts past the dark page edge, and is as wide as R_num -- at
    # 0.000-0.070 it clipped 3-digit дело numbers to two digits.
    "L_num":  (0.012, 0.092), "L_date": (0.308, 0.393),
    "R_num":  (0.492, 0.572), "R_date": (0.800, 0.885),
}
GAP = 14


def rule_lines(im: Image.Image) -> list[float]:
    a = np.asarray(im.convert("L")); h, w = a.shape
    band = (a < 110)[int(h * 0.12):int(h * 0.95), :]
    col = band.sum(axis=0); thr = band.shape[0] * 0.45
    xs = [x for x in range(w) if col[x] > thr]
    groups: list[list[int]] = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 3: groups[-1].append(x)
        else: groups.append([x])
    return [float(np.mean(g)) / w for g in groups]


def build(img_path: Path, scale: float) -> Image.Image:
    im = Image.open(img_path).convert("L")
    w, h = im.size
    strips = []
    for key in ("L_num", "L_date", "R_num", "R_date"):
        a, b = BANDS[key]
        strips.append(im.crop((int(w * a), 0, int(w * b), h)))
    total_w = sum(s.width for s in strips) + GAP * 5
    sheet = Image.new("L", (total_w, h + 40), 255)
    d = ImageDraw.Draw(sheet)
    x = GAP
    for i, (key, s) in enumerate(zip(("L_num", "L_date", "R_num", "R_date"), strips)):
        sheet.paste(s, (x, 34))
        d.text((x + 4, 12), {"L_num": "L  №", "L_date": "L  даты",
                             "R_num": "R  №", "R_date": "R  даты"}[key])
        x += s.width + GAP
        if i == 1: x += GAP           # visual break between the two pages
    if scale != 1:
        sheet = sheet.resize((int(sheet.width * scale), int(sheet.height * scale)),
                             Image.LANCZOS)
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", type=Path, default=Path("pdf/RGIA_F497_Op18/images"))
    ap.add_argument("--pages", required=True, help="image numbers, e.g. 21,22,23")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/rgia_worksheet"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    nums = [int(x) for x in args.pages.split(",")]
    stub = []
    for n in nums:
        src = args.images_dir / f"img{n:03d}.jpg"
        out = args.out_dir / f"worksheet_img{n:03d}.jpg"
        sheet = build(src, args.scale)
        sheet.save(out, quality=90)
        print(f"  {out}  {sheet.size}  (листъ {n-2} old / {n-12} new)")
        stub.append({"image": n, "list_old": n - 2, "delo_no": "", "dates_verbatim": "",
                     "year_start": "", "year_end": "", "notes": ""})

    csv_path = args.out_dir / "dates_to_verify.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(stub[0]))
        w.writeheader(); w.writerows(stub)
    print(f"\ntype into: {csv_path}")


if __name__ == "__main__":
    main()
