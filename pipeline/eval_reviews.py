"""Stage 5 of the season-reviews pipeline: score a transcription run against
the hand-typed gold pages (docs/season_reviews.md §11).

THE DESIGN POINT, and the reason this is not a copy of eval_against_gold.py:

  eval_against_gold.py compares gold and predicted rows BY LIST POSITION.
  On pages where the model correctly found people the gold excerpt had
  skipped, every subsequent row compared against the wrong person -- roughly
  half of all reported mismatches in the tabular full run were that artifact
  (known_issues.md #21; real error rate ~1.9%, reported ~14%).

  Prose has an exact analogue and it would bite harder: one extra or missing
  block shifts everything after it. So the headline metric here is character
  error rate over a SEQUENCE ALIGNMENT of the whole page's text, which has no
  positional assumption at all, and block structure is reported SEPARATELY so
  a structural disagreement shows up as a structural finding instead of
  silently destroying the text score.

  That was not enough. Sequence alignment tolerates insertions and deletions
  but NOT a move: a block that is correct and merely somewhere else stops
  being recognisable as matching, and the mismatch propagates. Measured on
  gold page 03 (2026-09-24, run `lines-qwen3vl`), where the model placed a
  63-character photo caption first and the gold places it seventh:

      as returned              49% of gold characters aligned    CER 1.019
      that one block moved     94%                               CER 0.082

  One displaced block took an 8%-wrong page to 102% wrong and dragged the
  corpus mean from ~0.039 to 0.121. So CER is now computed after matching
  predicted blocks to gold blocks BY CONTENT and restoring them to gold's
  order, and the ordering itself is scored separately as `order` -- §11 lists
  reading order as its own metric precisely because it is a different kind of
  error from misreading a letter. `cer_raw` keeps the as-returned number so
  nothing is hidden by the repair.

  Note this deliberately does NOT try to fix under-segmentation: when the
  model returns one block where gold has thirty, the text still aligns fine
  as one long run, and `struct` is the metric that reports it.

Metrics
-------
cer                 headline: edit distance / gold length, over plain text,
                    after restoring gold's block order (see above)
cer_raw             the same, over the blocks exactly as returned
order               fraction of matched block PAIRS in the same relative
                    order as gold; 1.00 = reading order fully agrees
blocks_moved        how many predicted blocks had to be moved
folio_exact         printed folio matched
block_type_ratio    similarity of the block-type sequence (structure only)
<attr>_p / _r       precision and recall for разрядка / bold / italic / lang
punct_delta         per-codepoint count differences for the marks §7 forbids
                    normalising

Usage:
    python pipeline/eval_reviews.py --raw-dir outputs/reviews/raw \
        --gold-dir docs/eval/gold_reviews --run-id qwen3-vl-plus_v1
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gold_reviews import is_filled_in, parse_gold_file
from parse_reviews import repair
from schemas.review import (BlockLLM, ReviewPageLLM, block_plain_text,
                            page_plain_text, spans_plain_text)

# The marks docs/season_reviews.md §7 forbids normalising.
PUNCT = ["«", "»", "„", "“", "—", "–", "-"]
PUNCT_NAMES = {"«": "«", "»": "»", "„": "„", "“": "“",
               "—": "em-dash", "–": "en-dash", "-": "hyphen"}


def _lev(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def edit_distance(gold: str, pred: str) -> int:
    """Exact edit distance, computed only over the segments that differ.

    difflib isolates the matching runs, so the quadratic DP runs on the small
    remainder instead of on two full pages. No external dependency; install
    rapidfuzz if this ever becomes a bottleneck."""
    total = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, gold, pred, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            total += i2 - i1
        elif tag == "insert":
            total += j2 - j1
        else:
            total += _lev(gold[i1:i2], pred[j1:j2])
    return total


def _norm(s: str) -> str:
    return " ".join(s.split())


def marked(page: ReviewPageLLM, attr: str) -> Counter:
    """Multiset of the normalised strings carrying a given attribute."""
    c = Counter()
    for b in page.blocks:
        for s in b.spans + b.caption:
            if attr == "lang":
                if s.lang:
                    c[(s.lang, _norm(s.text))] += 1
            elif getattr(s, attr):
                t = _norm(s.text)
                if t:
                    c[t] += 1
    return c


def pr(gold: Counter, pred: Counter) -> tuple[float, float]:
    hit = sum((gold & pred).values())
    p = hit / sum(pred.values()) if pred else (1.0 if not gold else 0.0)
    r = hit / sum(gold.values()) if gold else (1.0 if not pred else 0.0)
    return p, r



def _block_key(b: BlockLLM) -> str:
    """The text a block contributes, normalised for matching only.

    Caption is included because a figure block's text often lives entirely
    there. Whitespace is collapsed so that a line-break disagreement cannot
    stop two blocks from being recognised as the same block."""
    return _norm(block_plain_text(b) + " " + spans_plain_text(b.caption))


def align_blocks(gold: ReviewPageLLM, pred: ReviewPageLLM) -> list[int | None]:
    """For each predicted block, the index of the gold block it belongs at.

    Greedy exclusive matching by similarity, then a containment fallback for
    the two disagreements exclusivity cannot express (both measured
    2026-09-25 on textfirst):

      * MERGE -- one predicted block spanning four gold blocks scores 0.52
        against any single one, under the 0.6 floor, so it went unmatched
        and was parked mid-page. On gold page 03 that one misplacement
        produced CER 0.60 for a page whose text was ~96% right. Fallback:
        if gold blocks are CONTAINED in the predicted one, anchor at the
        earliest of them.
      * SPLIT -- two predicted blocks covering one gold block: only one
        could claim it and the other was orphaned at 0.41. Fallback: a
        predicted block contained in a gold block anchors there even if
        that gold block is already claimed.

    Exclusivity is kept for the first pass on purpose. A global sequence
    alignment was tried instead and is WRONG for this: it is order-preserving
    by construction, so it scored deliberately shuffled pages as order 1.00.
    Per-block search without exclusivity is also wrong -- these pages repeat
    near-identical short blocks ("г-жа Кякштъ;", "г-жа Карсавина;") and the
    repeats anchor to the wrong occurrence."""
    g_keys = [_block_key(b) for b in gold.blocks]
    p_keys = [_block_key(b) for b in pred.blocks]

    pairs = []
    for pi, pk in enumerate(p_keys):
        if not pk:
            continue
        for gi, gk in enumerate(g_keys):
            if not gk:
                continue
            r = difflib.SequenceMatcher(None, gk, pk, autojunk=False).ratio()
            if r >= 0.6:
                pairs.append((r, pi, gi))
    pairs.sort(key=lambda t: -t[0])
    assign: list[int | None] = [None] * len(pred.blocks)
    taken: set[int] = set()
    for _, pi, gi in pairs:
        if assign[pi] is None and gi not in taken:
            assign[pi] = gi
            taken.add(gi)

    for pi, pk in enumerate(p_keys):
        if assign[pi] is not None or not pk:
            continue
        # merge: which gold blocks does this one swallow?
        inside = [gi for gi, gk in enumerate(g_keys)
                  if gk and len(gk) >= 12 and gk in pk]
        if inside:
            assign[pi] = min(inside)
            continue
        # split: which gold block swallows this one?
        holders = [gi for gi, gk in enumerate(g_keys)
                   if gk and len(pk) >= 12 and pk in gk]
        if holders:
            assign[pi] = min(holders)
    return assign


def restore_order(pred: ReviewPageLLM,
                  assign: list[int | None]) -> ReviewPageLLM:
    """Predicted blocks sorted into gold's reading order, by where each
    block's text sits in the gold page (see align_blocks).

    A block with no recognisable anchor keeps its place by inheriting the
    position of the last block that had one, so an unmatched block is never
    flung to one end of the page."""
    keys, last = [], -1.0
    for i, gi in enumerate(assign):
        if gi is not None:
            last = float(gi)
        else:
            last += 1e-3           # just after whatever it followed
        keys.append((last, i))     # original index breaks ties: stable
    order = sorted(range(len(assign)), key=lambda i: keys[i])
    return pred.model_copy(update={"blocks": [pred.blocks[i] for i in order]})


def order_score(assign: list[int | None]) -> tuple[float, int]:
    """(concordant fraction, blocks that had to move).

    Over every PAIR of matched blocks, how often does the model present them
    in the same relative order as the gold. Pairwise rather than positional
    so that one block in the wrong place costs roughly one block's worth of
    score, instead of shifting -- and so penalising -- every block after it.
    """
    idx = [gi for gi in assign if gi is not None]
    if len(idx) < 2:
        return 1.0, 0
    good = tot = 0
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            tot += 1
            if idx[a] < idx[b]:
                good += 1
    moved = sum(1 for a, b in zip(idx, sorted(idx)) if a != b)
    return good / tot, moved


def _relax_indent(s: str) -> str:
    """Collapse leading whitespace on every line.

    RG, 2026-09-25: verse indentation is no longer required. It is rare in
    the corpus and verse is recognisable without it, while reproducing it
    cost 0.4pt of corpus CER on its own -- the single largest recoverable
    chunk of error, and a convention question rather than a model failure.
    Gold KEEPS its indentation (it is the verbatim record); the eval simply
    stops charging the model for not reproducing it."""
    return re.sub(r"(?m)^[ \t]+", "", s)


def score_page(gold: ReviewPageLLM, pred: ReviewPageLLM) -> dict:
    g_text = _relax_indent(page_plain_text(gold))

    # Reading order and transcription are different errors and are scored
    # separately: CER over blocks put back in gold's order, `order` over the
    # ordering itself. cer_raw keeps the as-returned figure.
    assign = align_blocks(gold, pred)
    ordered = restore_order(pred, assign)
    ord_frac, moved = order_score(assign)

    p_text = _relax_indent(page_plain_text(ordered))
    p_text_raw = _relax_indent(page_plain_text(pred))
    dist = edit_distance(g_text, p_text)
    dist_raw = edit_distance(g_text, p_text_raw)

    def _cer(d: int, p: str) -> float:
        return d / len(g_text) if g_text else (0.0 if not p else 1.0)

    row = {
        "gold_chars": len(g_text),
        "pred_chars": len(p_text),
        "edits": dist,
        "cer": _cer(dist, p_text),
        "cer_raw": _cer(dist_raw, p_text_raw),
        "order": ord_frac,
        "blocks_moved": moved,
        "folio_exact": (gold.printed_folio or "") == (pred.printed_folio or ""),
        "gold_blocks": len(gold.blocks),
        "pred_blocks": len(pred.blocks),
        "block_type_ratio": difflib.SequenceMatcher(
            None, [b.block_type for b in gold.blocks],
            [b.block_type for b in pred.blocks]).ratio(),
    }
    for attr in ("razryadka", "bold", "italic", "lang"):
        # Multiset comparison, so ordering never mattered here.
        gm, pm = marked(gold, attr), marked(pred, attr)
        p, r = pr(gm, pm)
        row[f"{attr}_p"], row[f"{attr}_r"] = p, r
        # Raw counts as well, because averaging the per-page rates is
        # badly misleading on a sparse attribute -- see main().
        row[f"{attr}_hit"] = sum((gm & pm).values())
        row[f"{attr}_gold"] = sum(gm.values())
        row[f"{attr}_pred"] = sum(pm.values())
    row["punct_delta"] = {
        PUNCT_NAMES[ch]: p_text.count(ch) - g_text.count(ch)
        for ch in PUNCT if g_text.count(ch) or p_text.count(ch)
    }
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--gold-dir", type=Path, default=Path("docs/eval/gold_reviews"))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--history", type=Path,
                    default=Path("docs/eval/run_history_reviews.csv"))
    args = ap.parse_args()

    gold_files = sorted(args.gold_dir.glob("*.txt"))
    filled = [g for g in gold_files if is_filled_in(g)]
    if not filled:
        raise SystemExit(
            f"no gold file in {args.gold_dir} has been filled in yet "
            f"({len(gold_files)} templates found). Nothing to score against.")

    rows, missing = [], []
    for g in filled:
        page_id = g.stem.split("_", 1)[1]
        raw = args.raw_dir / f"{page_id}.raw.json"
        if not raw.exists():
            missing.append(page_id)
            continue
        gold = parse_gold_file(g)
        pred = ReviewPageLLM.model_validate(
            json.loads(raw.read_text(encoding="utf-8")))
        # Score what the pipeline actually produces, not the unrepaired
        # response -- parse_reviews.py drops empty figure blocks and the like,
        # so without this the block-structure metric compares against output
        # that never reaches disk.
        pred, _ = repair(pred)
        row = score_page(gold, pred)
        row["page_id"] = page_id
        rows.append(row)

    if not rows:
        raise SystemExit("no gold page had a matching extraction to score")

    n = len(rows)
    agg = {
        "run_id": args.run_id,
        "pages": n,
        "cer": sum(r["cer"] for r in rows) / n,
        "cer_raw": sum(r["cer_raw"] for r in rows) / n,
        "order": sum(r["order"] for r in rows) / n,
        "blocks_moved": sum(r["blocks_moved"] for r in rows),
        "folio_exact": sum(r["folio_exact"] for r in rows) / n,
        "block_type_ratio": sum(r["block_type_ratio"] for r in rows) / n,
    }
    # Corpus-wide (micro-averaged) precision/recall, NOT the mean of the
    # per-page rates.
    #
    # These attributes are sparse: разрядка appears on 2 of the 12 gold
    # pages, bold on 1. A page where gold and prediction are both empty
    # scores a trivial 1.0, so averaging per-page rates mostly averages
    # those. Until 2026-09-24 this reported разрядка P=R=0.83 and bold
    # P=R=0.92 -- which read as "usually right" but was exactly
    # (10 x 1.0 + 2 x 0.0)/12: the model found NONE of the 7 real разрядка
    # marks and none of the 1 bold mark. Pooling hits over the corpus
    # instead gives 0.00, which is the truth.
    for attr in ("razryadka", "bold", "italic", "lang"):
        hit = sum(r[f"{attr}_hit"] for r in rows)
        g_n = sum(r[f"{attr}_gold"] for r in rows)
        p_n = sum(r[f"{attr}_pred"] for r in rows)
        agg[f"{attr}_p"] = hit / p_n if p_n else (1.0 if not g_n else 0.0)
        agg[f"{attr}_r"] = hit / g_n if g_n else (1.0 if not p_n else 0.0)
        agg[f"{attr}_gold_n"] = g_n
        agg[f"{attr}_pred_n"] = p_n

    lines = [f"run_id: {args.run_id}", f"pages scored: {n}", ""]
    lines.append(f"{'page':38}{'CER':>8}{'raw':>8}{'edits':>7}"
                 f"{'blocks g/p':>12}{'struct':>8}{'order':>7}{'mv':>4}"
                 f"{'folio':>7}")
    for r in sorted(rows, key=lambda x: -x["cer"]):
        lines.append(f"{r['page_id']:38}{r['cer']:>8.4f}{r['cer_raw']:>8.4f}"
                     f"{r['edits']:>7}"
                     f"{str(r['gold_blocks'])+'/'+str(r['pred_blocks']):>12}"
                     f"{r['block_type_ratio']:>8.2f}{r['order']:>7.2f}"
                     f"{r['blocks_moved']:>4}"
                     f"{'ok' if r['folio_exact'] else 'MISS':>7}")
    lines += ["", f"MEAN CER: {agg['cer']:.4f}   "
                  f"(as returned: {agg['cer_raw']:.4f})   "
                  f"folio exact: {agg['folio_exact']*100:.0f}%", 
              f"reading order: {agg['order']:.2f}   "
              f"blocks moved: {agg['blocks_moved']}   "
              f"block-type similarity: {agg['block_type_ratio']:.2f}", ""]
    lines.append("attributes (corpus-wide, not a per-page average):")
    for attr in ("razryadka", "bold", "italic", "lang"):
        lines.append(f"  {attr:10} P={agg[f'{attr}_p']:.2f}  R={agg[f'{attr}_r']:.2f}"
                     f"   ({agg[f'{attr}_gold_n']} in gold, "
                     f"{agg[f'{attr}_pred_n']} predicted)")
    deltas = Counter()
    for r in rows:
        for k, v in r["punct_delta"].items():
            deltas[k] += v
    lines += ["", "punctuation drift (pred minus gold; 0 = faithful):"]
    for k, v in sorted(deltas.items()):
        lines.append(f"  {k:10} {v:+d}")
    if missing:
        lines += ["", f"gold pages with no extraction yet: {', '.join(missing)}"]

    report = "\n".join(lines)
    print(report)
    out = args.out or Path(args.raw_dir).parent / f"eval_reviews_{args.run_id}.txt"
    out.write_text(report + "\n", encoding="utf-8")
    print(f"\n-> {out}")

    args.history.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.history.exists()
    with open(args.history, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(agg.keys()))
        if write_header:
            w.writeheader()
        w.writerow(agg)
    print(f"-> {args.history}")


if __name__ == "__main__":
    main()
