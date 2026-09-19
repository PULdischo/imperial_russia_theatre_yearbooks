"""Cross-split boundary-row triage (docs/eval/known_issues.md #70, Option
B -- adopted 2026-09-14 after Option A, an attempted crop-trim fix, was
measured and set aside: tested against all 13 confirmed-bug page-pairs, it
left 6 of 17 (35%) confirmed-wrong rows STILL wrong -- some now reconciling
"cleanly" with silently mislabeled content, which is worse than the
original bug in the one way that matters most: it stopped being visible.
That result is why this script's job is deliberately narrow: find and
report, never guess.

split_spread_pages.py deliberately overlaps each half by ~500px past the
true fold cut so a row straddling the fold lands complete in at least one
half -- but that means the SAME printed row can genuinely get captured,
independently, by BOTH halves, and (confirmed this session, extensively
hand-verified) a split half's row detection is measurably unreliable right
at its own boundary edge, in either direction: sometimes misattributing a
neighboring row's content, sometimes dropping the true row outright,
sometimes silently shifting an entire column's date labels by one. No
crop-level fix tested was reliable enough to trust across pages and
seasons on its own (RG, 2026-09-14). So this script does not try to know
which of two boundary reads is right -- it only finds every (day, theater,
session) key that appears in BOTH halves and classifies how much they
agree, so a human (reading the scan) makes the actual call. Nothing here
discards or edits any extracted data; raw.json stays untouched, matching
CLAUDE.md's raw-layer convention.

Two hard guarantees this script and its companion, apply_split_overlap_
resolutions.py, are both built to hold (RG, 2026-09-14):
  1. Never lose text: every session that exists in either half's raw
     output is preserved somewhere downstream -- in the trusted output,
     or (if its key collides with the other half's and they disagree)
     in the pending-review file, never silently dropped. Confirming this
     lives in apply_split_overlap_resolutions.py's own docstring, since
     this script only reads and reports; it never writes a trusted
     dataset itself.
  2. Never make up text: this script and its companion only ever select
     between text a model call ACTUALLY produced, or a human's own
     verified transcription recorded in the resolutions log -- nothing is
     synthesized, blended, or guessed. See `classify`'s docstring for
     exactly which cases that lets get resolved automatically (only
     genuinely non-conflicting ones) versus which are routed to a human.

Tiers, and why hand-reading effort should concentrate on `ambiguous`
(RG, 2026-09-14: "split the queue, concentrate hand-reading on the
ambiguous cases"):
  - `exact`   -- both copies read back byte-identical (same works, same
    receipts_text, same annotation). No content decision to make; auto-
    resolved by apply_split_overlap_resolutions.py without a human step
    -- deduplicating a literal duplicate isn't "making up text".
  - `clear`   -- one copy is a strict superset of the other: same-or-more
    works (as a multiset -- order-independent) AND no conflicting receipts
    or annotation value (only "present vs. missing", never "present but
    different"). Also auto-resolved -- it's a real read that already
    exists, never a fabrication, just the fuller of two actual reads with
    no conflict between them.
  - `ambiguous` -- anything else: conflicting work lists, conflicting
    receipts/annotation values, or one-sided information neither copy's
    fuller than the other's. NEVER auto-resolved. Held out of the trusted
    output until a human resolution is recorded -- see
    apply_split_overlap_resolutions.py.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# Trailing genre abbreviation printed after a comma -- ", оп."/", бал."/
# ", ком."/", вод." etc. -- that one extraction sometimes carries and the
# other doesn't. Stripped only for the *comparison*; both raw readings are
# always kept in the review CSV untouched.
_GENRE_SUFFIX_RE = re.compile(r",\s*[а-яА-Я]{2,5}\.?\s*$")
_DAY_RE = re.compile(r"(\d+)")
_SEASON_RE = re.compile(r"_(\d{4}-\d{2})_")


def _normalize_title(t: str) -> str:
    t = t.strip().rstrip(".")
    t = t.replace("’", "'").replace("ʼ", "'")  # curly apostrophe variants
    t = _GENRE_SUFFIX_RE.sub("", t)
    return t.strip()


def day_of(date_text: str) -> str | None:
    m = _DAY_RE.search(date_text or "")
    return m.group(1) if m else None


def season_of(page_id: str) -> str | None:
    m = _SEASON_RE.search(page_id)
    return m.group(1) if m else None


def load_sessions(raw_dir: Path, page_id: str) -> list[dict]:
    f = raw_dir / f"{page_id}.raw.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))["sessions"]


def keyed_sessions(sessions: list[dict]) -> dict[tuple, dict]:
    """Builds a {key: session} map for one half's OWN session list.

    Found necessary 2026-09-14, verifying the "never lose text" guarantee
    for Option B: a plain `{(day, theater, session): s for s in
    sessions}` dict comprehension -- what this used to do, and what
    apply_split_overlap_resolutions.py also did independently -- silently
    drops an earlier session whenever a LATER one in the same half's own
    list shares its key. Confirmed this really happens, on 16 pages in
    the corpus (42 sessions at risk): a genuine month rollover repeats a
    day-of-month value for the same theater (day 30, then day 1 -- both
    real, different calendar days), and the plain day-of-month key can't
    tell them apart. This is a distinct problem from the cross-half
    collision this module exists to find -- it's a same-half key clash,
    and losing either side of it would violate the guarantee outright.

    Fixed by segmenting each theater's own sequence on day-of-month
    decreases (day-of-month must climb within one printed month; a drop
    means a new month started) before keying, so a rollover repeat gets a
    different key instead of overwriting. If two sessions still land on
    the exact same (month-segment, day, theater, session) key after that
    -- a genuine same-day repeat, or noisy OCR -- neither is dropped
    either: the second gets a disambiguating suffix rather than
    overwriting the first."""
    by_theater: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        by_theater[s["theater"]].append(s)

    keyed: dict[tuple, dict] = {}
    for theater, rows in by_theater.items():
        month_idx = 0
        prev_day: int | None = None
        for s in rows:
            day_text = day_of(s["date_text"])
            day = int(day_text) if day_text is not None else None
            if day is not None and prev_day is not None and day < prev_day:
                month_idx += 1
            if day is not None:
                prev_day = day
            key = (month_idx, day_text, theater, s["session"])
            if key not in keyed:
                keyed[key] = s
            else:
                dup_i = 2
                while (*key, dup_i) in keyed:
                    dup_i += 1
                keyed[(*key, dup_i)] = s
    return keyed


def base_key(k: tuple) -> tuple:
    """Strips keyed_sessions's month segment (and any disambiguation
    suffix) back down to the (day, theater, session) triple that the
    review queue and CSV output key on -- cross-half matching still goes
    by day/theater/session alone (a genuine cross-half collision is
    always within a few days of the fold, never near enough to a month
    rollover for the segment index to matter in practice); the month
    segmentation in `keyed_sessions` only needs to stop a same-half
    overwrite, not participate in cross-half comparison."""
    return k[1], k[2], k[3]


def classify(ts: dict, bs: dict) -> tuple[str, str | None, str]:
    """Returns (tier, suggested_keep, subtier).

    suggested_keep ('top'/'bottom'/None) is a hint for review ordering
    only -- see module docstring. Never applied automatically for the
    'ambiguous' tier; IS what apply_split_overlap_resolutions.py acts on
    automatically for 'clear' (never for a genuine conflict). `subtier`
    only means something for tier=='ambiguous': 'variant_only' means the
    two readings normalize to the same work list (only genre-suffix
    presence or quote-style differs) so review can be a quick orthography
    spot-check rather than a full transcription comparison; 'real' means
    the work lists genuinely disagree even after normalizing and needs
    full hand-reading."""
    tw = Counter(w["work_title"] for w in ts["works"])
    bw = Counter(w["work_title"] for w in bs["works"])
    tr, br = ts.get("receipts_text"), bs.get("receipts_text")
    ta, ba = ts.get("annotation"), bs.get("annotation")

    if tw == bw and tr == br and ta == ba:
        return "exact", None, ""

    def dominates(w1, r1, a1, w2, r2, a2) -> bool:
        # w1 must contain every work w2 has, at least as many times each
        if any(w1[k] < v for k, v in w2.items()):
            return False
        # no conflicting (both-present-but-different) receipts/annotation
        if r2 not in (None, "") and r1 != r2:
            return False
        if a2 not in (None, "") and a1 != a2:
            return False
        return True

    if dominates(tw, tr, ta, bw, br, ba):
        return "clear", "top", ""
    if dominates(bw, br, ba, tw, tr, ta):
        return "clear", "bottom", ""

    ntw = Counter(_normalize_title(k) for k, v in tw.items() for _ in range(v))
    nbw = Counter(_normalize_title(k) for k, v in bw.items() for _ in range(v))
    subtier = "variant_only" if ntw == nbw else "real"
    return "ambiguous", None, subtier


def build_queue(raw_dir: Path, images_dir: Path, page_numbers_csv: Path) -> tuple[list[dict], int]:
    rows = list(csv.DictReader(open(page_numbers_csv, encoding="utf-8")))
    pairs: dict[str, dict[str, int]] = defaultdict(dict)
    for r in rows:
        if r["page_number"]:
            pairs[r["source_page_id"]][r["half"]] = int(r["page_number"])

    queue = []
    checked = 0
    for source_pid, halves in sorted(pairs.items()):
        if "top" not in halves or "bottom" not in halves:
            continue
        season = season_of(source_pid)
        top_pid = f"repertoire_{season}_p{halves['top']:03d}"
        bottom_pid = f"repertoire_{season}_p{halves['bottom']:03d}"
        top_sessions = load_sessions(raw_dir, top_pid)
        bottom_sessions = load_sessions(raw_dir, bottom_pid)
        if not top_sessions or not bottom_sessions:
            continue
        checked += 1

        top_keyed = keyed_sessions(top_sessions)
        bottom_keyed = keyed_sessions(bottom_sessions)
        # Group by base_key (day, theater, session) for cross-half
        # comparison -- see base_key's docstring for why a base_key can
        # legitimately map to more than one session on one side (a month
        # rollover repeating a day-of-month within that same half).
        top_by_base: dict[tuple, list] = defaultdict(list)
        for k, s in top_keyed.items():
            top_by_base[base_key(k)].append(s)
        bottom_by_base: dict[tuple, list] = defaultdict(list)
        for k, s in bottom_keyed.items():
            bottom_by_base[base_key(k)].append(s)

        for key in set(top_by_base) & set(bottom_by_base):
            top_group, bottom_group = top_by_base[key], bottom_by_base[key]
            if len(top_group) != 1 or len(bottom_group) != 1:
                # A base_key with >1 session on either side means a month
                # rollover repeated this (day, theater, session) WITHIN
                # one half, right at a point that also collides with the
                # other half -- rare, and not safe to pair up by
                # guessing which is which. Flag every combination rather
                # than silently matching (or silently skipping) any of
                # them, so nothing is lost.
                for ts in top_group:
                    for bs in bottom_group:
                        queue.append({
                            "source_page_id": source_pid, "top_page_id": top_pid,
                            "bottom_page_id": bottom_pid,
                            "top_image": str(images_dir / f"{top_pid}.png"),
                            "bottom_image": str(images_dir / f"{bottom_pid}.png"),
                            "day": key[0], "theater": key[1], "session": key[2],
                            "tier": "ambiguous", "subtier": "month_rollover_collision",
                            "suggested_keep": "",
                            "top_date_text": ts["date_text"], "top_receipts": ts.get("receipts_text") or "",
                            "top_works": "; ".join(w["work_title"] for w in ts["works"]),
                            "bottom_date_text": bs["date_text"], "bottom_receipts": bs.get("receipts_text") or "",
                            "bottom_works": "; ".join(w["work_title"] for w in bs["works"]),
                            "kept_half": "", "corrected_date_text": "", "corrected_works": "",
                            "corrected_receipts": "", "corrected_annotation": "",
                            "reviewer_note": "multiple same-key sessions within one half "
                                             "(month rollover) collided with the other half "
                                             "-- needs hand disambiguation, not auto-paired",
                        })
                continue
            ts, bs = top_group[0], bottom_group[0]
            tier, suggested, subtier = classify(ts, bs)
            queue.append({
                "source_page_id": source_pid,
                "top_page_id": top_pid,
                "bottom_page_id": bottom_pid,
                "top_image": str(images_dir / f"{top_pid}.png"),
                "bottom_image": str(images_dir / f"{bottom_pid}.png"),
                "day": key[0], "theater": key[1], "session": key[2],
                "tier": tier,
                "subtier": subtier,
                "suggested_keep": suggested or "",
                "top_date_text": ts["date_text"],
                "top_receipts": ts.get("receipts_text") or "",
                "top_works": "; ".join(w["work_title"] for w in ts["works"]),
                "bottom_date_text": bs["date_text"],
                "bottom_receipts": bs.get("receipts_text") or "",
                "bottom_works": "; ".join(w["work_title"] for w in bs["works"]),
                # Filled in during manual review; this same file, once
                # hand-annotated, IS the resolutions input
                # apply_split_overlap_resolutions.py reads -- see that
                # script's docstring. "kept_half" ('top'/'bottom') covers
                # the common case where one side's actual read is simply
                # correct; the "corrected_*" columns are for the rarer
                # case (confirmed to occur this session -- e.g.
                # repertoire_1890-91_p011 Малый day 11, where top was
                # truncated AND bottom was wrong) where NEITHER side's
                # read is fully right and the reviewer types the true
                # transcription straight from the scan. Never both: a row
                # with any corrected_* value takes that over kept_half.
                "kept_half": "",
                "corrected_date_text": "",
                "corrected_works": "",
                "corrected_receipts": "",
                "corrected_annotation": "",
                "reviewer_note": "",
            })
    return queue, checked


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, required=True,
                     help="directory of <page_id>.raw.json column-wise extraction output")
    ap.add_argument("--images-dir", type=Path, required=True,
                     help="split-half images directory, for the review CSV's image pointers")
    ap.add_argument("--page-numbers", type=Path, required=True,
                     help="split_page_numbers.csv (extract_split_page_numbers.py)")
    ap.add_argument("--out", type=Path, required=True, help="review queue CSV path")
    args = ap.parse_args()

    queue, checked = build_queue(args.raw_dir, args.images_dir, args.page_numbers)

    # ambiguous/real first -- that's where hand-reading effort should
    # concentrate; ambiguous/variant_only next (a spot-check, not a full
    # read); clear and exact last (auto-resolved by
    # apply_split_overlap_resolutions.py, listed here only for the audit
    # trail).
    subtier_order = {"month_rollover_collision": -1, "real": 0, "variant_only": 1, "": 2}
    tier_order = {"ambiguous": 0, "clear": 1, "exact": 2}
    queue.sort(key=lambda r: (tier_order[r["tier"]], subtier_order[r["subtier"]],
                               r["source_page_id"], r["day"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(queue[0].keys()) if queue else [])
        w.writeheader()
        w.writerows(queue)

    counts = Counter(r["tier"] for r in queue)
    amb_sub = Counter(r["subtier"] for r in queue if r["tier"] == "ambiguous")
    print(f"checked {checked} source page pairs with data on both halves")
    print(f"{len(queue)} duplicate keys queued -> {args.out}")
    print(f"  ambiguous: {counts['ambiguous']}")
    print(f"    - real:          {amb_sub['real']}  (genuinely differing content -- full hand-read)")
    print(f"    - variant_only:  {amb_sub['variant_only']}  (same works once genre-suffix/quotes normalized -- orthography spot-check)")
    print(f"  clear:     {counts['clear']}  (auto-resolved -- fuller of two real reads, no conflict)")
    print(f"  exact:     {counts['exact']}  (auto-resolved -- literal duplicate)")


if __name__ == "__main__":
    main()
