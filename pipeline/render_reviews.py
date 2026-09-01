"""Stage 1 of the season-reviews pipeline (docs/season_reviews.md §1): render
every page of every PDF in pdf/Reviews_Season/ and write a manifest.

Parallel to render_pages.py, which serves the tabular pipeline. Kept separate
because the reviews are a different track with a different filename grammar,
a genre dimension the tabular manifest has no column for, and different
resolution needs (see below).

Idempotent -- re-running skips pages whose image already exists, so adding a
newly scanned volume costs only that volume (docs/season_reviews.md §13).

Two non-obvious choices:

* **JPEG, not PNG.** The tabular pipeline emits 300dpi PNGs; at 1,024 review
  pages that is ~3GB, on a machine that has repeatedly run short of disk, and
  it re-trips the DashScope 20MB payload limit that required emergency JPEG
  re-encoding twice (known_issues.md #19). Quality 95 is visually
  indistinguishable here -- the source scans are the limiting factor, not the
  re-encode.

* **300 dpi, but never upsampling.** 300dpi is the setting the tabular
  pipeline established empirically (render_pages.py: "150 -> 300 fixed the
  character-level OCR errors"). Source scans here are 200, 300 or 600 dpi
  natively -- 39 of 41 files are already at 300 or better. So each page
  renders at min(its native dpi, --target-dpi): the 600dpi scans come down to
  300, the 300dpi scans pass through untouched, and the two 200dpi files stay
  at 200 rather than having pixels invented for them.

Usage:
    python pipeline/render_reviews.py --out-dir outputs/reviews
    python pipeline/render_reviews.py --out-dir outputs/reviews --limit 2
    python pipeline/render_reviews.py --out-dir outputs/reviews --genre Ballet
"""
from __future__ import annotations

import argparse
import csv
import io
import re
from pathlib import Path

import pymupdf
from PIL import Image

# docs/season_reviews.md §13: this vocabulary is closed on purpose. An
# unrecognised token is an error, not a new category -- otherwise a typo
# silently becomes a genre and surfaces later as a review nothing can find.
GENRES = {"Ballet", "Opera", "All", "RussianDrama", "FrenchDrama"}
CITIES = {"SP": "SP", "Moscow": "Moscow"}
CITY_TOKEN = {"SP": "SP", "Moscow": "MSK"}

FILENAME_RE = re.compile(
    r"^(?P<season>\d{4}-\d{2})_SeasonReview_(?P<genre>[A-Za-z]+?)(?P<city>SP|Moscow)\.pdf$"
)


class BadFilename(Exception):
    pass


def validate_season(season: str) -> None:
    """Second half must be the first half plus one, century rollover allowed.

    This is the check that would have caught 1899-90 and 1905-07 before they
    reached the tabular manifest (docs/season_reviews.md §13)."""
    first, second = season.split("-")
    if (int(first) + 1) % 100 != int(second):
        raise BadFilename(f"malformed season {season!r}: {second} is not {first}+1")


def parse_filename(name: str) -> dict:
    m = FILENAME_RE.match(name)
    if not m:
        raise BadFilename(f"does not match <season>_SeasonReview_<Genre><City>.pdf")
    season, genre, city = m.group("season"), m.group("genre"), m.group("city")
    validate_season(season)
    if genre not in GENRES:
        raise BadFilename(
            f"unknown genre {genre!r}; expected one of {sorted(GENRES)}"
        )
    # docs/season_reviews.md §1: the French troupe played the Mikhailovsky and
    # had no Moscow counterpart, so this combination cannot exist.
    if genre == "FrenchDrama" and city == "Moscow":
        raise BadFilename("FrenchDrama pairs only with SP -- there was no Moscow French troupe")
    return {"season": season, "genre": genre, "city": CITIES[city],
            "city_token": CITY_TOKEN[city]}


def make_page_id(meta: dict, page_index: int) -> str:
    return (f"review_{meta['season']}_{meta['city_token']}"
            f"_{meta['genre'].lower()}_p{page_index:03d}")


def native_long_edge(doc: pymupdf.Document, page: pymupdf.Page) -> int | None:
    """Longest pixel dimension of the largest image embedded in the page, or
    None if the page has no raster image (unlikely here -- these are scans)."""
    best = None
    for info in page.get_images(full=True):
        try:
            img = doc.extract_image(info[0])
        except Exception:
            continue
        edge = max(img["width"], img["height"])
        if best is None or edge > best:
            best = edge
    return best


def render_dpi(doc: pymupdf.Document, page: pymupdf.Page, target_dpi: int) -> int:
    """min(native dpi, target_dpi) -- downsample the 600dpi scans, pass the
    300dpi ones through, and never invent pixels for the 200dpi ones."""
    rect = page.rect
    page_long_pt = max(rect.width, rect.height)
    if page_long_pt <= 0:
        return target_dpi
    native = native_long_edge(doc, page)
    if not native:
        return target_dpi
    native_dpi = 72.0 * native / page_long_pt
    return max(1, int(round(min(float(target_dpi), native_dpi))))


def discover(pdf_dir: Path):
    bad = []
    found = []
    for path in sorted(pdf_dir.glob("*.pdf")):
        try:
            found.append((path, parse_filename(path.name)))
        except BadFilename as e:
            bad.append((path.name, str(e)))
    return found, bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", type=Path, default=Path("pdf/Reviews_Season"))
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--target-dpi", type=int, default=300,
                    help="render dpi ceiling; pages at lower native resolution "
                         "stay at native rather than being upsampled")
    ap.add_argument("--quality", type=int, default=95, help="JPEG quality")
    ap.add_argument("--format", choices=["jpg", "png"], default="jpg")
    ap.add_argument("--genre", default=None, help="restrict to one genre (staging)")
    ap.add_argument("--limit", type=int, default=None, help="stop after N PDFs")
    args = ap.parse_args()

    images_dir = args.out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    found, bad = discover(args.pdf_dir)
    if bad:
        print("REJECTED FILENAMES (fix these before proceeding):")
        for name, why in bad:
            print(f"  {name}\n      {why}")
        raise SystemExit(1)

    rows = []
    n_pdfs = n_new = n_skipped = 0
    for path, meta in found:
        if args.genre and meta["genre"] != args.genre:
            continue
        if args.limit is not None and n_pdfs >= args.limit:
            break
        n_pdfs += 1
        doc = pymupdf.open(path)
        for i, page in enumerate(doc):
            page_id = make_page_id(meta, i)
            image_path = images_dir / f"{page_id}.{args.format}"
            if image_path.exists():
                n_skipped += 1
            else:
                dpi = render_dpi(doc, page, args.target_dpi)
                px = page.get_pixmap(dpi=dpi)
                im = Image.frombytes("RGB", (px.width, px.height), px.samples)
                if args.format == "jpg":
                    im.save(image_path, "JPEG", quality=args.quality, optimize=True)
                else:
                    im.save(image_path)
                n_new += 1
            rows.append({
                "page_id": page_id,
                "entity_type": "SeasonReview",
                "season": meta["season"],
                "city": meta["city"],
                "genre": meta["genre"],
                "source_file": path.name,
                "source_page_index": i,
                "printed_page_number": "",  # filled by extraction, not derivable here
                "image_file": f"images/{page_id}.{args.format}",
            })
        print(f"{path.name}: {len(doc)} pages")
        doc.close()

    manifest = args.out_dir / "manifest.csv"
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n{n_pdfs} PDFs, {len(rows)} pages "
          f"({n_new} rendered, {n_skipped} already present) -> {manifest}")


if __name__ == "__main__":
    main()
