"""Consolidates a split source page's two halves into one trusted session
list, using dedup_split_overlap.py's review queue as the source of truth
for every colliding (day, theater, session) key. This is the step that
actually enforces the two guarantees RG set for Option B (2026-09-14,
docs/eval/known_issues.md #70):

  1. NEVER LOSE TEXT. Every session in either half's raw.json ends up
     somewhere in this script's output -- the trusted list, or (for a
     colliding key nobody has resolved yet) `pending_review.json`. Nothing
     is ever silently dropped. A non-colliding key (present on only one
     half -- the overwhelming majority of rows) passes straight through
     unchanged; there is nothing to resolve there.
  2. NEVER MAKE UP TEXT. Every session this script emits is either (a) a
     row a model call actually produced, verbatim, or (b) a human's own
     verified transcription recorded in the queue's corrected_* columns,
     verbatim. Nothing is blended, interpolated, or guessed. Automatic
     resolution (no human needed) is intentionally narrow -- see below.

What resolves automatically vs. what waits for a human, per
dedup_split_overlap.py's tiers:
  - `exact`      -- both copies are byte-identical. Keeping either is
    deduplicating a literal duplicate, not fabricating anything -- auto-
    resolved.
  - `clear`      -- one copy is a strict superset of the other (more
    works, no conflicting receipts/annotation). Keeping the fuller one is
    still just selecting between two REAL reads with no conflict between
    them -- auto-resolved.
  - `ambiguous`  -- the two reads disagree. This is exactly the case
    where guessing would violate guarantee 2 (confirmed necessary this
    session: in several hand-checked cases, BOTH machine reads were
    wrong, and only reading the actual scan produced the true text -- see
    known_issues.md #70's boundary-row-misalignment addendum). Resolved
    ONLY if the queue row has been hand-annotated: `corrected_*` columns
    (a human's own transcription, checked against the scan) take
    priority over `kept_half` (a human's judgment that one machine read

CAUTION (added 2026-09-17, known_issues.md #70's receipts-residual
addenda): this script's OWN inputs are `--raw-dir` (raw model output)
and `--queue` (collision resolutions) -- it has no way to know about
content corrections that were applied AFTER the fact, directly to an
`--out-dir` file, for errors that were never a top/bottom collision in
the first place (a single half's own row simply misread by the model --
28 sessions' worth, across 16 pages, as of the above addenda). Those
corrections live only in the `trusted` list on disk. Re-running this
script recomputes `trusted` from scratch and will silently overwrite
that file, discarding them, unless `--force` is passed. Default
behavior is to refuse to overwrite a `trusted` list that would change
from what's on disk, and print exactly which files/sessions differ, so
this can never happen silently.
    was already correct) -- both require a person to have looked. An
    unannotated ambiguous row is written to `pending_review.json`, not
    guessed at, and not dropped.
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dedup_split_overlap import keyed_sessions, base_key, season_of, day_of  # noqa: E402


def load_sessions(raw_dir: Path, page_id: str) -> list[dict]:
    f = raw_dir / f"{page_id}.raw.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))["sessions"]


def _parse_corrected_works(text: str) -> list[dict]:
    """`corrected_works` format: semicolon-separated "title|genre" pairs,
    genre optional (omit the trailing "|" if there isn't one) -- e.g.
    "Иоаннъ Лейденскій|оп.; Гроза" -> two works, the second with no
    genre. A human types this straight from the scan; never generated
    automatically."""
    works = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            title, genre = part.split("|", 1)
            works.append({"work_title": title.strip(), "genre": genre.strip() or None})
        else:
            works.append({"work_title": part, "genre": None})
    return works


def resolve_row(queue_row: dict, ts: dict, bs: dict) -> list[tuple[dict, str]]:
    """Returns a list of (session, disposition) pairs to add to trusted.
    Empty list means this key is still unresolved (tier 'ambiguous' with
    no hand annotation) -- the caller routes that to pending_review.json,
    never drops it. Almost always at most one pair; `kept_half == "both"`
    is the one exception (see below) and returns two.

    "both" (2026-09-15, hand-resolving the pending queue): confirmed
    this session that day-only matching (day-of-month, ignoring month)
    can produce a FALSE collision -- two genuinely different, both-
    correct calendar days that happen to share a day-of-month digit,
    most likely when one is near a split boundary and the other is a
    much-later occurrence deep in the same half's own list (found on
    `1897-98_p020`/`p021`: top's Feb 27 collided with bottom's own,
    unrelated, later-season day 27). Picking either side here would
    silently discard a real, correct, distinct row -- so a human marking
    `kept_half=both` keeps both verbatim as separate trusted sessions
    rather than being forced into a choice that violates "never lose
    text". Distinct from `corrected_*`, which represents one merged
    human transcription, not two independently-valid raw reads."""
    tier = queue_row["tier"]
    if tier == "exact":
        return [(dict(ts), "auto:exact")]
    if tier == "clear":
        chosen = ts if queue_row["suggested_keep"] == "top" else bs
        return [(dict(chosen), f"auto:clear:{queue_row['suggested_keep']}")]

    # ambiguous -- only a human annotation resolves this
    corrected_works = (queue_row.get("corrected_works") or "").strip()
    corrected_date = (queue_row.get("corrected_date_text") or "").strip()
    if corrected_works or corrected_date:
        session = {
            "date_text": corrected_date or ts["date_text"],
            "month_text": ts.get("month_text"),
            "year_text": ts.get("year_text"),
            "session": ts["session"],
            "theater": ts["theater"],
            "is_dark": False,
            "receipts_text": (queue_row.get("corrected_receipts") or "").strip() or None,
            "annotation": (queue_row.get("corrected_annotation") or "").strip() or None,
            "works": _parse_corrected_works(corrected_works) if corrected_works else [],
        }
        return [(session, "human:corrected")]

    kept_half = (queue_row.get("kept_half") or "").strip().lower()
    if kept_half in ("top", "bottom"):
        chosen = ts if kept_half == "top" else bs
        return [(dict(chosen), f"human:kept_{kept_half}")]
    if kept_half == "both":
        return [(dict(ts), "human:kept_both:top"), (dict(bs), "human:kept_both:bottom")]

    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, required=True,
                     help="directory of <page_id>.raw.json column-wise extraction output")
    ap.add_argument("--page-numbers", type=Path, required=True,
                     help="split_page_numbers.csv (extract_split_page_numbers.py)")
    ap.add_argument("--queue", type=Path, required=True,
                     help="dedup_split_overlap.py's review queue CSV, hand-annotated or not "
                          "-- unannotated ambiguous rows are written to pending_review.json, "
                          "never guessed at")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--force", action="store_true",
                     help="overwrite an existing <page_id>.resolved_sessions.json even if its "
                          "on-disk `trusted` list differs from what this run recomputes -- that "
                          "difference is presumptively a manual content correction applied "
                          "after the fact (see this module's docstring); without --force such a "
                          "file is left untouched and reported instead of silently clobbered")
    args = ap.parse_args()

    # A key can have MORE than one queue row -- dedup_split_overlap.py
    # writes one row per (top, bottom) combination for a month-rollover
    # collision (see its module docstring), so this must be a list, not
    # a single row: collapsing to one via a plain {key: row} dict would
    # silently lose every combination but the last, the exact bug
    # keyed_sessions() exists to prevent elsewhere in this pipeline.
    queue_by_key: dict[tuple, list[dict]] = defaultdict(list)
    for r in csv.DictReader(open(args.queue, encoding="utf-8")):
        key = (r["source_page_id"], r["day"], r["theater"], r["session"])
        queue_by_key[key].append(r)

    def find_queue_row(source_pid: str, key: tuple, ts: dict, bs: dict) -> dict | None:
        """Disambiguates among multiple queue rows sharing a key by
        matching the exact date_text on both sides -- unique per
        combination even though day/theater/session collide."""
        candidates = queue_by_key.get((source_pid, key[0], key[1], key[2]), [])
        for r in candidates:
            if r["top_date_text"] == ts["date_text"] and r["bottom_date_text"] == bs["date_text"]:
                return r
        return candidates[0] if len(candidates) == 1 else None

    number_rows = list(csv.DictReader(open(args.page_numbers, encoding="utf-8")))
    pairs: dict[str, dict[str, int]] = defaultdict(dict)
    for r in number_rows:
        if r["page_number"]:
            pairs[r["source_page_id"]][r["half"]] = int(r["page_number"])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    totals = defaultdict(int)
    pending_all = []
    skipped_diffs = []

    for source_pid, halves in sorted(pairs.items()):
        if "top" not in halves or "bottom" not in halves:
            continue
        season = season_of(source_pid)
        top_pid = f"repertoire_{season}_p{halves['top']:03d}"
        bottom_pid = f"repertoire_{season}_p{halves['bottom']:03d}"
        top_sessions = load_sessions(args.raw_dir, top_pid)
        bottom_sessions = load_sessions(args.raw_dir, bottom_pid)
        if not top_sessions and not bottom_sessions:
            continue

        # See dedup_split_overlap.keyed_sessions's docstring: a plain
        # {(day, theater, session): s} dict comprehension silently drops
        # an earlier session whenever a later one in the SAME half's own
        # list shares its key (a month rollover repeating a day-of-month
        # value) -- confirmed to really happen in this corpus. Grouping
        # by base_key into LISTS (not a single session each) means that
        # case shows up as a group with >1 entry instead of quietly
        # losing one.
        top_by_base: dict[tuple, list] = defaultdict(list)
        for k, s in keyed_sessions(top_sessions).items():
            top_by_base[base_key(k)].append(s)
        bottom_by_base: dict[tuple, list] = defaultdict(list)
        for k, s in keyed_sessions(bottom_sessions).items():
            bottom_by_base[base_key(k)].append(s)
        all_keys = set(top_by_base) | set(bottom_by_base)

        trusted = []
        pending = []
        for key in sorted(all_keys, key=lambda k: (k[0] or "", k[1], k[2])):
            top_group, bottom_group = top_by_base.get(key, []), bottom_by_base.get(key, [])
            if top_group and not bottom_group:
                for s in top_group:
                    trusted.append({**s, "_source": f"{top_pid} (top, no collision)"})
                    totals["passthrough"] += 1
                continue
            if bottom_group and not top_group:
                for s in bottom_group:
                    trusted.append({**s, "_source": f"{bottom_pid} (bottom, no collision)"})
                    totals["passthrough"] += 1
                continue

            if len(top_group) != 1 or len(bottom_group) != 1:
                # A month rollover repeated this (day, theater, session)
                # within one half, at a point that ALSO collides with
                # the other half -- rare. Never guess which top session
                # pairs with which bottom one; each combination gets its
                # own queue row (dedup_split_overlap.py) and is resolved
                # (or left pending) exactly like any other ambiguous row.
                # Combinations that resolve to the literally same content
                # (e.g. one top session correctly dominating two
                # different bottom duplicates) are deduplicated before
                # adding to `trusted` -- otherwise the same real session
                # would be counted twice, the exact double-counting this
                # whole mechanism exists to prevent.
                resolved_sessions, seen_norm = [], set()
                for ts in top_group:
                    for bs in bottom_group:
                        qrow = find_queue_row(source_pid, key, ts, bs)
                        if qrow is None:
                            pending.append({
                                "source_page_id": source_pid, "day": key[0], "theater": key[1],
                                "session": key[2], "reason": "multiple same-key sessions within "
                                "one half (month rollover), collision not in queue -- re-run "
                                "dedup_split_overlap.py against this raw-dir first",
                                "top_session": ts, "bottom_session": bs,
                            })
                            totals["unresolved_not_in_queue"] += 1
                            continue
                        results = resolve_row(qrow, ts, bs)
                        if not results:
                            pending.append({
                                "source_page_id": source_pid, "day": key[0], "theater": key[1],
                                "session": key[2], "reason": "ambiguous (month-rollover "
                                "collision), not yet hand-reviewed",
                                "top_session": ts, "bottom_session": bs,
                            })
                            totals["unresolved"] += 1
                            continue
                        for session, disposition in results:
                            norm = json.dumps(session, sort_keys=True, ensure_ascii=False)
                            if norm not in seen_norm:
                                seen_norm.add(norm)
                                session["_source"] = disposition
                                resolved_sessions.append((session, disposition))
                for session, disposition in resolved_sessions:
                    trusted.append(session)
                    totals[disposition.split(":")[0]] += 1
                continue

            ts, bs = top_group[0], bottom_group[0]
            # collides on both halves -- must go through the queue
            qrow = find_queue_row(source_pid, key, ts, bs)
            if qrow is None:
                # Collision exists in the raw data but wasn't in the queue
                # (queue built from a different raw-dir/run) -- do NOT
                # guess; treat as unresolved rather than silently picking
                # one side.
                pending.append({
                    "source_page_id": source_pid, "day": key[0], "theater": key[1],
                    "session": key[2], "reason": "collision not in queue -- re-run "
                    "dedup_split_overlap.py against this raw-dir first",
                    "top_session": ts, "bottom_session": bs,
                })
                totals["unresolved_not_in_queue"] += 1
                continue
            results = resolve_row(qrow, ts, bs)
            if not results:
                pending.append({
                    "source_page_id": source_pid, "day": key[0], "theater": key[1],
                    "session": key[2], "reason": "ambiguous, not yet hand-reviewed",
                    "top_session": ts, "bottom_session": bs,
                })
                totals["unresolved"] += 1
            else:
                for session, disposition in results:
                    session["_source"] = disposition
                    trusted.append(session)
                    totals[disposition.split(":")[0]] += 1

        out_path = args.out_dir / f"{source_pid}.resolved_sessions.json"
        if out_path.exists() and not args.force:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if existing.get("trusted") != trusted:
                skipped_diffs.append(source_pid)
                pending_all.extend({**p, "source_page_id": source_pid} for p in pending)
                continue
        out_path.write_text(json.dumps({"trusted": trusted, "pending": pending},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
        pending_all.extend({**p, "source_page_id": source_pid} for p in pending)

    print(f"passthrough (no collision): {totals['passthrough']}")
    print(f"auto-resolved (exact/clear): {totals['auto']}")
    print(f"human-resolved (kept_half or corrected): {totals['human']}")
    print(f"still pending review: {totals['unresolved'] + totals['unresolved_not_in_queue']}")
    if totals["unresolved_not_in_queue"]:
        print(f"  ({totals['unresolved_not_in_queue']} of those weren't in the queue at all -- "
              f"re-run dedup_split_overlap.py against the same --raw-dir)")
    print(f"per-page-pair output -> {args.out_dir}/<source_page_id>.resolved_sessions.json")
    if skipped_diffs:
        print(f"\nWARNING: {len(skipped_diffs)} file(s) left UNTOUCHED because their on-disk "
              f"`trusted` list differs from what this run recomputed -- that's presumptively a "
              f"manual content correction applied after the fact (see this module's docstring "
              f"and docs/eval/known_issues.md #70's receipts-residual addenda). Pass --force to "
              f"overwrite anyway once you've confirmed those corrections are captured elsewhere "
              f"(or don't need to be):")
        for pid in skipped_diffs:
            print(f"  {pid}")


if __name__ == "__main__":
    main()
