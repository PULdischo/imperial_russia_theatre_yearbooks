"""Recombine per-band extraction output into one page-shaped raw JSON per page.

`make_bands.py` cuts a page into N overlapping bands and `run_reviews.py`
extracts each separately, so a banded view arrives as `<page_id>__band0`,
`__band1`, ... Everything downstream (`parse_reviews.py`, then
`merge_views.py`) works per PAGE, so the bands have to be sewn back together
first. This is that step.

Two things make it more than a concatenation:

**The bands deliberately overlap.** Each is padded inward by a quarter of a
band height so that text sitting on a cut appears whole in at least one band
— which means the seam region is extracted twice. A block repeated across
the seam is dropped; a block SPLIT across it (the model saw half in each
band) is merged on the shared words.

**Page-level fields from a band are not trustworthy.** A band that cannot see
the folio invents one: on review_1896-97_SP_ballet_p017 band0 reported folio
194 and band1 reported the true 247. So `printed_folio` is deliberately left
null here, and `tailpiece_present` / `reading_order_uncertain` are OR-ed
rather than taken from any single band. The full-page view is the reference
in `merge_views.py` and supplies the real page-level values; a banded view
contributes block TEXT only.

Usage:
    uv run python pipeline/stitch_bands.py \
        --raw-dir outputs/reviews/bands4/raw \
        --out-dir outputs/reviews/bands4/stitched
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
from pathlib import Path

WORD = re.compile(r"\S+")
DUPLICATE = 0.85        # two blocks this similar across a seam are the same block
MIN_OVERLAP = 5         # shared words needed to treat a split block as one
SEAM_WINDOW = 3         # blocks either side of a seam worth comparing


def block_text(b: dict) -> str:
    if b.get("block_type") == "figure":
        return " ".join(s.get("text", "") for s in b.get("caption", []) or [])
    return " ".join(s.get("text", "") for s in b.get("spans", []) or [])


def append_text(b: dict, extra: str) -> None:
    key = "caption" if b.get("block_type") == "figure" else "spans"
    spans = b.get(key) or []
    if spans:
        spans[-1]["text"] = (spans[-1].get("text", "") + " " + extra).strip()
    else:
        b[key] = [{"text": extra}]


def suffix_prefix_overlap(a_words: list[str], b_words: list[str]) -> int:
    """Longest k where a's last k words equal b's first k words."""
    limit = min(len(a_words), len(b_words), 60)
    for k in range(limit, MIN_OVERLAP - 1, -1):
        if a_words[-k:] == b_words[:k]:
            return k
    return 0


def stitch(bands: list[dict]) -> dict:
    out_blocks: list[dict] = []
    for band in bands:
        incoming = list(band.get("blocks") or [])
        if not out_blocks:
            out_blocks.extend(incoming)
            continue
        tail = out_blocks[-SEAM_WINDOW:]
        consumed = 0
        for b in incoming[:SEAM_WINDOW]:
            bt = block_text(b).strip()
            if not bt:
                consumed += 1
                continue
            bw = WORD.findall(bt)
            merged = False
            for a in reversed(tail):
                at = block_text(a).strip()
                if not at:
                    continue
                if difflib.SequenceMatcher(a=at, b=bt, autojunk=False).ratio() >= DUPLICATE:
                    consumed += 1          # the seam showed us this block twice
                    merged = True
                    break
                k = suffix_prefix_overlap(WORD.findall(at), bw)
                if k:
                    rest = " ".join(bw[k:])
                    if rest:
                        append_text(a, rest)   # one block the cut split in two
                    consumed += 1
                    merged = True
                    break
            if not merged:
                break                      # past the seam; keep the rest as-is
        out_blocks.extend(incoming[consumed:])

    return {
        # a band cannot see the whole page, so it cannot be trusted for these
        "printed_folio": None,
        "tailpiece_present": any(b.get("tailpiece_present") for b in bands),
        "no_text": all(b.get("no_text") for b in bands) if bands else True,
        "copy_artifacts": sorted({a for b in bands
                                  for a in (b.get("copy_artifacts") or [])}),
        "reading_order_uncertain": any(b.get("reading_order_uncertain")
                                       for b in bands),
        "blocks": out_blocks,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()

    by_page: dict[str, list[tuple[int, Path]]] = collections.defaultdict(list)
    unparsed = 0
    for f in sorted(a.raw_dir.glob("*.raw.json")):
        m = re.match(r"^(.*)__band(\d+)\.raw\.json$", f.name)
        if not m:
            unparsed += 1
            continue
        by_page[m.group(1)].append((int(m.group(2)), f))

    a.out_dir.mkdir(parents=True, exist_ok=True)
    written = bad = 0
    dropped = 0
    for page_id, items in sorted(by_page.items()):
        items.sort()
        bands = []
        for _, f in items:
            try:
                bands.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                bad += 1
        if not bands:
            continue
        before = sum(len(b.get("blocks") or []) for b in bands)
        page = stitch(bands)
        dropped += before - len(page["blocks"])
        (a.out_dir / f"{page_id}.raw.json").write_text(
            json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
        written += 1

    print(f"{written} pages stitched -> {a.out_dir}")
    print(f"{dropped} duplicate/split blocks resolved at the seams")
    if bad:
        print(f"{bad} band file(s) were not valid JSON and were skipped")
    if unparsed:
        print(f"{unparsed} file(s) did not look like <page>__bandN.raw.json")


if __name__ == "__main__":
    main()
