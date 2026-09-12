"""Reads the real printed Yearbook page number off each half of a split
two-page-spread Repertoire image (pipeline/split_spread_pages.py's output),
and checks that the numbers chain correctly -- the cheap verification step
before any extraction budget is spent on the split halves themselves (plan
Phase 3).

Direct inspection of several sample spreads (repertoire_1893-94_p006,
repertoire_1892-93_p001) found the actual printed page number sitting in
the margin along the LEFT edge of each half, printed rotated 90° (read by
rotating counter-clockwise), in the form "— 14 —" -- NOT the running
date-range header, which occupies the *right* edge instead and is a
separate, already-solved problem (extract_page_headers.py). Confirmed
across two different seasons before writing this, same discipline as that
script's own top_fraction tuning.

Crops a narrow strip along the left edge, full height of the half-image,
rotates it upright, and asks for ONE verbatim string -- same verbatim-in/
parse-with-code-after split as extract_page_headers.py and the project's
general date-handling convention (parse in pipeline/schemas/dates.py-style
code, never trust the model to pre-parse).

Usage:
    python pipeline/extract_split_page_numbers.py \
        --split-extents outputs/<run>/split_pages/split_extents.csv \
        --images-dir outputs/<run>/split_pages/images \
        --out outputs/<run>/split_pages/split_page_numbers.csv \
        --max-concurrent 8

    # then, once extraction has run:
    python pipeline/extract_split_page_numbers.py --validate-only \
        --split-extents outputs/<run>/split_pages/split_extents.csv \
        --page-numbers outputs/<run>/split_pages/split_page_numbers.csv
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import io
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from PIL import Image

BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"
PROMPTS_DIR = Path(__file__).parent / "prompts"

RETRYABLE = (APIError, APITimeoutError, RateLimitError, ConnectionError, TimeoutError)
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 5

# Started at 0.12 (measured against repertoire_1893-94_p006,
# repertoire_1892-93_p001, repertoire_1891-92_p001) but that clipped the
# number entirely on repertoire_1892-93_p003__top -- confirmed by direct
# inspection, its "8" sits at ~16% of page width, not ~10% like the others
# (page-to-page scan/trim variation, not a fixed layout constant). Matches
# extract_page_headers.py's own top_fraction=0.20 now, same "generous
# margin" reasoning -- cheap to over-crop, expensive to clip the one thing
# we're looking for.
LEFT_FRACTION = 0.20

PAGE_NUM_SCHEMA = {
    "type": "object",
    "properties": {
        "page_number_text": {
            "type": "string",
            "description": "The leaf's own printed page number, verbatim "
                            "(e.g. '— 14 —'), or empty string if not found.",
        }
    },
    "required": ["page_number_text"],
}

_PAGE_NUM_RE = re.compile(r"(\d+)")


def crop_left_margin(image_path: Path, left_fraction: float = LEFT_FRACTION) -> str:
    """Returns a base64 data URI of the left `left_fraction` of the page,
    full height, rotated 90° counter-clockwise so the page number (printed
    sideways in the render, upright in the true physical page orientation)
    reads normally for the model -- confirmed empirically to be the correct
    rotation direction (the other direction renders it upside down), not
    assumed. Never writes a temp file to disk."""
    im = Image.open(image_path)
    im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
    w, h = im.size
    crop = im.crop((0, 0, int(w * left_fraction), h))
    crop = crop.transpose(Image.Transpose.ROTATE_90)  # PIL's ROTATE_90 is counter-clockwise
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def parse_page_number(text: str) -> int | None:
    """Pulls the integer out of a verbatim '— 14 —'-shaped string. Returns
    None (not a guess) if no digits are present -- an empty/unparseable
    result is a finding for the continuity check below, not something to
    paper over here.

    One specific, well-evidenced fallback: the model twice transcribed a
    printed "11" as "II" (repertoire_1890-91_p003/p004__bottom, then again
    repertoire_1893-94_p004__bottom -- two different seasons, same exact
    misreading) -- the classic I/1 glyph confusion in a serif face, not a
    genuine Roman numeral (a running arabic page-number sequence doesn't
    switch notation for one page). Only re-attempted when the plain digit
    regex finds nothing, and only recognizes this one specific shape
    (one-or-more bare I's/l's, nothing else) -- not a general Roman-numeral
    parser, which would wrongly accept things like "IV" or "IX" as if they
    were page numbers in a different notation."""
    m = _PAGE_NUM_RE.search(text or "")
    if m:
        return int(m.group(1))
    stripped = re.sub(r"[\s—–\-]", "", text or "")
    if stripped and re.fullmatch(r"[Il]+", stripped):
        # Each bare I/l is a misread "1" digit, not a tally -- "II" is a
        # misread "11", not "2" (confirmed: both real occurrences so far
        # were two characters standing in for a two-digit "11", not a
        # count of strokes).
        return int("1" * len(stripped))
    return None


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
                        {"type": "text", "text": "Transcribe the page number."},
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


async def process_half(client: AsyncOpenAI, sem: asyncio.Semaphore, half_id: str,
                        source_page_id: str, half: str, images_dir: Path,
                        model: str, system_prompt: str) -> dict:
    log_row = {"half_id": half_id, "source_page_id": source_page_id, "half": half,
               "status": "", "page_number_text": "", "page_number": "",
               "elapsed_seconds": "", "prompt_tokens": "", "completion_tokens": "",
               "total_tokens": "", "error": ""}

    image_path = images_dir / f"{half_id}.png"
    if not image_path.exists():
        log_row["status"] = "missing_image"
        log_row["error"] = str(image_path)
        return log_row

    async with sem:
        t0 = time.monotonic()
        try:
            image_data_uri = crop_left_margin(image_path)
            raw_text, usage = await call_with_retry(client, model, system_prompt, PAGE_NUM_SCHEMA, image_data_uri)
            parsed = json.loads(raw_text)
            page_number_text = parsed.get("page_number_text", "")
            page_number = parse_page_number(page_number_text)
            log_row.update(status="ok", page_number_text=page_number_text,
                            page_number=page_number if page_number is not None else "",
                            elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage)
        except Exception as e:
            log_row.update(status="failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}", error=str(e))
        return log_row


def load_halves(split_extents_path: Path) -> list[tuple[str, str, str]]:
    """Returns (half_id, source_page_id, half) for both halves of every
    source page in split_extents.csv -- the authoritative list of what
    split_spread_pages.py actually produced, rather than re-deriving it by
    globbing/parsing filenames."""
    rows = list(csv.DictReader(open(split_extents_path, encoding="utf-8")))
    halves = []
    for r in rows:
        page_id = r["page_id"]
        halves.append((f"{page_id}__top", page_id, "top"))
        halves.append((f"{page_id}__bottom", page_id, "bottom"))
    return halves


def validate_continuity(split_extents_path: Path, page_numbers_path: Path) -> list[dict]:
    """The concrete check the plan calls for: a source page's own two
    halves should carry consecutive page numbers (bottom = top + 1), and
    consecutive source pages (in manifest/render order, i.e. the order
    they appear in split_extents.csv) should chain with no gap or
    duplicate across that boundary too. Returns one finding dict per
    problem, empty list if everything chains cleanly -- an empty result is
    itself a finding worth having, not just a silent pass."""
    extents = list(csv.DictReader(open(split_extents_path, encoding="utf-8")))
    numbers_by_half = {r["half_id"]: r for r in csv.DictReader(open(page_numbers_path, encoding="utf-8"))}

    findings = []

    def get_num(half_id: str) -> int | None:
        r = numbers_by_half.get(half_id)
        if r is None or r.get("page_number") in (None, ""):
            return None
        return int(r["page_number"])

    def season_of(page_id: str) -> str:
        # "repertoire_1890-91_p003" -> "repertoire_1890-91" -- each season
        # is its own bound volume with its own page numbering starting
        # over, so a season boundary is never a real continuity break.
        return page_id.rsplit("_p", 1)[0]

    prev_bottom_num = None
    prev_page_id = None
    prev_season = None
    for r in extents:
        page_id = r["page_id"]
        season = season_of(page_id)
        top_id, bottom_id = f"{page_id}__top", f"{page_id}__bottom"
        top_num, bottom_num = get_num(top_id), get_num(bottom_id)

        if top_num is None or bottom_num is None:
            findings.append({"page_id": page_id, "kind": "unreadable",
                              "detail": f"top={top_num} bottom={bottom_num}"})
        elif bottom_num != top_num + 1:
            findings.append({"page_id": page_id, "kind": "within_page_gap",
                              "detail": f"top={top_num} bottom={bottom_num} (expected bottom=top+1)"})

        if (season == prev_season and prev_bottom_num is not None
                and top_num is not None and top_num != prev_bottom_num + 1):
            findings.append({"page_id": f"{prev_page_id}->{page_id}", "kind": "cross_page_gap",
                              "detail": f"prev_bottom={prev_bottom_num} this_top={top_num} "
                                        f"(expected this_top=prev_bottom+1)"})

        prev_bottom_num = bottom_num
        prev_page_id = page_id
        prev_season = season

    return findings


def halves_needing_resample(split_extents_path: Path, page_numbers_path: Path) -> set[str]:
    """Turns validate_continuity()'s findings into a concrete set of
    half_ids to re-call -- the "one independent resample" step the plan
    calls for. For an `unreadable` finding, resample only the side that
    actually came back empty (its sibling was already fine); for a
    `within_page_gap`, resample BOTH halves, since without ground truth
    there's no way to tell from the numbers alone which side is wrong (both
    real occurrences checked by hand this session -- 1890-91_p001,
    1892-93_p003 -- turned out to be a single spurious digit on ONE side,
    but not always predictably which). `cross_page_gap` findings are a
    consequence of a neighboring page's own error, not a new half to
    resample -- they clear once the underlying unreadable/gap finding
    they're chained from is fixed."""
    findings = validate_continuity(split_extents_path, page_numbers_path)
    numbers_by_half = {r["half_id"]: r for r in csv.DictReader(open(page_numbers_path, encoding="utf-8"))}

    to_resample: set[str] = set()
    for f in findings:
        if f["kind"] == "unreadable":
            page_id = f["page_id"]
            for half in ("top", "bottom"):
                half_id = f"{page_id}__{half}"
                r = numbers_by_half.get(half_id)
                if r is None or not r.get("page_number"):
                    to_resample.add(half_id)
        elif f["kind"] == "within_page_gap":
            page_id = f["page_id"]
            to_resample.add(f"{page_id}__top")
            to_resample.add(f"{page_id}__bottom")
    return to_resample


