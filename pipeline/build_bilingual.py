"""Build the side-by-side Russian/English reading files, one per review.

RG's two uses for the season-review text (2026-09-26): run it through a
translator and skim it in English, and link mentions to database entities.
She will **quote from the scan, never from this file** -- so these are
reading copies, not an edition. That is why the Russian is reflowed here
(printed line breaks and end-of-line hyphens joined) and why prose is
allowed to run across the photographs that interrupt it on the page.

**These files are DERIVED. Never hand-edit one.** Every file carries a
`source-hash` in its header; when the source text changes the hash stops
matching and the file is stale. Re-run this script, don't patch the output.
See docs/season_reviews.md §12.12.

Translation is deliberately NOT done here. This script joins Russian text to
whatever English already exists in a translation sidecar, keyed by block_id,
and leaves the English cell empty when there is none. That keeps three things
independent: extraction, translation, and layout. Re-translating, or
switching `--source-layer` to a corrected layer later, touches only one of
them.

Usage:
    uv run python pipeline/build_bilingual.py \
        --parsed-dir outputs/reviews/pilot_parsed \
        --out-dir outputs/reviews/bilingual \
        [--translations outputs/reviews/translations.csv] \
        [--source-layer parsed]
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

csv.field_size_limit(10_000_000)

CITY = {"SP": "St Petersburg", "MSK": "Moscow"}
GENRE = {"Ballet": "Ballet", "Opera": "Opera", "All": "Ballet and Opera"}
# blocks that belong to a photographic plate rather than the running review
PLATE = {"figure"}
# A review's own section heading. An issue often packs two reviews onto one
# printed page, so a review's FIRST page can open with the tail of the
# previous one -- 17 of 46 reviews do (opera roster changes before a ballet
# review, drama criticism before another). Those paragraphs are dropped.
# Only PARAGRAPHS: a plate caption before the heading usually belongs to the
# review it introduces (1902-03 SP Opera opens with a Servilia plate), and a
# heading before it is the parent title (1910-11 Moscow's
# "ОБЗОРЪ СЕЗОНА 1910-1911 г.-МОСКВА"). Dropping those would lose real content.
SECTION_HEADING = {"балетъ", "опера", "драма"}
# The mirror case: a review's LAST page can run on into the NEXT section,
# because the same printed page was scanned into both PDFs. 1894-95 Moscow
# Opera ends with 8 ballet blocks. Drop from the foreign section heading on.
# Not applied to the combined "All" volumes, which legitimately hold both.
OWN_HEADING = {"Ballet": "балетъ", "Opera": "опера"}
# blocks with no reading value in a translation file
SKIP = {"byline"}


def reflow(text: str) -> str:
    """Join the printed line breaks; drop an end-of-line hyphen from a split word.

    A hyphen after a digit or a Roman numeral is kept: it is a COMPOUND hyphen,
    not a soft one. The print reads `за XLV-` / `лѣтнюю службу`, and joining
    that gives `XLVлѣтнюю`, which is not a word. Latin I V X L C D M never end
    a Russian word, so the lookbehind is safe.
    """
    text = re.sub(r"(?<![\dIVXLCDM])([^\s-])-\n\s*", r"\1", text)
    return re.sub(r"\s*\n\s*", " ", text).strip()


def cell(text: str) -> str:
    """Make a string safe inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def section_heading_index(blocks: list[dict]) -> int | None:
    """Index of the review's own section heading, if present."""
    for i, b in enumerate(blocks):
        if b["block_type"] != "heading":
            continue
        if (b["text"] or "").strip().strip(".").strip().lower() in SECTION_HEADING:
            return i
    return None


def foreign_heading_index(blocks: list[dict], own: str | None) -> int | None:
    """Index where a DIFFERENT section begins on this review's last page."""
    if not own:
        return None
    for i, b in enumerate(blocks):
        if b["block_type"] != "heading":
            continue
        t = (b["text"] or "").strip().strip(".").strip().lower()
        if t in SECTION_HEADING and t != own:
            return i
    return None


def page_no(page_id: str) -> int:
    m = re.search(r"_p(\d+)$", page_id)
    return int(m.group(1)) if m else 0


