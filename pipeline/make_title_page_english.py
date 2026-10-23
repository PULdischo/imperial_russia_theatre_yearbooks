"""English-language version of the 1891-92 Yearbook title page.

Erases each Russian text line from the full-res scan, rebuilds the paper
underneath (smooth tone + real paper grain borrowed from a blank area), and
typesets the English in the same position, cap height and ink colour.
Ornaments and '1893.' are left untouched.

Usage:
    uv run python pipeline/make_title_page_english.py SRC OUT

SRC is the full-resolution image embedded in page 4 of
`Yearbook Scans - Originals/1891-92 Yearbook/1891-92_Frontpages.pdf`
(4915x5583 px, ~600 dpi); the line boxes below are pixel coordinates in
that image, so a different render will not line up. Uses macOS system
fonts (/System/Library/Fonts). Output last written to
outputs/title_page_english/ and copied to `Sample Yearbook Images for
Presentations/` (2026-10-23).
"""
import sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
SF = "/System/Library/Fonts/Supplemental/"
F = {
    "didot": (SF + "Didot.ttc", 0),
    "avcond": ("/System/Library/Fonts/Avenir Next Condensed.ttc", 7),  # Regular
    "avcond_med": ("/System/Library/Fonts/Avenir Next Condensed.ttc", 5),
    "typew": (SF + "AmericanTypewriter.ttc", 0),  # Regular
    "times": (SF + "Times New Roman.ttf", 0),
    "clar": (SF + "SuperClarendon.ttc", 5),
    "copper": (SF + "Copperplate.ttc", 1),  # Light
    "charter": (SF + "Charter.ttc", 0),
}

img = np.array(Image.open(SRC).convert("RGB")).astype(np.float32)
H, W, _ = img.shape
gray = img.mean(2)

# ---- line specs: (band y0, y1, x0, x1) of the Russian, then English ----
# cap = target cap height in px; track = letterspacing in em; w = max width
LINES = [
    dict(box=(690, 935, 840, 2910), text="YEARBOOK", font="didot", cap=181, track=0.16, bold=1),
    dict(box=(1145, 1360, 270, 3470), text="OF THE IMPERIAL", font="didot", cap=182, track=0.06, bold=1),
    dict(box=(1590, 1740, 1170, 2580), text="THEATERS.", font="didot", cap=127, track=0.14, bold=1),
    dict(box=(1975, 2112, 1000, 2730), text="Season 1891—92.", font="avcond", cap=114, track=0.17),
    dict(box=(2295, 2410, 1435, 2350), text="(SECOND YEAR)", font="avcond_med", cap=62, track=0.10),
    dict(box=(2815, 2900, 1375, 2385), text="By commission of the Directorate", font="typew", cap=46, track=0.0),
    dict(box=(2965, 3045, 1060, 2720), text="of the Imperial Theaters", font="typew", cap=44, track=0.14),
    dict(box=(3128, 3185, 1620, 2150), text="EDITED BY", font="times", cap=32, track=0.12),
    dict(box=(3250, 3337, 1350, 2420), text="A. E. Molchanov.", font="clar", cap=62, track=0.02),
    dict(box=(3742, 3827, 1535, 2262), text="PUBLISHED BY", font="copper", cap=54, track=0.22),
    dict(box=(3888, 3992, 950, 2840), text="Directorate of the Imperial Theaters.", font="copper", cap=57, track=0.0),
    dict(box=(4558, 4651, 1425, 2380), text="ST. PETERSBURG.", font="didot", cap=68, track=0.22, bold=1),
    dict(box=(4655, 4762, 630, 3170),
         text="Printing House of the Imperial St. Petersburg Theaters (Chief Admin. of Appanages), 40 Mokhovaya St.",
         font="times", cap=50, track=0.0, maxw=2950, bold=1),
]

# ---- ink mask + paper reconstruction ----
bg_gray = cv2.medianBlur(gray.astype(np.uint8), 101).astype(np.float32)
inkmask = (bg_gray - gray) > 30
erase = np.zeros((H, W), bool)
for L in LINES:
    y0, y1, x0, x1 = L["box"]
    erase[y0:y1, x0:x1] |= inkmask[y0:y1, x0:x1]
