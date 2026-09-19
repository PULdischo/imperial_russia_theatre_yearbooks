"""Small, targeted extraction pass: reads just the printed header line above
each Repertoire page's table (e.g. "16 декабря. 1907 г. 25 декабря."), not
the table itself. Written to close a specific gap (docs/eval/known_issues.md
#69's "event-date field audit" addendum): `flatten_repertoire_page` computes
`date_undate` from only a session's own `month_text`/`year_text`, which the
column-wise extraction pipeline populates on just ~13-21% of rows per season
(vs ~100% for baseline extraction) -- most rows simply never had a month/year
to read in their own cropped column. The page's own header states the exact
date range unambiguously and is cheap to read on its own (a small crop, a
short verbatim string, no table transcription at all) -- reconciling it
against each page's own day-number sequence (a separate step, not this
script) can then backfill `month_text`/`year_text` for the rows missing it,
without re-running or touching the existing column-wise raw JSON.

Crops the top 15% of each rendered page image (generous margin -- the header
sits within the top ~6-10% on every season checked, per
docs/eval/known_issues.md #69) and asks for ONE verbatim string, not
structured fields: keeps this consistent with the project's verbatim-
transcription discipline (parse the string with code afterward, the same
way `date_text` itself is parsed by `pipeline/schemas/dates.py`, rather than
trusting the model to split it into fields itself).

Usage:
    python pipeline/extract_page_headers.py --manifest outputs/gate3_columnwise/manifest.csv \
        --images-dir <rendered images dir> --out outputs/gate3_columnwise/page_header_dates.csv \
        --max-concurrent 8
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import io
import json
import os
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

HEADER_SCHEMA = {
    "type": "object",
    "properties": {
        "header_text": {
            "type": "string",
            "description": "The page's own printed date-range header line, "
                            "verbatim, or empty string if not found.",
        }
    },
    "required": ["header_text"],
}


def crop_header(image_path: Path, top_fraction: float = 0.20) -> str:
    """Returns a base64 data URI of the top `top_fraction` of the page,
    full width -- never writes a temp file to disk."""
    im = Image.open(image_path)
    im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
    w, h = im.size
    crop = im.crop((0, 0, w, int(h * top_fraction)))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{data}"


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
                        {"type": "text", "text": "Transcribe the header line."},
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
                        images_dir: Path, model: str, system_prompt: str) -> dict:
    page_id = row["page_id"]
    log_row = {"page_id": page_id, "status": "", "header_text": "",
               "elapsed_seconds": "", "prompt_tokens": "", "completion_tokens": "",
               "total_tokens": "", "error": ""}

    image_path = images_dir / f"{page_id}.png"
    if not image_path.exists():
        image_path = images_dir / f"{page_id}.jpg"
    if not image_path.exists():
        log_row["status"] = "missing_image"
        log_row["error"] = str(images_dir / f"{page_id}.(png|jpg)")
        return log_row

    async with sem:
        t0 = time.monotonic()
        try:
            image_data_uri = crop_header(image_path)
            raw_text, usage = await call_with_retry(client, model, system_prompt, HEADER_SCHEMA, image_data_uri)
            parsed = json.loads(raw_text)
            log_row.update(status="ok", header_text=parsed.get("header_text", ""),
                            elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage)
        except Exception as e:
            log_row.update(status="failed", elapsed_seconds=f"{time.monotonic() - t0:.1f}", error=str(e))
        return log_row


async def main_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)

    system_prompt = (PROMPTS_DIR / "repertoire_pageheader_system.txt").read_text(encoding="utf-8")
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    if args.limit:
        rows = rows[:args.limit]

    sem = asyncio.Semaphore(args.max_concurrent)
    t0 = time.monotonic()
    results = await asyncio.gather(*[
        process_page(client, sem, row, args.images_dir, args.model, system_prompt)
        for row in rows
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
    print(f"{len(results)} pages: {n_ok} ok, {n_failed} failed, "
          f"{total_tokens} total tokens, {elapsed:.1f}s wall clock", file=sys.stderr)
    print(f"Written: {args.out}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-concurrent", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                     help="only process the first N manifest rows (smoke test)")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
