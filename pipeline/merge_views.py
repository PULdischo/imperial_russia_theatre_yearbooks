"""Merge several parsed extraction runs of the same pages into one, via the selector.

Each run is a *view* of the page -- the whole page, or the page cut into
bands (`bands_n.py` / `run_reviews.py`). Views of the same page disagree in
different places, and `select_reading.select()` chooses among the readings
they produced. Measured on the 12 gold pages:

    single full-page pass                  56 words wrong   97.46%
    selector over 3 RESAMPLES of one view  49               97.78%
    selector over 3 DIFFERENT views        32               98.55%
    selector over 6 views                  24               98.91%   (3.4x cost, no linking gain)

Three views is the chosen production configuration (RG, 2026-09-28).

**The first `--parsed-dir` is the reference.** Its block order, block types
and whitespace are what survive; the other runs only ever supply alternative
READINGS for words. That is deliberate: the selector may choose a different
word, never a different structure, so the merged output stays comparable to
the reference run and the printed line breaks are preserved exactly.

Alignment is done ONCE PER PAGE, not per block, and that matters. A banded
view fragments the page differently — review_1902-03_SP_ballet_p009 is one
block whole and twenty-two blocks when quartered, because each band cuts a
paragraph and the model emits every piece separately. Matching blocks
one-to-one would throw twenty-one of those away. Instead each view's whole
page is projected onto the reference's word positions, and every reference
block takes its slice of that projection.

Where a view cannot be aligned at all (genuinely different reading order,
missing page) its candidate at each position comes back empty, the selector
drops it, and the reference word stands. Views degrade to silence rather
than to damage.

Usage:
    uv run python pipeline/merge_views.py \
        --parsed-dir outputs/reviews/pilot_parsed \
        --parsed-dir outputs/reviews/pilot2_parsed \
        --parsed-dir outputs/reviews/pilot3_parsed \
        --out-dir outputs/reviews/merged_parsed
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import re
import shutil
from pathlib import Path

from select_reading import select

csv.field_size_limit(10_000_000)

WORD = re.compile(r"\S+")
MATCH_FLOOR = 0.60          # below this, two blocks are not the same block
PLATE = {"figure"}


def field_of(block: dict) -> str:
    """Which column carries this block's text."""
    return "caption_text" if block["block_type"] in PLATE else "text"


def align_blocks(ref: list[dict], other: list[dict]) -> dict[int, dict]:
    """Greedy exclusive similarity match: ref index -> the other run's block.

    Exclusive because the same short block (a one-line caption, an
    enumerator) recurs on a page; without exclusivity every copy anchors to
    whichever one scores highest and the rest go unmatched.
    """
    pairs = []
    for i, rb in enumerate(ref):
        rt = (rb[field_of(rb)] or "").strip()
        if not rt:
            continue
        for j, ob in enumerate(other):
            ot = (ob[field_of(ob)] or "").strip()
            if not ot:
                continue
            r = difflib.SequenceMatcher(a=rt, b=ot, autojunk=False).quick_ratio()
            if r >= MATCH_FLOOR:
                pairs.append((r, i, j))
    pairs.sort(reverse=True)
    used_i, used_j, out = set(), set(), {}
    for r, i, j in pairs:
        if i in used_i or j in used_j:
            continue
        # quick_ratio is an upper bound; confirm before committing the pair
        rt = (ref[i][field_of(ref[i])] or "").strip()
        ot = (other[j][field_of(other[j])] or "").strip()
        if difflib.SequenceMatcher(a=rt, b=ot, autojunk=False).ratio() < MATCH_FLOOR:
            continue
        used_i.add(i); used_j.add(j); out[i] = other[j]
    return out