erase = cv2.dilate(erase.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0

# smooth paper tone with ink removed: inpaint on a downsampled copy
ds = 8
small = cv2.resize(img.astype(np.uint8), (W // ds, H // ds), interpolation=cv2.INTER_AREA)
small_mask = cv2.resize((inkmask | erase).astype(np.uint8) * 255, (W // ds, H // ds), interpolation=cv2.INTER_AREA)
small_mask = ((small_mask > 0) * 255).astype(np.uint8)
small_mask = cv2.dilate(small_mask, np.ones((3, 3), np.uint8))
small_bg = cv2.inpaint(small, small_mask, 6, cv2.INPAINT_TELEA)
smooth = cv2.GaussianBlur(cv2.resize(small_bg, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32), (0, 0), 6)

# real paper grain: residual from a blank band between the title and 'Season'
gy0, gy1, gx0, gx1 = 1760, 1960, 600, 3300
grain = img[gy0:gy1, gx0:gx1] - smooth[gy0:gy1, gx0:gx1]
grain = np.clip(grain, -18, 18)
gh, gw = grain.shape[:2]
reps = (H // gh + 1, W // gw + 1, 1)
grain_full = np.tile(grain, reps)[:H, :W]

paper = smooth + grain_full
out = img.copy()
# feather the erase edge so no hard seams
feather = cv2.GaussianBlur(erase.astype(np.float32), (0, 0), 2.5)[..., None]
out = out * (1 - feather) + paper * feather

# ink colour: median of solid ink in the big title
ys, xs = np.where(inkmask[702:883, 900:2850] & ((bg_gray - gray)[702:883, 900:2850] > 90))
INK = np.median(img[702:883, 900:2850][ys, xs], axis=0)
print("ink rgb", INK)


def font_for_cap(key, cap):
    path, idx = F[key]
    size = cap * 1.4
    for _ in range(6):
        f = ImageFont.truetype(path, int(round(size)), index=idx)
        bb = f.getbbox("H")
        size *= cap / (bb[3] - bb[1])
    return ImageFont.truetype(path, int(round(size)), index=idx)


def render(text, font, track_px):
    """Return float alpha array and the y-offset of the cap top within it."""
    asc, desc = font.getmetrics()
    # condensed faces have a stubby em dash; the original's is long, so draw a rule
    dash_w = font.getlength("0") * 1.5
    widths = [dash_w if c == "—" else font.getlength(c) for c in text]
    total = sum(widths) + track_px * (len(text) - 1)
    pad = 20
    canvas = Image.new("L", (int(total) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(canvas)
    x = pad
    for c, w in zip(text, widths):
        if c == "—":
            _, xt, _, base = font.getbbox("x")
            mid = (xt + base) / 2
            th = (base - font.getbbox("H")[1]) * 0.075
            d.rectangle((x, pad + mid - th / 2, x + w, pad + mid + th / 2), fill=255)
        else:
            d.text((x, pad), c, font=font, fill=255)
        x += w + track_px
    a = np.array(canvas).astype(np.float32) / 255
    captop = pad + font.getbbox("H")[1]
    return a, captop, total


report = []
for L in LINES:
    y0, y1, x0, x1 = L["box"]
    # where the original cap tops/baseline were: measured ink body in this box
    prof = inkmask[y0:y1, x0:x1].sum(1)
    body = np.where(prof > 0.12 * prof.max())[0]
    cap_top = y0 + body.min()
    cx = (x0 + x1) / 2
    cap = L["cap"]
    maxw = L.get("maxw", 3350)
    while True:
        font = font_for_cap(L["font"], cap)
        a, captop, total = render(L["text"], font, L["track"] * font.size)
        if total <= maxw:
            break
        cap *= 0.97
    if L.get("bold"):  # thicken hairlines to letterpress weight
        k = 2 * L["bold"] + 1
        a = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    # letterpress: slightly uneven ink and soft edges
    rng = np.random.default_rng(len(L["text"]))
    speck = cv2.GaussianBlur(rng.random(a.shape).astype(np.float32), (0, 0), 2.0)
    a = a * (0.86 + 0.14 * (speck - speck.min()) / (np.ptp(speck) + 1e-6))
    a = cv2.GaussianBlur(a, (0, 0), 1.3)
    ah, aw = a.shape
    ox = int(round(cx - aw / 2))
    oy = int(round(cap_top - captop))
    region = out[oy:oy + ah, ox:ox + aw]
    al = a[..., None] * 0.97
    out[oy:oy + ah, ox:ox + aw] = region * (1 - al) + INK * al
    report.append((L["text"][:40], x1 - x0, int(total), round(cap)))

for r in report:
    print(r)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT, dpi=(600, 600))
