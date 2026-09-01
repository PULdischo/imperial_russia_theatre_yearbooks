"""Batch driver for the RGIA Fond 497 opis 18 finding aid: runs every page
image N times (at differing upscale factors) and saves ONLY the raw JSON
responses, one file per page-pass.

Multiple passes are the point, not redundancy. At ~127 dpi the model's own
`uncertain` flag is useless (it fired 0 times in 57 pilot entries) -- but
independent passes disagree exactly where the reading is shaky, so
disagreement across passes is the confidence signal. Consolidation into a
single table, with that signal attached, is rgia_opis_consolidate.py --
re-consolidating is free, re-calling the API is not.

Usage:
    python pipeline/rgia_opis_batch.py --out-dir outputs/rgia_full --passes 3 \
        --max-concurrent 6
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import os
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

sys.path.insert(0, str(Path(__file__).parent))
from rgia_opis_extract import SYSTEM_PROMPT, OpisPage, load_image

BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"
RETRYABLE = (APIError, APITimeoutError, RateLimitError, ConnectionError, TimeoutError)
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 5
PASS_SCALES = [1.0, 2.0, 1.5]        # pass 1, 2, 3 -- input diversity on purpose


async def call_with_retry(client, model, image_uri, label):
    full_system = (SYSTEM_PROMPT + "\n\nReturn JSON matching exactly this JSON "
                   "Schema (the object, not the schema itself):\n"
                   + json.dumps(OpisPage.model_json_schema()))
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            comp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Transcribe and translate this opening."},
                        {"type": "image_url", "image_url": {"url": image_uri}},
                    ]},
                ],
                response_format={"type": "json_object"},
            )
            u = comp.usage
            return comp.choices[0].message.content, {
                "prompt_tokens": getattr(u, "prompt_tokens", None),
                "completion_tokens": getattr(u, "completion_tokens", None),
            }
        except RETRYABLE as e:
            last = e
            if attempt < MAX_ATTEMPTS:
                wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                print(f"  {label}: attempt {attempt} failed ({e!r}), retry in {wait}s",
                      file=sys.stderr)
                await asyncio.sleep(wait)
    raise last


async def one(client, sem, model, img_path: Path, pass_no: int, out_dir: Path, stats):
    dest = out_dir / f"{img_path.stem}.pass{pass_no}.raw.json"
    if dest.exists() and dest.stat().st_size > 0:
        stats["skipped"] += 1
        return
    scale = PASS_SCALES[(pass_no - 1) % len(PASS_SCALES)]
    label = f"{img_path.stem} p{pass_no}"
    async with sem:
        uri = await asyncio.to_thread(load_image, img_path, scale)
        try:
            raw, usage = await call_with_retry(client, model, uri, label)
        except Exception as e:
            print(f"  {label}: FAILED {e!r}", file=sys.stderr)
            stats["failed"] += 1
            return
    dest.write_text(raw, encoding="utf-8")
    stats["done"] += 1
    stats["prompt_tokens"] += usage.get("prompt_tokens") or 0
    stats["completion_tokens"] += usage.get("completion_tokens") or 0


async def main_async(args):
    load_dotenv()
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=key, base_url=BASE_URL)

    images = sorted(args.images_dir.glob("img*.jpg"))
    if args.pages:
        want = {int(x) for x in args.pages.split(",")}
        images = [p for p in images if int(p.stem[3:]) in want]
    out_dir = args.out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(args.max_concurrent)
    stats = {"done": 0, "skipped": 0, "failed": 0, "prompt_tokens": 0, "completion_tokens": 0}
    tasks = [one(client, sem, args.model, p, n, out_dir, stats)
             for p in images for n in range(1, args.passes + 1)]
    total = len(tasks)
    print(f"{len(images)} images x {args.passes} passes = {total} calls "
          f"(concurrency {args.max_concurrent})", file=sys.stderr)

    t0 = time.time()
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        await coro
        if i % 20 == 0 or i == total:
            el = time.time() - t0
            rate = i / el if el else 0
            eta = (total - i) / rate if rate else 0
            print(f"  {i}/{total}  done={stats['done']} skipped={stats['skipped']} "
                  f"failed={stats['failed']}  ETA {eta/60:.1f} min", file=sys.stderr)

    print(f"\nfinished in {(time.time()-t0)/60:.1f} min: {stats}", file=sys.stderr)
    if stats["failed"]:
        print("Re-run the same command to retry only the failures.", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", type=Path, default=Path("pdf/RGIA_F497_Op18/images"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/rgia_full"))
    ap.add_argument("--pages", help="comma-separated image numbers (default: all)")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--max-concurrent", type=int, default=6)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