def project(ref_words: list[str], other_words: list[str]) -> list[str]:
    """What the other run reads at each of the reference's word positions."""
    out = [""] * len(ref_words)
    sm = difflib.SequenceMatcher(a=ref_words, b=other_words, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                out[k] = ref_words[k]
        elif tag == "replace":
            blob = " ".join(other_words[j1:j2])
            for k in range(i1, i2):
                out[k] = blob
        elif tag == "delete":
            for k in range(i1, i2):
                out[k] = ""
    return out


def merge_text(ref_text: str, projected: list[list[str]]) -> tuple[str, int]:
    """Selector over the views, splicing chosen words back into ref's whitespace.

    `projected` holds, per view, what that view reads at each of this block's
    word positions (already aligned page-wide by the caller).
    """
    spans = list(WORD.finditer(ref_text))
    if not spans or not projected:
        return ref_text, 0
    ref_words = [m.group() for m in spans]
    usable = [p for p in projected if len(p) == len(ref_words)]
    if not usable:
        return ref_text, 0

    pieces, last, changed = [], 0, 0
    for i, m in enumerate(spans):
        cands = [ref_words[i]] + [p[i] for p in usable]
        chosen, _ = select(cands, prefer=ref_words[i])
        pieces.append(ref_text[last:m.start()])
        pieces.append(chosen)
        if chosen != ref_words[i]:
            changed += 1
        last = m.end()
    pieces.append(ref_text[last:])
    return "".join(pieces), changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path, action="append",
                    dest="parsed_dirs",
                    help="repeat; the FIRST is the reference run")
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    if len(a.parsed_dirs) < 2:
        raise SystemExit("give at least two --parsed-dir values")

    runs = []
    for d in a.parsed_dirs:
        with open(d / "review_block.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        by_page = collections.defaultdict(list)
        for b in rows:
            by_page[b["page_id"]].append(b)
        for v in by_page.values():
            v.sort(key=lambda b: int(b["block_index"]))
        runs.append(by_page)
    ref_pages, others = runs[0], runs[1:]

    n_blocks = n_changed = n_words = 0
    pages_missing = collections.Counter()
    merged: list[dict] = []
    for page_id, ref_blocks in ref_pages.items():
        # one alignment per page per view; each block then takes its slice
        ref_words: list[str] = []
        bounds: list[tuple[int, int]] = []
        for rb in ref_blocks:
            w = WORD.findall(rb[field_of(rb)] or "")
            bounds.append((len(ref_words), len(ref_words) + len(w)))
            ref_words.extend(w)

        projections = []
        for other in others:
            ob = other.get(page_id)
            if not ob:
                pages_missing[page_id] += 1
                continue
            other_words: list[str] = []
            for b in ob:
                other_words.extend(WORD.findall(b[field_of(b)] or ""))
            if other_words and ref_words:
                projections.append(project(ref_words, other_words))

        for (start, end), rb in zip(bounds, ref_blocks):
            col = field_of(rb)
            ref_text = rb[col] or ""
            slices = [p[start:end] for p in projections]
            new_text, changed = merge_text(ref_text, slices)
            row = dict(rb)
            row[col] = new_text
            merged.append(row)
            n_blocks += 1
            n_changed += changed
            n_words += end - start

    a.out_dir.mkdir(parents=True, exist_ok=True)
    with open(a.parsed_dirs[0] / "review_block.csv", encoding="utf-8") as f:
        cols = csv.DictReader(f).fieldnames
    with open(a.out_dir / "review_block.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(merged)
    # structure comes from the reference run, so its page table carries over
    for side in ("review_page.csv", "review_span.csv", "repairs.csv"):
        src = a.parsed_dirs[0] / side
        if src.exists():
            shutil.copy(src, a.out_dir / side)

    print(f"{len(a.parsed_dirs)} runs | {len(ref_pages)} pages | {n_blocks} blocks")
    print(f"{n_changed:,} of {n_words:,} words changed "
          f"({100*n_changed/max(n_words,1):.2f}%) -> {a.out_dir}")
    if pages_missing:
        print(f"{len(pages_missing)} page(s) absent from a non-reference run "
              f"(kept from the reference)")


if __name__ == "__main__":
    main()
