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

Metrics
-------
cer                 headline: edit distance / gold length, over plain text
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
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gold_reviews import is_filled_in, parse_gold_file
from parse_reviews import repair
from schemas.review import ReviewPageLLM, page_plain_text

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


def score_page(gold: ReviewPageLLM, pred: ReviewPageLLM) -> dict:
    g_text, p_text = page_plain_text(gold), page_plain_text(pred)
    dist = edit_distance(g_text, p_text)
    row = {
        "gold_chars": len(g_text),
        "pred_chars": len(p_text),
        "edits": dist,
        "cer": dist / len(g_text) if g_text else (0.0 if not p_text else 1.0),
        "folio_exact": (gold.printed_folio or "") == (pred.printed_folio or ""),
        "gold_blocks": len(gold.blocks),
        "pred_blocks": len(pred.blocks),
        "block_type_ratio": difflib.SequenceMatcher(
            None, [b.block_type for b in gold.blocks],
            [b.block_type for b in pred.blocks]).ratio(),
    }
    for attr in ("razryadka", "bold", "italic", "lang"):
        p, r = pr(marked(gold, attr), marked(pred, attr))
        row[f"{attr}_p"], row[f"{attr}_r"] = p, r
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
        "folio_exact": sum(r["folio_exact"] for r in rows) / n,
        "block_type_ratio": sum(r["block_type_ratio"] for r in rows) / n,
    }
    for attr in ("razryadka", "bold", "italic", "lang"):
        agg[f"{attr}_p"] = sum(r[f"{attr}_p"] for r in rows) / n
        agg[f"{attr}_r"] = sum(r[f"{attr}_r"] for r in rows) / n

    lines = [f"run_id: {args.run_id}", f"pages scored: {n}", ""]
    lines.append(f"{'page':40}{'CER':>8}{'edits':>8}{'blocks g/p':>12}"
                 f"{'struct':>8}{'folio':>7}")
    for r in sorted(rows, key=lambda x: -x["cer"]):
        lines.append(f"{r['page_id']:40}{r['cer']:>8.4f}{r['edits']:>8}"
                     f"{str(r['gold_blocks'])+'/'+str(r['pred_blocks']):>12}"
                     f"{r['block_type_ratio']:>8.2f}"
                     f"{'ok' if r['folio_exact'] else 'MISS':>7}")
    lines += ["", f"MEAN CER: {agg['cer']:.4f}   "
                  f"folio exact: {agg['folio_exact']*100:.0f}%   "
                  f"block-type similarity: {agg['block_type_ratio']:.2f}", ""]
    for attr in ("razryadka", "bold", "italic", "lang"):
        lines.append(f"  {attr:10} P={agg[f'{attr}_p']:.2f}  R={agg[f'{attr}_r']:.2f}")
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