def load_translations(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return {r["block_id"]: r["english"] for r in csv.DictReader(f)
                if r.get("english", "").strip()}


def build(parsed_dir: Path, out_dir: Path, translations: dict[str, str],
          source_layer: str) -> list[tuple[str, int, int]]:
    with open(parsed_dir / "review_page.csv", encoding="utf-8") as f:
        pages = {r["page_id"]: r for r in csv.DictReader(f)}
    with open(parsed_dir / "review_block.csv", encoding="utf-8") as f:
        blocks = list(csv.DictReader(f))

    # group pages into reviews: one per (season, city, genre) = one source PDF
    reviews: dict[tuple, list[str]] = collections.defaultdict(list)
    for pid, p in pages.items():
        reviews[(p["season"], p["city"], p["genre"])].append(pid)

    by_page: dict[str, list[dict]] = collections.defaultdict(list)
    for b in blocks:
        by_page[b["page_id"]].append(b)
    for v in by_page.values():
        v.sort(key=lambda b: int(b["block_index"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for (season, city, genre), page_ids in sorted(reviews.items()):
        page_ids.sort(key=page_no)
        # hash the source text so staleness is detectable without re-reading it
        digest = hashlib.sha256()
        for pid in page_ids:
            for b in by_page[pid]:
                digest.update((b["text"] or "").encode("utf-8"))
                digest.update((b["caption_text"] or "").encode("utf-8"))
        src_hash = digest.hexdigest()[:12]

        lines = [f"# {season} — {CITY.get(city, city)} — {GENRE.get(genre, genre)}", ""]
        lines.append("<!-- generated, do not hand-edit · build: pipeline/build_bilingual.py")
        lines.append(f"     source-layer: {source_layer} · source-hash: {src_hash} · "
                     f"built: {date.today().isoformat()} -->")
        lines.append("")

        plates: list[tuple[str, str, str]] = []
        n_blocks = 0
        dropped_foreign = 0
        for idx_page, pid in enumerate(page_ids):
            folio = (pages[pid].get("printed_folio") or "").strip()
            body, page_plates = [], []
            page_blocks = by_page[pid]
            skip_before = 0
            if idx_page == 0:
                h = section_heading_index(page_blocks)
                if h:
                    skip_before = h
            stop_at = len(page_blocks)
            if idx_page == len(page_ids) - 1:
                f = foreign_heading_index(page_blocks, OWN_HEADING.get(genre))
                if f is not None:
                    stop_at = f
            for bi, b in enumerate(page_blocks):
                if bi >= stop_at:
                    dropped_foreign += 1
                    continue
                if bi < skip_before and b["block_type"] not in PLATE \
                        and b["block_type"] != "heading":
                    dropped_foreign += 1
                    continue
                kind = b["block_type"]
                if kind in SKIP:
                    continue
                raw = (b["caption_text"] if kind in PLATE else b["text"]) or ""
                ru = reflow(raw)
                if not ru:
                    continue
                en = translations.get(b["block_id"], "")
                if kind in PLATE:
                    page_plates.append((f"p{page_no(pid)} · {folio or '—'}", ru, en))
                else:
                    body.append((ru, en))
                n_blocks += 1
            if not body and not page_plates:
                continue
            head = f"## Page {page_no(pid)}"
            if folio:
                head += f" · folio {folio}"
            lines += [head, ""]
            if body:
                lines += ["| Русскій | English |", "| --- | --- |"]
                lines += [f"| {cell(ru)} | {cell(en)} |" for ru, en in body]
                lines.append("")
            plates.extend(page_plates)

        if plates:
            lines += ["##### Plate captions", "",
                      "| Page · folio | Русскій | English |", "| --- | --- | --- |"]
            lines += [f"| {ref} | {cell(ru)} | {cell(en)} |" for ref, ru, en in plates]
            lines.append("")

        name = f"{season}_{city}_{genre}.md"
        (out_dir / name).write_text("\n".join(lines), encoding="utf-8")
        written.append((name, len(page_ids), n_blocks, dropped_foreign))
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--translations", type=Path, default=None,
                    help="CSV with block_id,english. Missing English is left blank.")
    ap.add_argument("--source-layer", default="parsed",
                    help="recorded in each file's header; change when the text "
                         "comes from a corrected or search layer instead")
    a = ap.parse_args()

    tr = load_translations(a.translations)
    written = build(a.parsed_dir, a.out_dir, tr, a.source_layer)
    total_pages = sum(w[1] for w in written)
    total_blocks = sum(w[2] for w in written)
    print(f"{len(written)} review files, {total_pages} pages, {total_blocks} blocks "
          f"-> {a.out_dir}")
    print(f"translations supplied for {len(tr)} blocks"
          + ("" if tr else "  (English columns will be empty)"))
    total_dropped = sum(w[3] for w in written)
    if total_dropped:
        print(f"{total_dropped} paragraph(s) belonging to the PREVIOUS review "
              f"dropped from first pages")
    for name, npages, nblocks, dropped in written:
        tail = f"  (-{dropped} foreign)" if dropped else ""
        print(f"  {name:34s} {npages:3d} pages  {nblocks:4d} blocks{tail}")


if __name__ == "__main__":
    main()
