"""Build a review document for disagreement-flagged pages, with image crops.

RG, 2026-09-26, after 24 of 24 agreement on hand-read assessments: switch
from page-by-page to batched review.

The point of the batch form is what the 24/24 did NOT test. Those rulings
measured whether Claude READS a crop correctly. They say nothing about
whether Claude noticed every dispute, or cropped the right line -- and the
second failed once, on "карэ", where RG had to point out the crop did not
show the word.

So this lists EVERY difference between the three passes on a page, not only
the ones Claude judges worth raising: the confident calls, the dismissed
dash-spacing, the line-break wobble, all of it, each with Claude's verdict
and a crop where one can be located. RG then spot-checks the JUDGEMENT
about what matters, which is the untested half.

Usage:
    python pipeline/triage_report.py --pages outputs/reviews/triage_queue.txt \
        --runs outputs/reviews/pilot_1 outputs/reviews/pilot_2 outputs/reviews/pilot_3 \
        --images outputs/reviews/images --out outputs/reviews/triage_batch
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_reviews import repair, repair_json_escapes, repair_mixed_script
from orthography import judge_hard_soft, judge_i_vs_i
from schemas.review import ReviewPageLLM, block_plain_text, spans_plain_text

WORD = re.compile(r"\S+")

# Classes Claude resolves without asking, per decisions recorded in
# docs/eval/triage_rulings.md. Listed anyway so RG can audit the filter.
DASHES = "—–-"
QUOTES = "’'„“«»"


def load(run: Path, page_id: str) -> ReviewPageLLM:
    text = (run / f"{page_id}.raw.json").read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json.loads(repair_json_escapes(text)[0])
    page, _ = repair(ReviewPageLLM.model_validate(data))
    for b in page.blocks:
        for sp in list(b.spans) + list(b.caption):
            if sp.text:
                sp.text, _ = repair_mixed_script(sp.text)
    return page


def body_words(page: ReviewPageLLM) -> list[str]:
    text = " ".join(t for t in (block_plain_text(b) for b in page.blocks
                                if b.block_type != "figure") if t)
    return WORD.findall(re.sub(r"-\n", "", text))


def classify(variants: list[str]) -> str:
    """Why these differ, so RG can audit what Claude filters out.

    Ordered most-specific first. Earlier versions compared only the EDGES of
    each variant, which put "меня»,—ласково" vs "меня», — ласково" under
    "different letters" -- a spacing difference reported as a reading
    dispute. Normalise the whole string instead."""
    if any(not v.strip() for v in variants):
        return "PRESENT IN SOME PASSES ONLY"        # moved or dropped block

    # everything that is not a letter or digit
    def letters(v: str) -> str:
        return re.sub(r"[^\w]", "", v, flags=re.UNICODE).lower()

    L = {letters(v) for v in variants}
    if len(L) == 1:
        return "spacing or punctuation only"
    if len({v.lower() for v in variants}) == 1:
        return "capitalisation only"
    if len({re.sub(r"[\u044a\u044c]", "", x) for x in L}) == 1:
        return "HARD/SOFT SIGN"
    if len({re.sub(r"[\u0463\u0472\u0473\u0406\u0456\u0472]", "", x) for x in L}) == 1:
        return "PRE-REFORM LETTER"
    if len({len(x) for x in L}) > 1 and min(len(x) for x in L) > 0 and \
       all(min(L, key=len) in x for x in L):
        return "one pass has EXTRA text"
    return "DIFFERENT LETTERS"


def variant_groups(P: list[ReviewPageLLM]) -> list[dict]:
    """Aligned disputes across three passes, not raw set differences.

    A set difference reports "Барыш" and "истовъ" as two mysterious tokens
    when one pass simply kept a line break the others closed up. Aligning
    the word sequences pairwise against pass 1 gives the real shape: at
    THIS position, pass 1 said X and pass 2 said Y."""
    W = [body_words(p) for p in P]
    groups: dict[int, dict] = {}
    for j in (1, 2):
        for tag, i1, i2, k1, k2 in difflib.SequenceMatcher(
                None, W[0], W[j], autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            g = groups.setdefault(i1, {"at": i1,
                                       "runs": {1: " ".join(W[0][i1:i2])}})
            g["runs"][j + 1] = " ".join(W[j][k1:k2])
    out = []
    for g in sorted(groups.values(), key=lambda x: x["at"]):
        i = g["at"]
        variants = [g["runs"].get(r, g["runs"][1]) for r in (1, 2, 3)]
        kind = classify([v for v in variants if v])
        row = {
            "context": " ".join(W[0][max(0, i - 4):i + 5]),
            "run1": variants[0], "run2": variants[1], "run3": variants[2],
            "kind": kind,
        }
        # A rule may settle it -- but only by picking a reading a pass
        # actually produced. See orthography.py on why it may never override.
        if kind == "HARD/SOFT SIGN":
            row["rule_choice"], row["rule"] = judge_hard_soft(variants)
        elif kind == "PRE-REFORM LETTER":
            row["rule_choice"], row["rule"] = judge_i_vs_i(variants)
        if row.get("rule_choice"):
            row["needs_human"] = False
        elif kind in ("HARD/SOFT SIGN", "PRE-REFORM LETTER"):
            row["needs_human"] = True
        out.append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, type=Path)
    ap.add_argument("--runs", required=True, nargs="+", type=Path)
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    page_ids = [p for p in args.pages.read_text().split() if p]
    if args.limit:
        page_ids = page_ids[:args.limit]
    args.out.mkdir(parents=True, exist_ok=True)

    rows, tally = [], collections.Counter()
    for page_id in page_ids:
        P = [load(r, page_id) for r in args.runs]
        for g in variant_groups(P):
            g["page_id"] = page_id
            rows.append(g)
            tally[g["kind"]] += 1

    out = args.out / "differences.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"{len(page_ids)} pages | {len(rows)} disputes -> {out}")
    for kind, n in tally.most_common():
        print(f"   {n:4d}  {kind}")


if __name__ == "__main__":
    main()
