"""Two-tier repair pass for column-wise Repertoire pages whose merge left
one or more theaters unresolved (docs/eval/known_issues.md #69, 2026-09-10).

Measured across the Gate 3 corpus: 271/996 theater-merge-attempts (27.2%)
fail to reconcile, leaving 171/332 pages missing at least one whole
theater's data (20 of those pages missing all of them). This isn't a
hypothetical edge case -- it's roughly a quarter of the corpus's
theater-columns silently absent from the merged output.

Root cause, per `merge_columnwise_page`'s own design
(pipeline/schemas/repertoire_columnwise.py): a theater's sessions only
land in the output if its own row count reconciles against the date-only
column's day count, or against that column's own compound-day positions
as a fallback. When neither reconciles, the theater is DROPPED, not
guessed at (a deliberate choice -- known_issues.md #69 measured emitting
a plausible-but-wrong-dated row as strictly worse than an honest gap).
That refusal is the right call for a SINGLE extraction attempt, but
doesn't mean the page's true content is unrecoverable.

Two tiers, tried in order, per failed theater:

1. RESAMPLE -- a fresh date-only call plus a fresh theater-only call for
   that page, re-attempted through the SAME merge logic. Validated
   empirically (2026-09-10, random 12-case sample spanning both small and
   large date-count mismatches): recovers about HALF of failures
   outright, including ones with large mismatches, not just off-by-one
   cases. A tier-1 recovery is the same trusted method the rest of the
   corpus already relies on -- no extra scrutiny needed.

2. BASELINE FALLBACK -- for whatever is STILL unresolved after tier 1,
   fall back to one whole-page baseline (single-call) extraction and take
   that theater's sessions from it. Validated on the same 12-case sample:
   recovers SOME data in every case tested, but the row counts frequently
   disagree with what the theater's own column-wise read reported --
   baseline is the extraction method known_issues.md #1/#68 already
   documents as prone to cross-date content bleed, which is why
   column-wise was built to replace it for exactly this table shape.
   Tier-2 rows are marked `_repair_tier: "baseline_fallback"` in the
   report (never silently merged in as equivalent to a column-wise read)
   so they can be routed to review before being trusted the way the rest
   of the corpus is.

Already-OK theaters are read straight from the existing raw JSON and
never touched -- this only re-attempts what was already broken, and never
discards a theater's original successful read to replace it with a fresh
(equally valid, just different) resample.

Usage:
    python pipeline/repair_columnwise_merge.py \\
        --manifest outputs/gate3_columnwise/manifest_<season>.csv \\
        --raw-dir outputs/gate3_columnwise/raw_columnwise \\
        --images-dir <cropped-to-table images for this season> \\
        --baseline-images-dir <full rendered page images, any season> \\
        --out-dir outputs/gate3_columnwise/raw_columnwise_repaired \\
        --column-config docs/repertoire_column_bounds.json \\
        --report-out outputs/gate3_columnwise/repair_report.csv \\
        --max-concurrent 6

One `--images-dir` per invocation, same as run_pilot.py -- seasons with
their own corrected crop (1903-04, 1907-08, see known_issues.md #69) need
their own invocation pointed at their own cropped-images directory, same
as the original Gate 3 run itself required.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).parent))
from schemas import (
    RosterPage, RepertoirePage, DateOnlyPage, TheaterOnlyPage, merge_columnwise_page,
)
from row_detect import detect_columns
from crop_to_table import load_column_config, column_group_for
from run_pilot import (
    call_dateonly, call_theateronly, encode_image, call_with_retry,
    PROMPTS_DIR, BASE_URL, DEFAULT_MODEL,
)
from quality_checks import KNOWN_THEATERS, _normalize_theater, _modernize, _MODERNIZED_THEATERS


def _canonical_theater(theater: str) -> str:
    """Resolves a theater string to its canonical KNOWN_THEATERS name,
    handling the modernized-spelling variant (modern и for pre-reform і)
    as well as `_normalize_theater`'s plain prefix match.

    Confirmed necessary, not just cautious (2026-09-10): a fresh baseline
    call for `repertoire_1899-00_p026` correctly returned "Маріинскій
    театръ" (pre-reform і), but the ORIGINALLY-FAILED theater name from
    the column-wise merge report was "Мариинскій театръ." (modern и,
    known_issues.md #69's modernized_theater_spelling case). Comparing
    both sides through plain `_normalize_theater` alone missed this match
    entirely -- it only matches a string that already starts with the
    CANONICAL spelling, so the modern-и failure name normalized to
    itself, unmatched, and the repair pass reported a real, present
    recovery as `unrecovered`. Two independent calls disagreeing on и/і
    is exactly the kind of surface variance a repair pass must not let
    block a real match."""
    modernized = _modernize(theater.strip())
    for mod_name, canonical in _MODERNIZED_THEATERS.items():
        if modernized.startswith(mod_name):
            return canonical
    return _normalize_theater(theater)

REPORT_FIELDS = ["page_id", "theater", "outcome", "orig_n_date_days", "orig_n_theater_rows",
                 "new_n_date_days", "new_n_theater_rows", "n_sessions_recovered", "detail"]


def _load_repertoire_prompt_and_schema():
    prompt = (PROMPTS_DIR / "repertoire_system.txt").read_text(encoding="utf-8")
    schema = RepertoirePage.model_json_schema()
    return prompt, schema


async def _call_baseline_page(client: AsyncOpenAI, sem: asyncio.Semaphore, model: str,
                               prompt: str, schema: dict, image_path: Path) -> list[dict]:
    async with sem:
        image_data_uri = encode_image(image_path)
        raw_text, _usage = await call_with_retry(client, model, prompt, schema, image_data_uri)
    return json.loads(raw_text).get("sessions", [])


async def repair_page(client: AsyncOpenAI, sem: asyncio.Semaphore, row: dict,
                       images_dir: Path, baseline_images_dir: Path, raw_dir: Path,
                       out_dir: Path, column_crops_dir: Path, model: str,
                       dateonly_prompt: str, theateronly_prompt: str,
                       dateonly_schema: dict, theateronly_schema: dict,
                       baseline_prompt: str, baseline_schema: dict,
                       column_config: dict | None) -> list[dict]:
    """Repairs one page in place if it has any unresolved theater. Returns
    a list of report rows (one per originally-failed theater); an
    already-fully-resolved page returns an empty list and its raw JSON is
    copied through unchanged."""
    page_id = row["page_id"]
    raw_path = raw_dir / f"{page_id}.raw.json"
    columns_path = raw_dir / f"{page_id}.columns.json"
    out_path = out_dir / f"{page_id}.raw.json"

    if not raw_path.exists():
        return [{"page_id": page_id, "theater": "", "outcome": "missing_raw_json",
                  "orig_n_date_days": "", "orig_n_theater_rows": "", "new_n_date_days": "",
                  "new_n_theater_rows": "", "n_sessions_recovered": "", "detail": str(raw_path)}]

    original = json.loads(raw_path.read_text(encoding="utf-8"))
    if not columns_path.exists():
        # No merge report to diagnose from -- nothing to repair against,
        # copy through unchanged rather than guessing.
        out_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        return []

    columns_data = json.loads(columns_path.read_text(encoding="utf-8"))
    failed = [m for m in columns_data.get("merge", []) if not m.get("ok")]
    if not failed:
        out_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        return []

    failed_names = {m["theater"] for m in failed}
    failed_by_name = {m["theater"]: m for m in failed}

    # Sessions from theaters that already succeeded are kept exactly as
    # extracted -- never replaced by a fresh resample, even though tier 1
    # below pays for one anyway (detect_columns/theater-only calls don't
    # know in advance which crop index belongs to which theater name, so
    # every crop on a page needing ANY repair gets re-read; see module
    # docstring).
    #
    # Excluded by CANONICAL name, not exact string -- confirmed necessary,
    # not just cautious (2026-09-10): `1903-04_p030`'s .columns.json
    # recorded a failed theater as "Маріинскій т." (a truncated/garbled
    # header read from whenever that merge report was generated), while
    # the ALREADY-PRESENT sessions for that same theater in its raw.json
    # were correctly labeled "Маріинскій театръ." -- an exact-string
    # exclusion filter didn't recognize these as the same theater, so
    # tier 1's fresh (also successful) resample was appended ON TOP of
    # the already-good sessions rather than replacing them, doubling
    # every row for that theater. A stale or garbled merge-report theater
    # name must not be trusted as a literal key into the raw JSON it
    # describes.
    failed_canonical = {_canonical_theater(n) for n in failed_names}
    kept_sessions = [s for s in original.get("sessions", [])
                      if _canonical_theater(s.get("theater") or "") not in failed_canonical]

    report_rows = []
    image_path = images_dir / f"{page_id}.png"
    if not image_path.exists():
        image_path = images_dir / f"{page_id}.jpg"
    if not image_path.exists():
        for m in failed:
            report_rows.append({"page_id": page_id, "theater": m["theater"],
                                  "outcome": "missing_image", "orig_n_date_days": m["n_date_days"],
                                  "orig_n_theater_rows": m["n_theater_rows"], "new_n_date_days": "",
                                  "new_n_theater_rows": "", "n_sessions_recovered": "",
                                  "detail": str(image_path)})
        out_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        return report_rows

    # --- Tier 1: resample -----------------------------------------------
    group = column_group_for(page_id, column_config) if column_config else None
    try:
        if group is not None:
            kwargs = dict(dividers_frac=group["dividers"], date_side=group["date_side"])
            if "theater_pad" in group:
                kwargs["theater_pad"] = group["theater_pad"]
            columns = detect_columns(image_path, column_crops_dir / page_id, **kwargs)
        else:
            columns = detect_columns(image_path, column_crops_dir / page_id)
    except Exception as e:
        for m in failed:
            report_rows.append({"page_id": page_id, "theater": m["theater"],
                                  "outcome": "column_detect_failed", "orig_n_date_days": m["n_date_days"],
                                  "orig_n_theater_rows": m["n_theater_rows"], "new_n_date_days": "",
                                  "new_n_theater_rows": "", "n_sessions_recovered": "", "detail": str(e)})
        out_path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        return report_rows

    date_rows, date_usage = await call_dateonly(
        client, sem, model, dateonly_prompt, dateonly_schema, Path(columns[0].date_image_path))

    theater_results = await asyncio.gather(
        *[call_theateronly(client, sem, model, theateronly_prompt, theateronly_schema,
                            Path(c.theater_image_path)) for c in columns],
        return_exceptions=True,
    )

    still_failed_names = set(failed_names)
    for result in theater_results:
        if isinstance(result, Exception):
            continue
        theater_name, theater_rows, _usage = result
        # Only theaters that were ORIGINALLY failing get a fresh attempt --
        # a crop whose name doesn't match any originally-failed theater
        # (i.e. it already succeeded) is read here only because tier 1
        # can't know in advance which crop index it needs; its fresh
        # result is discarded unconditionally.
        matched_orig_name = next(
            (n for n in failed_names if _canonical_theater(n) == _canonical_theater(theater_name)),
            None)
        if matched_orig_name is None:
            continue
        merged = merge_columnwise_page(date_rows, theater_name, theater_rows)
        orig = failed_by_name[matched_orig_name]
        if merged.ok:
            kept_sessions.extend(merged.sessions)
            still_failed_names.discard(matched_orig_name)
            report_rows.append({
                "page_id": page_id, "theater": theater_name, "outcome": "recovered_tier1_resample",
                "orig_n_date_days": orig["n_date_days"], "orig_n_theater_rows": orig["n_theater_rows"],
                "new_n_date_days": merged.n_date_days, "new_n_theater_rows": merged.n_theater_rows,
                "n_sessions_recovered": len(merged.sessions), "detail": "",
            })
        else:
            report_rows.append({
                "page_id": page_id, "theater": theater_name, "outcome": "tier1_still_unresolved",
                "orig_n_date_days": orig["n_date_days"], "orig_n_theater_rows": orig["n_theater_rows"],
                "new_n_date_days": merged.n_date_days, "new_n_theater_rows": merged.n_theater_rows,
                "n_sessions_recovered": 0, "detail": merged.reason,
            })

    # A theater name from the ORIGINAL failure list that no fresh crop
    # matched at all (e.g. the model read the header differently this
    # time) is still in still_failed_names here (nothing above discards a
    # name unless its fresh merge actually succeeded) -- tier 2 covers it
    # below the same as an explicit tier-1 failure.

    # --- Tier 2: baseline fallback, only for what's still unresolved ----
    if still_failed_names:
        baseline_image_path = baseline_images_dir / f"{page_id}.png"
        if not baseline_image_path.exists():
            baseline_image_path = baseline_images_dir / f"{page_id}.jpg"
        if baseline_image_path.exists():
            try:
                baseline_sessions = await _call_baseline_page(
                    client, sem, model, baseline_prompt, baseline_schema, baseline_image_path)
            except Exception as e:
                baseline_sessions = None
                baseline_error = str(e)
        else:
            baseline_sessions = None
            baseline_error = str(baseline_image_path)

        for name in sorted(still_failed_names):
            orig = failed_by_name[name]
            if baseline_sessions is None:
                report_rows.append({
                    "page_id": page_id, "theater": name, "outcome": "tier2_baseline_call_failed",
                    "orig_n_date_days": orig["n_date_days"], "orig_n_theater_rows": orig["n_theater_rows"],
                    "new_n_date_days": "", "new_n_theater_rows": "", "n_sessions_recovered": 0,
                    "detail": baseline_error,
                })
                continue
            canonical = _canonical_theater(name)
            matched = [s for s in baseline_sessions
                       if _canonical_theater(s.get("theater") or "") == canonical]
            if matched:
                for s in matched:
                    s["_repair_tier"] = "baseline_fallback"
                kept_sessions.extend(matched)
                report_rows.append({
                    "page_id": page_id, "theater": name, "outcome": "recovered_tier2_baseline",
                    "orig_n_date_days": orig["n_date_days"], "orig_n_theater_rows": orig["n_theater_rows"],
                    "new_n_date_days": "", "new_n_theater_rows": len(matched),
                    "n_sessions_recovered": len(matched),
                    "detail": "NEEDS REVIEW -- baseline extraction, not column-wise; row counts "
                              "have been observed to disagree with the theater's own column read",
                })
            else:
                report_rows.append({
                    "page_id": page_id, "theater": name, "outcome": "unrecovered",
                    "orig_n_date_days": orig["n_date_days"], "orig_n_theater_rows": orig["n_theater_rows"],
                    "new_n_date_days": "", "new_n_theater_rows": "", "n_sessions_recovered": 0,
                    "detail": "baseline extraction did not return this theater either",
                })

    out_path.write_text(json.dumps({"sessions": kept_sessions}, ensure_ascii=False),
                         encoding="utf-8")
    return report_rows


async def main_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    # Explicit timeout AND keep-alive disabled -- neither is the SDK
    # default, and both turned out to matter (2026-09-10). A full-scale
    # repair run stalled repeatedly: established-but-silent TCP
    # connections to the API host sitting at 0% CPU for 5-30+ minutes
    # with zero progress. A fresh, isolated client (this project's own
    # standalone test, outside this script) reached the SAME endpoint in
    # seconds for both a text-only call and a real page-image call,
    # ruling out a DashScope-side outage. Adding just a client `timeout`
    # (so a stall raises `APITimeoutError` for call_with_retry's existing
    # retry loop to catch -- that retry path already existed, nothing
    # timed-out was ever being handed to it) turned the permanent hang
    # into forward progress, but at ~1 page per 4-5 minutes -- consistent
    # with nearly EVERY request first hitting the full 120s timeout
    # before succeeding on retry, not just an occasional one. That
    # pattern -- fine in isolation, reliably stalling only on a
    # long-lived, sustained-use client -- is the signature of a NAT/
    # middlebox silently dropping an idle keep-alive connection without
    # sending a proper close: the socket still looks ESTABLISHED locally,
    # but the first request to reuse it from the pool hangs until the
    # client's own timeout gives up on it. `max_keepalive_connections=0`
    # forces a fresh connection per request, which is otherwise
    # unnecessary overhead but cheap relative to a stalled request, and
    # directly removes the one thing (a reused pooled connection) every
    # hang had in common.
    client = AsyncOpenAI(
        api_key=api_key, base_url=BASE_URL, timeout=120.0,
        http_client=httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=20)),
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.column_crops_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))

    dateonly_prompt = (PROMPTS_DIR / "repertoire_dateonly_system.txt").read_text(encoding="utf-8")
    theateronly_prompt = (PROMPTS_DIR / "repertoire_theateronly_system.txt").read_text(encoding="utf-8")
    dateonly_schema = DateOnlyPage.model_json_schema()
    theateronly_schema = TheaterOnlyPage.model_json_schema()
    baseline_prompt, baseline_schema = _load_repertoire_prompt_and_schema()
    column_config = load_column_config(args.column_config) if args.column_config else None

    sem = asyncio.Semaphore(args.max_concurrent)
    tasks = [
        repair_page(client, sem, row, args.images_dir, args.baseline_images_dir, args.raw_dir,
                    args.out_dir, args.column_crops_dir, args.model, dateonly_prompt,
                    theateronly_prompt, dateonly_schema, theateronly_schema,
                    baseline_prompt, baseline_schema, column_config)
        for row in rows
    ]

    all_report_rows = []
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        report_rows = await coro
        all_report_rows.extend(report_rows)
        pid = report_rows[0]["page_id"] if report_rows else rows[i - 1]["page_id"]
        n_recovered = sum(1 for r in report_rows
                           if r["outcome"].startswith("recovered"))
        print(f"[{i}/{len(tasks)}] {pid}: {len(report_rows)} theater(s) needed repair, "
              f"{n_recovered} recovered")

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.report_out.exists()
    with open(args.report_out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(all_report_rows)

    from collections import Counter
    outcomes = Counter(r["outcome"] for r in all_report_rows)
    print(f"\n{len(all_report_rows)} theater-repair attempt(s) logged -> {args.report_out}")
    for outcome, n in outcomes.most_common():
        print(f"  {outcome}: {n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path,
                     help="existing column-wise raw_columnwise dir, with both "
                          "{page_id}.raw.json and {page_id}.columns.json per page")
    ap.add_argument("--images-dir", required=True, type=Path,
                     help="cropped-to-table images for this season (same as the "
                          "original Gate 3 run used -- season-specific crop fixes apply)")
    ap.add_argument("--baseline-images-dir", required=True, type=Path,
                     help="full rendered page images, for tier-2 baseline fallback")
    ap.add_argument("--out-dir", required=True, type=Path,
                     help="repaired raw JSON is written here, one file per page in "
                          "the manifest (unchanged pages are copied through)")
    ap.add_argument("--column-crops-dir", type=Path, default=None,
                     help="where tier-1's fresh column crops are written; defaults "
                          "to <out-dir>/column_crops")
    ap.add_argument("--column-config", type=Path, default=None)
    ap.add_argument("--report-out", required=True, type=Path,
                     help="repair report CSV (appended to, not overwritten)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-concurrent", type=int, default=6)
    args = ap.parse_args()
    if args.column_crops_dir is None:
        args.column_crops_dir = args.out_dir / "column_crops"
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
