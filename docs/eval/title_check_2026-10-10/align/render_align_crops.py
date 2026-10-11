"""Render lean reader crops for the column-structure read (issue #151 follow-up 15).

    uv run python docs/eval/title_check_2026-10-10/align/render_align_crops.py OUT_DIR page_id [page_id ...]

Single page: whole page at 1700 px wide, cut into a top and a bottom band (10% overlap).  Spread (pairNNN): the PDF page is a
landscape spread with the table text rotated 90 degrees; it is rotated clockwise (text upright, date rows down the page) and
cut into four bands (2 per printed page).  Files: OUT_DIR/<page_id>__1.jpg, __2.jpg ...  Embedded full-res scan images are read
with pymupdf from pdf/RepertoireTables/ForUpload_<season>_Repertoire.pdf (single: manifest source_page_index; spread: NNN/2-1).
"""
import csv, io, re, sys
from pathlib import Path
import fitz
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[4]
PDF = ROOT / "pdf" / "RepertoireTables"
W = 1700


def manifest():
    return {r["page_id"]: r for r in csv.DictReader(open(ROOT / "outputs/full_run/manifest.csv", encoding="utf-8"))}


def page_image(pid, man):
    m = re.match(r"repertoire_(\d{4}-\d{2})_(p|pair)(\d+)$", pid)
    season, kind, n = m.group(1), m.group(2), int(m.group(3))
    src = PDF / f"ForUpload_{season}_Repertoire.pdf"
    if kind == "pair":
        idx = n // 2 - 1
    else:
        r = man.get(pid, {})
        if not r.get("source_page_index"):
            return None, kind
        idx = int(r["source_page_index"])
    doc = fitz.open(src)
    imgs = doc[idx].get_images(full=True)
    if not imgs:
        return None, kind
    # the largest embedded image on the page
    best = max(imgs, key=lambda t: t[2] * t[3])
    im = Image.open(io.BytesIO(doc.extract_image(best[0])["image"])).convert("L")
    return im, kind


def bands(im, k, overlap=0.10):
    h = im.height
    step = h / k
    out = []
    for i in range(k):
        a = max(0, int(i * step - overlap * step)); b = min(h, int((i + 1) * step + overlap * step))
        out.append(im.crop((0, a, im.width, b)))
    return out


def main(out_dir, pids):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    man = manifest()
    for pid in pids:
        im, kind = page_image(pid, man)
        if im is None:
            print("NO IMAGE", pid); continue
        if kind == "pair":
            im = im.rotate(-90, expand=True)           # clockwise
            k = 4
        else:
            k = 2
        im = im.resize((W, int(im.height * W / im.width)))
        for i, b in enumerate(bands(im, k), 1):
            b.save(out / f"{pid}__{i}.jpg", quality=80)
        print("ok", pid, kind, im.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
