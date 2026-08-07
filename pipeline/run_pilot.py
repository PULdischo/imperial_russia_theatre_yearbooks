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
from schemas import RosterPage, RepertoirePage

PROMPTS_DIR = Path(__file__).parent / "prompts"
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"
ROSTER_KINDS = {"Administrators", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}

RETRYABLE = (APIError, APITimeoutError, RateLimitError, ConnectionError, TimeoutError)
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 5


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


async def main_async(args):
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))

    roster_prompt = (PROMPTS_DIR / "roster_system.txt").read_text(encoding="utf-8")
    repertoire_prompt = (PROMPTS_DIR / "repertoire_system.txt").read_text(encoding="utf-8")
    roster_schema = RosterPage.model_json_schema()
    repertoire_schema = RepertoirePage.model_json_schema()

    sem = asyncio.Semaphore(args.max_concurrent)
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
    usage_path = args.out_dir / "usage_log.csv"
    fieldnames = list(log_rows[0].keys()) if log_rows else \
        ["page_id", "status", "attempts", "elapsed_seconds",
         "prompt_tokens", "completion_tokens", "total_tokens", "error"]
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
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
