"""Stage 4b of the season-reviews pipeline: recover ENUMERATED ITEM
boundaries from already-extracted text, with no vision call.

WHY THIS IS NOT DONE IN THE EXTRACTION PROMPT
---------------------------------------------
Measured 2026-09-24/25. Asking the model to split numbered lists works on
the twelve gold pages and does not survive unseen ones: over 60 non-gold
pages the model marked 29 enumerated items while its own transcribed text
contained 90. It reads the labels correctly and files two thirds of the
items as ordinary prose.

A regex over that same text recovers all of them -- 47/47 on every gold run
and 90/90 out of sample, verified against the scans. It is deterministic,
free, re-runnable, and carries none of the run-to-run wobble the vision
pass has. Pressing the prompt harder instead cost 0.8pt of character
accuracy and destabilised page 02 (22 blocks one run, 1 the next).

This is the flatten-boundary discipline CLAUDE.md already mandates: keep
the paid, non-deterministic vision output stable and derive what can be
derived downstream, where it is free to iterate.

WHAT IT DOES NOT DO, AND WHY IT SHOULD NOT
------------------------------------------
Bare-labelled items -- a dance title followed by its performers, with no
printed "1)" in front of it. Eight of them in the gold, e.g.
"Solo des Etoiles doubles—г-жи Мендесъ 1-я и Мендесъ 2-я."

A pattern rule for these was tested and DELIBERATELY NOT ADOPTED. Matching
"Latin-script title + em dash" found 7 of the 8 with zero false positives
across the twelve gold pages -- tempting, and wrong.

RG, 2026-09-25: "I don't think we can assume that bare-labelled always
starts with Latin. We can later identify these lists from the meaning of
their content."

The distinction this script rests on:

  * "12)" and "а)" ARE the label. The printer put them there to mark the
    item, so finding them finds the thing itself. That is why the rule
    generalised to 90/90 across 60 unseen pages.
  * Latin script is a CORRELATE. It coincides with dance titles in the
    volumes examined; nothing guarantees it. A volume with bare RUSSIAN
    titles would defeat it silently, which is the worst failure mode --
    it would look like the page simply had no items.

Recognising "this is a dance title followed by who performed it" is a
judgement about meaning, not typography, and belongs in a later pass over
finished text where it is free to iterate and never re-pays for vision.
Same place the language-ID pass sits. See docs/season_reviews.md, deferred
work, and the general rule: the vision pass records FORM; meaning is
assigned downstream.

Usage:
    python pipeline/segment_reviews.py --parsed-dir outputs/reviews/parsed \
        --out-dir outputs/reviews/segmented
    python pipeline/segment_reviews.py --raw-dir outputs/reviews/raw --report
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import (BlockLLM, ReviewPageLLM, SpanLLM,
                            block_plain_text, spans_plain_text)

# "1)" ... "99)", and single Latin or Cyrillic letters "a)" "б)". Must be
# preceded by start-of-text or whitespace and followed by whitespace, so a
# page reference like "(см. 4)" inside a word does not match.
ENUMERATOR = re.compile(r"(?:^|(?<=[\s\n]))(\d{1,2}\)|[a-zA-Zа-яёА-ЯЁ]\))(?=\s)")


def folded_text(block: BlockLLM) -> str:
    """The block's text with its enumerator FIELD put back inline.

    The model is inconsistent about this by design -- when it recognises an
    item it lifts the label into `enumerator`, and when it does not the
    label simply stays in the prose. Folding covers both, which is why this
    works against the extraction prompt unchanged."""
    t = block_plain_text(block) or spans_plain_text(block.caption)
    e = (block.enumerator or "").strip()
    return f"{e} {t}" if e else t


def split_block(block: BlockLLM) -> list[BlockLLM]:
    """Split one block at each enumerator found in its text.

    Returns [block] unchanged when there is nothing to split, so this is
    safe to run over every block on every page."""
    text = folded_text(block)
    hits = list(ENUMERATOR.finditer(text))
    if len(hits) < 2 and not (hits and hits[0].start() == 0):
        return [block]

    cuts = [m.start() for m in hits]
    if cuts[0] > 0:
        cuts.insert(0, 0)          # keep any lead-in prose as its own piece
    out: list[BlockLLM] = []
    for i, start in enumerate(cuts):
        end = cuts[i + 1] if i + 1 < len(cuts) else len(text)
        piece = text[start:end].strip()
        if not piece:
            continue
        m = ENUMERATOR.match(piece)
        enum = m.group(1) if m else ""
        body = piece[m.end():].lstrip() if m else piece
        out.append(BlockLLM(
            block_type=block.block_type if enum else "paragraph",
            enumerator=enum,
            spans=[SpanLLM(text=body)],
        ))
    return out or [block]


def segment_page(page: ReviewPageLLM) -> tuple[ReviewPageLLM, int]:
    blocks, added = [], 0
    for b in page.blocks:
        if b.block_type == "figure":       # captions are not item lists
            blocks.append(b)
            continue
        pieces = split_block(b)
        added += len(pieces) - 1
        blocks.extend(pieces)
    return page.model_copy(update={"blocks": blocks}), added


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--parsed-dir", type=Path)
    src.add_argument("--raw-dir", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--report", action="store_true",
                    help="print what would change; write nothing")
    args = ap.parse_args()

    in_dir = args.parsed_dir or args.raw_dir
    files = sorted(in_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no *.json in {in_dir}")
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)

    tot_added = tot_pages = 0
    for f in files:
        page = ReviewPageLLM.model_validate(
            json.loads(f.read_text(encoding="utf-8")))
        out, added = segment_page(page)
        tot_added += added
        tot_pages += bool(added)
        if added and args.report:
            print(f"  {f.stem:44} {len(page.blocks):3d} -> {len(out.blocks):3d}")
        if args.out_dir:
            (args.out_dir / f.name).write_text(
                out.model_dump_json(indent=2), encoding="utf-8")
    print(f"\n{len(files)} pages | {tot_pages} changed | {tot_added} items split out")
    if args.out_dir:
        print(f"-> {args.out_dir}")


if __name__ == "__main__":
    main()
