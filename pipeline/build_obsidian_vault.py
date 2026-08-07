"""Stage 5c: package the verbatim/raw layer as an Obsidian vault -- one note
per source page (docs/verbatim_deliverables.md's recommended granularity:
one printed page = one note, mirroring how the source is actually read,
rather than one note per transcribed row which would turn the vault into a
flat data dump). Each note gets YAML frontmatter (the source_pages columns),
an embedded downscaled page image, a verbatim table of that page's rows,
and prev/next links within its source PDF. A small set of index notes
(one per entity_type, grouped by season) and a Home note tie it together.

Images are re-encoded to a much smaller "viewing copy" (long-edge capped,
JPEG) for the vault -- the archival 300dpi PNGs average ~9.9MB each
(12.8GB across the corpus), which would make the vault impractical to sync
via Obsidian Sync or a cloud-synced folder. The archival images are not
touched; the vault's copies are separate, disposable files.

Usage:
    python pipeline/build_obsidian_vault.py --parsed-dir outputs/full_run/parsed \
        --manifest outputs/full_run/manifest.csv --images-dir outputs/full_run/images \
        --out-dir outputs/full_run/obsidian_vault
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROSTER_KINDS = {"Administrators", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}

VIEW_MAX_EDGE = 1600
VIEW_JPEG_QUALITY = 82

ROSTER_COLUMNS = [
    ("list_number", "#"), ("family_name", "Family name"), ("first_name", "First name"),
    ("patronymic", "Patronymic"), ("heading_path", "Heading"),
    ("rank_or_title", "Rank/title"), ("service_class", "Class"),
    ("instrument", "Instrument"), ("subject_taught", "Subject"),
    ("tenure_note_text", "Tenure"), ("credit_summary_text", "Credits"),
]
EVENT_COLUMNS = [
    ("date_text", "Date"), ("theater", "Theater"), ("time_of_day", "Time of day"),
    ("event_status", "Status"), ("_works", "Works"),
    ("receipts_text", "Receipts"), ("annotation", "Annotation"),
]


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def by_key(rows: list[dict], key: str) -> dict[str, list[dict]]:
    d = defaultdict(list)
    for r in rows:
        d[r[key]].append(r)
    return d


def md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def md_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "*(no rows extracted for this page)*\n"
    header = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for r in rows:
        cells = [md_escape(str(r.get(key, ""))) for key, _ in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def make_viewing_image(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = VIEW_MAX_EDGE / max(w, h)
        if scale < 1:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=VIEW_JPEG_QUALITY)


def page_note(row: dict, roster_rows: list[dict], event_rows: list[dict],
              performances_by_event: dict[str, list[dict]], prev_id: str | None,
              next_id: str | None) -> str:
    page_id = row["page_id"]
    fm = [
        "---",
        f"page_id: {page_id}",
        f"entity_type: {row['entity_type']}",
        f"season: {row['season']}",
        f"city: {row.get('city', '') or ''}",
        f"source_file: {row['source_file']}",
        f"source_page_index: {row['source_page_index']}",
        f"printed_page_number: {row.get('printed_page_number', '') or ''}",
        "---", "",
    ]
    body = [f"![[{page_id}.jpg]]", ""]

    if row["entity_type"] in ROSTER_KINDS:
        body.append(md_table(roster_rows, ROSTER_COLUMNS))
    else:
        expanded = []
        for s in event_rows:
            performances = performances_by_event.get(s["event_id"], [])
            work_text = "; ".join(
                f"{w['performance_title']} ({w['genre']})" if w.get("genre") else w["performance_title"]
                for w in performances
            )
            expanded.append({**s, "_works": work_text})
        body.append(md_table(expanded, EVENT_COLUMNS))

    nav = []
    if prev_id:
        nav.append(f"[[{prev_id}|<- Previous page]]")
    if next_id:
        nav.append(f"[[{next_id}|Next page ->]]")
    if nav:
        body.append("")
        body.append(" | ".join(nav))

    return "\n".join(fm) + "\n".join(body) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    pages_dir = args.out_dir / "pages"
    images_dir = args.out_dir / "images"
    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_csv(args.manifest)
    roster_by_page = by_key(load_csv(args.parsed_dir / "person_entry.csv"), "page_id")
    events_by_page = by_key(load_csv(args.parsed_dir / "event_entry.csv"), "page_id")
    performances_by_event = by_key(load_csv(args.parsed_dir / "event_entry_performance.csv"), "event_id")

    # prev/next within each source PDF, in page order
    by_file = defaultdict(list)
    for row in manifest:
        by_file[row["source_file"]].append(row)
    for rows in by_file.values():
        rows.sort(key=lambda r: int(r["source_page_index"]))

    n_images = 0
    for row in manifest:
        page_id = row["page_id"]
        src_png = args.images_dir / f"{page_id}.png"
        src_jpg = args.images_dir / f"{page_id}.jpg"
        src = src_png if src_png.exists() else src_jpg
        if src.exists():
            make_viewing_image(src, images_dir / f"{page_id}.jpg")
            n_images += 1

    n_notes = 0
    for rows in by_file.values():
        for i, row in enumerate(rows):
            page_id = row["page_id"]
            prev_id = rows[i - 1]["page_id"] if i > 0 else None
            next_id = rows[i + 1]["page_id"] if i < len(rows) - 1 else None
            note = page_note(row, roster_by_page.get(page_id, []),
                              events_by_page.get(page_id, []), performances_by_event,
                              prev_id, next_id)
            (pages_dir / f"{page_id}.md").write_text(note, encoding="utf-8")
            n_notes += 1

    # Index notes: one per entity_type, pages grouped by season in order
    by_entity_season = defaultdict(lambda: defaultdict(list))
    for row in manifest:
        by_entity_season[row["entity_type"]][row["season"]].append(row)

    for entity_type, seasons in by_entity_season.items():
        lines = [f"# {entity_type}", ""]
        for season in sorted(seasons):
            lines.append(f"## {season}")
            rows = sorted(seasons[season], key=lambda r: (r["source_file"], int(r["source_page_index"])))
            for row in rows:
                lines.append(f"- [[{row['page_id']}]]")
            lines.append("")
        (args.out_dir / f"{entity_type}.md").write_text("\n".join(lines), encoding="utf-8")

    home = ["# Imperial Theater Yearbooks -- Verbatim Vault", "",
            "Ежегодникъ Императорскихъ театровъ, 1890/91-1907/08, one note per "
            "digitized page. See docs/schema.md and docs/verbatim_deliverables.md "
            "in the project repo for full context.", "", "## Browse by type", ""]
    for entity_type in sorted(by_entity_season):
        home.append(f"- [[{entity_type}]]")
    (args.out_dir / "Home.md").write_text("\n".join(home) + "\n", encoding="utf-8")

    print(f"{n_notes} page notes -> {pages_dir}")
    print(f"{n_images} viewing-copy images -> {images_dir}")
    print(f"{len(by_entity_season)} entity-type index notes + Home.md -> {args.out_dir}")


if __name__ == "__main__":
    main()
