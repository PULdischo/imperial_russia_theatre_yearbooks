"""Stage 1 of the pipeline (docs/pipeline.md): render every page of every
PDF in pdfs/ to a PNG, and write a corpus-wide manifest matching the columns
of docs/eval/gold/source_pages.csv.

Idempotent -- re-running skips pages whose image already exists, so it's
safe to re-run after adding new PDFs (e.g. once Graduates/ProductionStats
are sourced) without re-rendering everything.

Usage:
    python pipeline/render_pages.py --pdf-dir pdfs --out-dir outputs --dpi 300
    python pipeline/render_pages.py --limit 5   # smoke-test a handful of pages
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pymupdf

# folder name -> (entity_type as used in docs/schema.md, page_id slug)
FOLDER_MAP = {
    "RepertoireTables": ("Repertoire", "repertoire"),
    "Spiski_Administration": ("Administrators", "administration"),
    "Spiski_BalletArtists": ("BalletArtists", "balletartists"),
    "Spiski_Musicians": ("Musicians", "musicians"),
    "Spiski_ProductionTeam": ("ProductionTeam", "productionteam"),
    "Spiski_TheaterSchoolStaff": ("TheaterSchoolStaff", "theaterschoolstaff"),
    "Spiski_Graduates": ("Graduates", "graduates"),
    "Spiski_ProductionStats": ("ProductionStats", "productionstats"),
}

SEASON_RE = re.compile(r"ForUpload_(\d{4}-\d{2})_")


def city_from_filename(name: str) -> tuple[str, str]:
    """SP/Moscow is only recoverable from the filename for BalletArtists and
    Musicians, which are split into separate files per city. RepertoireTables
    interleaves both cities within one file/page in ways that can't be
    determined without reading the page (see docs/schema.md) -- leave blank
    here; it gets filled in during extraction/parsing instead.

    Returns (city_token, city_value): city_token is the short form used in
    page_id ("SP"/"MSK", for readable filenames); city_value is the full
    value docs/schema.md specifies for the `city` column ("SP"/"Moscow")."""
    if name.endswith("SP.pdf"):
        return "SP", "SP"
    if name.endswith("Moscow.pdf"):
        return "MSK", "Moscow"
    return "", ""


def discover_pdfs(pdf_dir: Path):
    for folder in sorted(pdf_dir.iterdir()):
        if not folder.is_dir() or folder.name not in FOLDER_MAP:
            continue
        entity_type, slug = FOLDER_MAP[folder.name]
        for pdf_path in sorted(folder.glob("*.pdf")):
            m = SEASON_RE.match(pdf_path.name)
            season = m.group(1) if m else "unknown"
            city_token, city_value = city_from_filename(pdf_path.name)
            yield pdf_path, entity_type, slug, season, city_token, city_value


def make_page_id(slug: str, season: str, city_token: str, page_index: int) -> str:
    city_part = f"_{city_token}" if city_token else ""
    return f"{slug}_{season}{city_part}_p{page_index:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", type=Path, default=Path("pdfs"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs"))
    ap.add_argument("--dpi", type=int, default=300)  # 150 -> 300 fixed the
    # character-level OCR errors seen in the first extraction smoke test
    ap.add_argument("--limit", type=int, default=None,
                     help="stop after this many PDFs (for a quick dry run)")
    ap.add_argument("--entity-type", default=None,
                     help="restrict to one entity_type (e.g. Administration) for a staged batch")
    args = ap.parse_args()

    images_dir = args.out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "manifest.csv"

    manifest_rows = []
    n_pdfs = 0
    for pdf_path, entity_type, slug, season, city_token, city_value in discover_pdfs(args.pdf_dir):
        if args.entity_type and entity_type != args.entity_type:
            continue
        if args.limit is not None and n_pdfs >= args.limit:
            break
        n_pdfs += 1
        doc = pymupdf.open(pdf_path)
        n_pages = len(doc)
        for i, page in enumerate(doc):
            page_id = make_page_id(slug, season, city_token, i)
            image_path = images_dir / f"{page_id}.png"
            if not image_path.exists():
                page.get_pixmap(dpi=args.dpi).save(image_path)
            manifest_rows.append({
                "page_id": page_id, "entity_type": entity_type, "season": season,
                "city": city_value, "source_file": pdf_path.name, "source_page_index": i,
                "printed_page_number": "",  # not derivable without reading the page
                "image_file": f"images/{page_id}.png",
            })
        doc.close()
        print(f"{pdf_path.relative_to(args.pdf_dir)}: {n_pages} pages")

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["page_id", "entity_type", "season", "city", "source_file",
                      "source_page_index", "printed_page_number", "image_file"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(manifest_rows)

    print(f"\n{n_pdfs} PDFs, {len(manifest_rows)} pages -> {manifest_path}")


if __name__ == "__main__":
    main()
