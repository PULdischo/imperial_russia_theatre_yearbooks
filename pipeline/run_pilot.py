"""Stage 2 batch driver: calls the model concurrently on every page listed in
a manifest, with retry on transient failures, and logs token usage per page.
Saves ONLY the raw JSON response, one file per page -- parsing/validation is
a separate step (parse_and_validate.py) so re-parsing later never requires
re-calling the API.

Despite the name, this now doubles as the general-purpose batch driver (used
for the 12-page pilot originally, and for staged full-corpus batches since --
the manifest and concurrency/retry logic don't care how many rows there are).

Usage:
    python pipeline/run_pilot.py --manifest outputs/administration/manifest.csv \
        --images-dir outputs/administration/images --out-dir outputs/administration/raw \
        --max-concurrent 5
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

sys.path.insert(0, str(Path(__file__).parent))
from schemas import (
    RosterPage, RepertoirePage, DateOnlyPage, TheaterOnlyPage, merge_columnwise_page,
)
from row_detect import detect_rows, detect_columns
from crop_to_table import load_column_config, column_group_for

PROMPTS_DIR = Path(__file__).parent / "prompts"
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"
ROSTER_KINDS = {"Administrators", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}

RETRYABLE = (APIError, APITimeoutError, RateLimitError, ConnectionError, TimeoutError)
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 5

# Split-half date-only columns (2026-09-11 fold-split extraction pilot):
# a single date-only call can silently under-read a long rotated date
# column -- schema satisfied, no exception raised, just wrong (3 rows read
# out of ~13 actually printed, confirmed by direct inspection of the crop).
# A resample of the SAME crop/prompt sometimes recovers completely (3->19
# rows) and sometimes doesn't (stayed stuck at a different-but-still-wrong
# 3 rows) -- unlike the earlier page-number-reading task (which turned out
# to be near-deterministic per crop, see extract_split_page_numbers.py),
# this harder, longer-output task genuinely varies call to call, so
# multiple attempts are worth it here in a way they weren't there.
DATEONLY_MAX_ATTEMPTS = 3
# A theater column doesn't share this failure mode (never observed
# undercounting a theater this way in the pilot); its own row count is
# therefore a same-page, same-scan-quality reference the date column
# SHOULD be broadly comparable to. 0.4x the best theater's row count
# cleanly separates the pilot's good calls (10-19 date rows against
# 11-14 theater rows) from its bad ones (3 date rows against the same
# 11-14) without needing a tighter, more fragile threshold.
DATEONLY_PLAUSIBLE_MIN_FRACTION = 0.4
DATEONLY_PLAUSIBLE_ABS_MIN = 4


def _date_rows_plausible(n_date_rows: int, theater_row_counts: list[int]) -> bool:
    """Judges a date-only read against the theater columns from the SAME
    page -- see DATEONLY_MAX_ATTEMPTS's docstring for why this signal
    exists at all. No theater succeeded -> nothing to compare against,
    so nothing to reject; accept whatever the date call returned."""
    if not theater_row_counts:
        return True
    if n_date_rows < DATEONLY_PLAUSIBLE_ABS_MIN:
        return False
    return n_date_rows >= DATEONLY_PLAUSIBLE_MIN_FRACTION * max(theater_row_counts)


def encode_image(image_path: Path) -> str:
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    ext = image_path.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else f"image/{ext}"
    return f"data:{mime};base64,{data}"


async def call_with_retry(client: AsyncOpenAI, model: str, system_prompt: str,
                            schema: dict, image_data_uri: str) -> tuple[str, dict]:
    full_system = (
        f"{system_prompt}\n\nReturn JSON matching exactly this JSON Schema "
        f"(the top-level object, not the schema itself):\n{json.dumps(schema)}"
    )
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Transcribe this page."},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ]},
                ],
                response_format={"type": "json_object"},
            )
            raw_text = completion.choices[0].message.content
            usage = completion.usage
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", ""),
                "completion_tokens": getattr(usage, "completion_tokens", ""),
                "total_tokens": getattr(usage, "total_tokens", ""),
            } if usage else {"prompt_tokens": "", "completion_tokens": "", "total_tokens": ""}
            return raw_text, usage_dict
        except RETRYABLE as e:
            last_exc = e
            if attempt < MAX_ATTEMPTS:
                wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                print(f"  attempt {attempt} failed ({e!r}), retrying in {wait}s ...", file=sys.stderr)
                await asyncio.sleep(wait)
    raise last_exc


async def process_page(client: AsyncOpenAI, sem: asyncio.Semaphore, row: dict,
                        images_dir: Path, out_dir: Path, model: str,
                        roster_prompt: str, repertoire_prompt: str,
                        roster_schema: dict, repertoire_schema: dict) -> dict:
    page_id = row["page_id"]
    out_path = out_dir / f"{page_id}.raw.json"
    log_row = {"page_id": page_id, "status": "", "attempts": "", "elapsed_seconds": "",
               "prompt_tokens": "", "completion_tokens": "", "total_tokens": "", "error": ""}

    if out_path.exists():
        log_row["status"] = "skipped_existing"
        return log_row

    # extension-agnostic: render_pages.py normally writes .png, but oversized
    # pages (some early-season Repertoire pages exceed DashScope's ~20MB
    # data-uri limit as PNG) get manually converted to .jpg -- same page_id,
    # different extension, so check both rather than hardcoding one.
    image_path = images_dir / f"{page_id}.png"
    if not image_path.exists():
        image_path = images_dir / f"{page_id}.jpg"
    if not image_path.exists():
        log_row["status"] = "missing_image"
        log_row["error"] = str(images_dir / f"{page_id}.(png|jpg)")
        return log_row

    kind = "roster" if row["entity_type"] in ROSTER_KINDS else "repertoire"
    system_prompt = roster_prompt if kind == "roster" else repertoire_prompt
    schema = roster_schema if kind == "roster" else repertoire_schema

    async with sem:
        t0 = time.monotonic()
        try:
            image_data_uri = encode_image(image_path)
            raw_text, usage = await call_with_retry(client, model, system_prompt, schema, image_data_uri)
            out_path.write_text(raw_text, encoding="utf-8")
            log_row.update(status="ok", elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage)
        except Exception as e:
            log_row.update(status="failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}", error=str(e))
        return log_row


async def call_one_row(client: AsyncOpenAI, sem: asyncio.Semaphore, model: str,
                        repertoire_prompt: str, repertoire_schema: dict,
                        image_path: Path) -> tuple[list[dict], dict]:
    """One row-crop's API call, guarded by the SAME semaphore every other
    call (page-level or row-level) shares -- this is what keeps N rows/page
    from multiplying concurrency past --max-concurrent, per the plan's
    section 3. Returns (sessions, usage) for this one row; raises on
    failure after retries (caller decides how to handle a partial page)."""
    async with sem:
        image_data_uri = encode_image(image_path)
        raw_text, usage = await call_with_retry(
            client, model, repertoire_prompt, repertoire_schema, image_data_uri)
    parsed = json.loads(raw_text)
    return parsed.get("sessions", []), usage


async def process_page_rowlevel(client: AsyncOpenAI, sem: asyncio.Semaphore, row: dict,
                                 images_dir: Path, out_dir: Path, row_crops_dir: Path,
                                 model: str, repertoire_prompt: str, repertoire_schema: dict,
                                 header_line_count: int,
                                 corrected_analysis_dir: Path | None = None,
                                 outer_top_border: bool = True) -> dict:
    """Row-isolated Repertoire extraction (known_issues.md #1/#49): detect
    each dated row locally (free, no API cost), crop it with the header
    reattached and zero neighboring-row content, then issue one API call
    per row instead of one call for the whole page. Concatenates every
    row's `sessions` into ONE page-level {"sessions": [...]} matching the
    existing single-call raw JSON shape exactly, so parse_and_validate.py
    needs zero changes downstream. Only writes the output file if EVERY
    row succeeded -- a partial write would look like `skipped_existing` on
    a re-run and silently keep missing rows forever; better to fail the
    whole page and let a re-run retry it in full, same as the single-call
    path already does on any failure.

    If `corrected_analysis_dir/{page_id}.pkl` exists (a `PageAnalysis`
    pickled after a human review pass -- see `analyze_page`/
    `insert_row_boundary`/`delete_row_boundary`), crops from THAT
    human-confirmed boundary set instead of running fresh automatic
    detection -- the practical bridge between the review workflow and
    this driver until the утро/вечер-divider auto-detection problem
    (known_issues.md #1, 2026-08-27 addendum) is solved, if ever."""
    page_id = row["page_id"]
    out_path = out_dir / f"{page_id}.raw.json"
    log_row = {"page_id": page_id, "status": "", "n_rows": "", "elapsed_seconds": "",
               "prompt_tokens": "", "completion_tokens": "", "total_tokens": "", "error": ""}

    if out_path.exists():
        log_row["status"] = "skipped_existing"
        return log_row

    image_path = images_dir / f"{page_id}.png"
    if not image_path.exists():
        image_path = images_dir / f"{page_id}.jpg"
    if not image_path.exists():
        log_row["status"] = "missing_image"
        log_row["error"] = str(images_dir / f"{page_id}.(png|jpg)")
        return log_row

    t0 = time.monotonic()
    analysis = None
    corrected_pkl = (corrected_analysis_dir / f"{page_id}.pkl") if corrected_analysis_dir else None
    if corrected_pkl and corrected_pkl.exists():
        import pickle
        with open(corrected_pkl, "rb") as f:
            analysis = pickle.load(f)
    try:
        row_crops = detect_rows(image_path, row_crops_dir / page_id,
                                 header_line_count=header_line_count, analysis=analysis,
                                 outer_top_border=outer_top_border)
    except Exception as e:
        log_row.update(status="row_detect_failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}",
                        error=str(e))
        return log_row

    results = await asyncio.gather(
        *[call_one_row(client, sem, model, repertoire_prompt, repertoire_schema,
                        Path(c.image_path)) for c in row_crops],
        return_exceptions=True,
    )

    all_sessions: list[dict] = []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    failures = [(i, r) for i, r in enumerate(results) if isinstance(r, Exception)]
    if failures:
        log_row.update(
            status="failed", n_rows=len(row_crops),
            elapsed_seconds=f"{time.monotonic() - t0:.1f}",
            error=f"{len(failures)}/{len(row_crops)} row call(s) failed, e.g. row "
                  f"{failures[0][0] + 1}: {failures[0][1]!r}",
        )
        return log_row

    for sessions, usage in results:
        all_sessions.extend(sessions)
        for k in usage_totals:
            v = usage.get(k)
            if v:
                usage_totals[k] += int(v)

    out_path.write_text(json.dumps({"sessions": all_sessions}, ensure_ascii=False),
                         encoding="utf-8")
    log_row.update(status="ok", n_rows=len(row_crops),
                    elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage_totals)
    return log_row


async def call_dateonly(client: AsyncOpenAI, sem: asyncio.Semaphore, model: str,
                         prompt: str, schema: dict, image_path: Path) -> tuple[list[dict], dict]:
    """The date-only crop's API call, same semaphore discipline as
    `call_one_row`. Returns (rows, usage); raises on failure after retries."""
    async with sem:
        image_data_uri = encode_image(image_path)
        raw_text, usage = await call_with_retry(client, model, prompt, schema, image_data_uri)
    parsed = json.loads(raw_text)
    return parsed.get("rows", []), usage


async def call_theateronly(client: AsyncOpenAI, sem: asyncio.Semaphore, model: str,
                            prompt: str, schema: dict, image_path: Path
                            ) -> tuple[str, list[dict], dict]:
    """One theater-only crop's API call. Returns (theater_name, rows,
    usage) -- the theater name is read by the model from the crop's own
    header, not supplied by the caller (see TheaterOnlyPage's docstring:
    manifest.csv has no per-page theater-name list). Raises on failure
    after retries."""
    async with sem:
        image_data_uri = encode_image(image_path)
        raw_text, usage = await call_with_retry(client, model, prompt, schema, image_data_uri)
    parsed = json.loads(raw_text)
    return parsed.get("theater", ""), parsed.get("rows", []), usage


async def process_page_columnwise(client: AsyncOpenAI, sem: asyncio.Semaphore, row: dict,
                                   images_dir: Path, out_dir: Path, column_crops_dir: Path,
                                   model: str, dateonly_prompt: str, theateronly_prompt: str,
                                   dateonly_schema: dict, theateronly_schema: dict,
                                   column_config: dict | None = None) -> dict:
    """Column-wise Repertoire extraction (known_issues.md #68): reads the
    date column once and each theater column once, independently -- no
    row-boundary detection involved at all, so this is structurally
    immune to the row-boundary problem row-level extraction still
    depends on. Not a replacement for row-level or full-page extraction;
    written to `out_dir` (a SEPARATE directory from either, e.g.
    outputs/<run>/raw_columnwise/) specifically as a second, independent
    read for the row-vs-column-vs-page cross-check in quality_checks.py
    to compare against -- three genuinely different failure modes, not
    three attempts at the same thing.

    Days a theater cannot be reconciled against are reported rather than
    guessed at, but the days that DO reconcile are kept (2026-09-08). The
    previous behaviour dropped the whole theater-page on any single
    ambiguity, which measured at 79% loss for columns carrying even one
    compound morning/evening day (docs/eval/known_issues.md #69). Per-column
    outcomes, and the raw per-column reads behind them, are written to
    `<page_id>.columns.json` beside the merged page.

    `column_config` (2026-09-08, docs/repertoire_column_bounds.json)
    supplies each page's column positions from a per-season measurement
    instead of detecting them on that page. Per-page detection finds the
    right column count on only 31/40 pages of a season, and when it is
    wrong it can be wrong SILENTLY -- on repertoire_1898-99_p024 it once
    produced a theater's content where the date crop belonged. The config
    also carries `date_side`, which matters because the two formats put
    the date column on opposite sides. Falls back to per-page detection
    when no config is given or the page has no entry."""
    page_id = row["page_id"]
    out_path = out_dir / f"{page_id}.raw.json"
    log_row = {"page_id": page_id, "status": "", "n_theaters_ok": "", "n_theaters_total": "",
               "elapsed_seconds": "", "prompt_tokens": "", "completion_tokens": "",
               "total_tokens": "", "error": ""}

    if out_path.exists():
        log_row["status"] = "skipped_existing"
        return log_row

    image_path = images_dir / f"{page_id}.png"
    if not image_path.exists():
        image_path = images_dir / f"{page_id}.jpg"
    if not image_path.exists():
        log_row["status"] = "missing_image"
        log_row["error"] = str(images_dir / f"{page_id}.(png|jpg)")
        return log_row

    t0 = time.monotonic()
    try:
        group = column_group_for(page_id, column_config) if column_config else None
        if group is not None:
            # theater_pad is an optional per-group override (2026-09-10,
            # docs/eval/known_issues.md #69) -- absent for every group except
            # 1903-04, where the Александринскій column's guest German-troupe
            # weeks need much more right-side padding than this corpus's
            # usual Russian abbreviations (theater_pad=15 clipped titles and
            # receipts figures mid-word/mid-number, confirmed against the
            # scan). Not raised as the new *default*: the narrowest
            # spread-format seasons' columns are only ~300px wide, and a
            # symmetric 150px pad from each neighbor would consume nearly
            # the whole column -- this needs to stay a per-group opt-in, not
            # a global constant.
            kwargs = dict(dividers_frac=group["dividers"], date_side=group["date_side"])
            if "theater_pad" in group:
                kwargs["theater_pad"] = group["theater_pad"]
            if "date_col_width_frac" in group:
                kwargs["date_col_width_frac"] = group["date_col_width_frac"]
            if "theater_pad_overrides" in group:
                # JSON keys are always strings; detect_columns keys its
                # overrides by the 0-based int theater_index (2026-09-15,
                # docs/eval/known_issues.md #70 addendum).
                kwargs["theater_pad_overrides"] = {
                    int(k): v for k, v in group["theater_pad_overrides"].items()
                }
            columns = detect_columns(image_path, column_crops_dir / page_id, **kwargs)
        else:
            columns = detect_columns(image_path, column_crops_dir / page_id)
    except Exception as e:
        log_row.update(status="column_detect_failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}",
                        error=str(e))
        return log_row

    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _accumulate(usage: dict):
        for k in usage_totals:
            v = usage.get(k)
            if v:
                usage_totals[k] += int(v)

    # Theater columns kick off immediately, in parallel with the date-only
    # attempts below -- their row counts are what judges date-only
    # plausibility, so they're needed either way, and there's no reason to
    # wait for them serially first.
    theater_task = asyncio.gather(
        *[call_theateronly(client, sem, model, theateronly_prompt, theateronly_schema,
                            Path(c.theater_image_path))
          for c in columns],
        return_exceptions=True,
    )

    date_rows = None
    date_all_attempts: list[list[dict]] = []
    theater_results = None
    for attempt in range(1, DATEONLY_MAX_ATTEMPTS + 1):
        try:
            rows, usage = await call_dateonly(
                client, sem, model, dateonly_prompt, dateonly_schema, Path(columns[0].date_image_path))
        except Exception as e:
            if attempt == DATEONLY_MAX_ATTEMPTS:
                log_row.update(status="failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}",
                                error=f"date-only call failed: {e!r}")
                return log_row
            continue
        _accumulate(usage)
        date_all_attempts.append(rows)
        if theater_results is None:
            theater_results = await theater_task
        theater_row_counts = [len(r[1]) for r in theater_results if not isinstance(r, Exception)]
        if _date_rows_plausible(len(rows), theater_row_counts):
            date_rows = rows
            break
    if date_rows is None:
        # Every attempt looked implausible -- use whichever attempt read
        # the MOST rows as the best available guess, not just the last one
        # tried. Not treated as a silent success either way: merge_report
        # below still reports per-theater unresolved days from whatever
        # date_rows ends up being, so a still-bad read stays visible
        # downstream rather than being masked by this fallback.
        date_rows = max(date_all_attempts, key=len)
    if theater_results is None:
        theater_results = await theater_task
    results = theater_results

    all_sessions: list[dict] = []
    n_ok = 0
    merge_report = []
    raw_columns = {
        "date_rows": date_rows,
        "date_attempts": len(date_all_attempts),
        "date_all_attempts": date_all_attempts if len(date_all_attempts) > 1 else None,
        "date_plausible": _date_rows_plausible(
            len(date_rows), [len(r[1]) for r in results if not isinstance(r, Exception)]),
        "theaters": {},
    }
    canonical_theaters = group.get("theaters") if group else None
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            continue
        model_said, theater_rows, usage = result
        _accumulate(usage)
        # Prefer the config's own known theater order over the model's read
        # (2026-09-12, full-corpus sweep): confirmed the theater-name header
        # is printed only on a spread's TOP half -- 89 of 90 bottom halves
        # checked came back with EVERY theater crop reading the same
        # (wrong) name, since there's nothing to read on those pages at
        # all. `columns[i].theater_index` is the crop's known left-to-right
        # position, stable regardless of what's printed on any given page;
        # `canonical_theaters[i]` is that season's own fixed print order,
        # already established by direct scan inspection. Falls back to the
        # model's own read when a group has no `theaters` list configured.
        if canonical_theaters and i < len(canonical_theaters):
            theater_name = canonical_theaters[i]
        else:
            theater_name = model_said
        raw_columns["theaters"][theater_name] = theater_rows
        merged = merge_columnwise_page(date_rows, theater_name, theater_rows)
        all_sessions.extend(merged.sessions)
        n_ok += merged.ok
        merge_report.append({
            "theater": theater_name, "model_said": model_said, "ok": merged.ok,
            "n_sessions": len(merged.sessions), "unresolved": merged.unresolved,
            "n_date_days": merged.n_date_days, "n_theater_rows": merged.n_theater_rows,
            "reason": merged.reason,
        })

    out_path.write_text(json.dumps({"sessions": all_sessions}, ensure_ascii=False), encoding="utf-8")
    # The per-column reads and the merge outcome, kept alongside the merged
    # page. Without these a refusal threw its own evidence away: the only way
    # to see WHY a theater failed to reconcile was to pay for the extraction
    # again (2026-09-08).
    (out_path.parent / f"{page_id}.columns.json").write_text(
        json.dumps({"merge": merge_report, "raw": raw_columns}, ensure_ascii=False),
        encoding="utf-8")
    log_row.update(status="ok" if n_ok == len(columns) else "partial",
                    n_theaters_ok=n_ok, n_theaters_total=len(columns),
                    elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage_totals)
    return log_row


async def main_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    # Explicit timeout, not the SDK default -- see repair_columnwise_merge.py's
    # main_async for the full diagnosis (2026-09-10): a long-lived client
    # with no request timeout can get a connection that never completes,
    # hanging silently (0% CPU, connection stays ESTABLISHED) rather than
    # raising something call_with_retry's existing retry loop can catch.
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL, timeout=120.0)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))

    roster_prompt = (PROMPTS_DIR / "roster_system.txt").read_text(encoding="utf-8")
    repertoire_prompt = (PROMPTS_DIR / "repertoire_system.txt").read_text(encoding="utf-8")
    roster_schema = RosterPage.model_json_schema()
    repertoire_schema = RepertoirePage.model_json_schema()

    sem = asyncio.Semaphore(args.max_concurrent)
    if args.column_level:
        # Column-wise path (known_issues.md #68) -- same single-entity-type
        # assumption as --row-level, same reason (not needed for what this
        # was built to test yet).
        dateonly_prompt = (PROMPTS_DIR / "repertoire_dateonly_system.txt").read_text(encoding="utf-8")
        theateronly_prompt = (PROMPTS_DIR / "repertoire_theateronly_system.txt").read_text(encoding="utf-8")
        dateonly_schema = DateOnlyPage.model_json_schema()
        theateronly_schema = TheaterOnlyPage.model_json_schema()
        args.column_crops_dir.mkdir(parents=True, exist_ok=True)
        column_config = load_column_config(args.column_config) if args.column_config else None
        if column_config:
            covered = sum(1 for r in rows if column_group_for(r["page_id"], column_config))
            print(f"column config: {len(column_config)} group(s); covers "
                  f"{covered}/{len(rows)} page(s) -- the rest fall back to per-page detection")
        tasks = [
            process_page_columnwise(client, sem, row, args.images_dir, args.out_dir,
                                     args.column_crops_dir, args.model, dateonly_prompt,
                                     theateronly_prompt, dateonly_schema, theateronly_schema,
                                     column_config=column_config)
            for row in rows
        ]
    elif args.row_level:
        # Row-isolated path (known_issues.md #1/#49) -- assumes every row in
        # this manifest is Repertoire; doesn't yet branch per-row for a
        # mixed manifest containing Roster pages too (not needed for the
        # pilot this was built to test; add that branching before pointing
        # this at a real mixed-entity-type manifest).
        args.row_crops_dir.mkdir(parents=True, exist_ok=True)
        tasks = [
            process_page_rowlevel(client, sem, row, args.images_dir, args.out_dir,
                                   args.row_crops_dir, args.model, repertoire_prompt,
                                   repertoire_schema, args.header_line_count,
                                   args.corrected_analysis_dir,
                                   outer_top_border=not args.cropped_images)
            for row in rows
        ]
    else:
        tasks = [
            process_page(client, sem, row, args.images_dir, args.out_dir, args.model,
                         roster_prompt, repertoire_prompt, roster_schema, repertoire_schema)
            for row in rows
        ]

    log_rows = []
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        result = await coro
        log_rows.append(result)
        print(f"[{i}/{len(tasks)}] {result['page_id']}: {result['status']}"
              + (f" ({result['error']})" if result["error"] else ""))

    # Append, not overwrite: a re-run only retries previously-failed pages
    # (everything else is skipped_existing), so overwriting would discard the
    # token/usage history for every page succeeded by an earlier invocation.
    # Each path logs to its own file -- their log_row shapes differ
    # (n_rows vs n_theaters_ok/n_theaters_total vs attempts), and each file
    # is appended to over time, so mixing shapes into one CSV risks a
    # DictWriter error on a later run with a different shape.
    if args.column_level:
        usage_filename = "usage_log_columnwise.csv"
        default_fieldnames = ["page_id", "status", "n_theaters_ok", "n_theaters_total",
                               "elapsed_seconds", "prompt_tokens", "completion_tokens",
                               "total_tokens", "error"]
    elif args.row_level:
        usage_filename = "usage_log_rowlevel.csv"
        default_fieldnames = ["page_id", "status", "n_rows", "elapsed_seconds",
                               "prompt_tokens", "completion_tokens", "total_tokens", "error"]
    else:
        usage_filename = "usage_log.csv"
        default_fieldnames = ["page_id", "status", "attempts", "elapsed_seconds",
                               "prompt_tokens", "completion_tokens", "total_tokens", "error"]
    usage_path = args.out_dir / usage_filename
    fieldnames = list(log_rows[0].keys()) if log_rows else default_fieldnames
    write_header = not usage_path.exists()
    with open(usage_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        w.writerows(log_rows)

    ok = sum(1 for r in log_rows if r["status"] == "ok")
    skipped = sum(1 for r in log_rows if r["status"] == "skipped_existing")
    failed = sum(1 for r in log_rows if r["status"] == "failed")
    missing = sum(1 for r in log_rows if r["status"] == "missing_image")
    total_tokens = sum(int(r["total_tokens"]) for r in log_rows if r["total_tokens"])
    print(f"\nok={ok} skipped={skipped} failed={failed} missing_image={missing}")
    print(f"total tokens billed this run: {total_tokens}")
    print(f"usage log -> {usage_path}")
    if failed:
        print(f"\n{failed} page(s) FAILED after {MAX_ATTEMPTS} attempts each -- re-run this "
              f"same command to retry just those (everything else is skipped as already-done).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-concurrent", type=int, default=5)
    ap.add_argument("--row-level", action="store_true",
                     help="row-isolated Repertoire extraction (known_issues.md #1/#49) -- "
                          "one API call per detected row instead of one per page. Assumes "
                          "every row in --manifest is Repertoire.")
    ap.add_argument("--row-crops-dir", type=Path, default=None,
                     help="where row_detect.py writes cropped row images; defaults to "
                          "<out-dir>/row_crops")
    ap.add_argument("--header-line-count", type=int, default=1,
                     help="passed through to row_detect.detect_rows -- see its docstring "
                          "for why this isn't universal across pages yet")
    ap.add_argument("--corrected-analysis-dir", type=Path, default=None,
                     help="directory of {page_id}.pkl PageAnalysis files saved after a human "
                          "review pass (analyze_page + insert_row_boundary/delete_row_boundary) "
                          "-- if a page's pkl exists here, crop from that confirmed boundary set "
                          "instead of running fresh automatic detection")
    ap.add_argument("--cropped-images", action="store_true",
                    help="the --images-dir holds pages already cropped to the table "
                         "(pipeline/crop_to_table.py), so the table's own outer top "
                         "rule is out of frame -- see detect_rows(outer_top_border=)")
    ap.add_argument("--column-level", action="store_true",
                     help="column-wise Repertoire extraction (known_issues.md #68) -- reads the "
                          "date column and each theater column independently, no row-boundary "
                          "detection at all. Meant as a SECOND, independent read for the row-vs-"
                          "column-vs-page cross-check, not a replacement for --row-level -- "
                          "write --out-dir to a separate directory from any other pass over the "
                          "same manifest. Assumes every row in --manifest is Repertoire.")
    ap.add_argument("--column-config", type=Path, default=None,
                    help="per-season column divider positions "
                         "(docs/repertoire_column_bounds.json). Without it, columns "
                         "are detected per page, which is less reliable")
    ap.add_argument("--column-crops-dir", type=Path, default=None,
                     help="where row_detect.py writes cropped date/theater column images; "
                          "defaults to <out-dir>/column_crops")
    args = ap.parse_args()
    if args.row_crops_dir is None:
        args.row_crops_dir = args.out_dir / "row_crops"
    if args.column_crops_dir is None:
        args.column_crops_dir = args.out_dir / "column_crops"
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