async def resample_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
    system_prompt = (PROMPTS_DIR / "repertoire_splitpagenum_system.txt").read_text(encoding="utf-8")

    all_halves = {half_id: (source_page_id, half) for half_id, source_page_id, half
                  in load_halves(args.split_extents)}
    to_resample = halves_needing_resample(args.split_extents, args.page_numbers)
    if not to_resample:
        print("Nothing to resample -- continuity check is already clean.")
        return

    print(f"Resampling {len(to_resample)} half(s): {sorted(to_resample)}")
    sem = asyncio.Semaphore(args.max_concurrent)
    fresh = await asyncio.gather(*[
        process_half(client, sem, half_id, *all_halves[half_id], args.images_dir, args.model, system_prompt)
        for half_id in sorted(to_resample)
    ])
    fresh_by_id = {r["half_id"]: r for r in fresh}

    existing = list(csv.DictReader(open(args.page_numbers, encoding="utf-8")))
    merged = [fresh_by_id.get(r["half_id"], r) for r in existing]
    with open(args.page_numbers, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        w.writeheader()
        w.writerows(merged)
    print(f"Updated: {args.page_numbers}")

    remaining = validate_continuity(args.split_extents, args.page_numbers)
    if remaining:
        print(f"{len(remaining)} finding(s) remain after resample:")
        for f in remaining:
            print(f"  [{f['kind']}] {f['page_id']}: {f['detail']}")
    else:
        print("All halves chain cleanly after resample: no gaps, no duplicates, everything read.")


async def main_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)

    system_prompt = (PROMPTS_DIR / "repertoire_splitpagenum_system.txt").read_text(encoding="utf-8")
    halves = load_halves(args.split_extents)
    if args.limit:
        halves = halves[:args.limit]

    sem = asyncio.Semaphore(args.max_concurrent)
    t0 = time.monotonic()
    results = await asyncio.gather(*[
        process_half(client, sem, half_id, source_page_id, half, args.images_dir, args.model, system_prompt)
        for half_id, source_page_id, half in halves
    ])
    elapsed = time.monotonic() - t0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_failed = len(results) - n_ok
    total_tokens = sum(int(r["total_tokens"]) for r in results if r.get("total_tokens"))
    print(f"{len(results)} halves: {n_ok} ok, {n_failed} failed, "
          f"{total_tokens} total tokens, {elapsed:.1f}s wall clock", file=sys.stderr)
    print(f"Written: {args.out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split-extents", required=True, type=Path,
                     help="split_extents.csv from split_spread_pages.py")
    ap.add_argument("--images-dir", type=Path, help="dir holding the {page_id}__top/__bottom.png halves")
    ap.add_argument("--out", type=Path, help="page-number extraction CSV to write")
    ap.add_argument("--page-numbers", type=Path,
                     help="an already-written page-number CSV, for --validate-only")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-concurrent", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                     help="only process the first N halves (smoke test)")
    ap.add_argument("--validate-only", action="store_true",
                     help="skip extraction; just run the continuity check against --page-numbers")
    ap.add_argument("--resample", action="store_true",
                     help="re-call only the halves the continuity check flags in --page-numbers "
                          "(an unreadable side, or both sides of a within-page gap), then re-validate")
    args = ap.parse_args()

    if args.validate_only:
        if not args.page_numbers:
            raise SystemExit("--validate-only requires --page-numbers")
        findings = validate_continuity(args.split_extents, args.page_numbers)
        if not findings:
            print("All halves chain cleanly: no gaps, no duplicates, everything read.")
        else:
            print(f"{len(findings)} continuity finding(s):")
            for f in findings:
                print(f"  [{f['kind']}] {f['page_id']}: {f['detail']}")
        return

    if args.resample:
        if not args.page_numbers or not args.images_dir:
            raise SystemExit("--resample requires --page-numbers and --images-dir")
        asyncio.run(resample_async(args))
        return

    if not args.images_dir or not args.out:
        raise SystemExit("--images-dir and --out are required unless --validate-only")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
