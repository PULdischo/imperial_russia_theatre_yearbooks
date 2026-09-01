"""Stage 2 of the season-reviews pipeline: call a vision model on every page
in a reviews manifest and save the RAW JSON response, one file per page.

Parsing/validation is a separate step (parse_reviews.py), so re-parsing after
a schema or convention change never re-calls the API -- the same
flatten-boundary discipline as the tabular pipeline (CLAUDE.md).

Idempotent by design (docs/season_reviews.md §13): pages whose .raw.json
already exists are skipped, so adding a newly scanned volume costs only that
volume, and an interrupted run resumes.

Two providers, for the bake-off in docs/season_reviews.md §11:

    --provider dashscope   (default)  qwen3-vl-plus
    --provider anthropic              claude-opus-5

Both paths use the SAME technique -- JSON requested in the prompt, parsed
afterwards -- rather than structured outputs on one and not the other. That
keeps the comparison about the models rather than about API features.

Usage:
    python pipeline/run_reviews.py --manifest outputs/reviews/manifest.csv \
        --images-dir outputs/reviews/images --out-dir outputs/reviews/raw \
        --max-concurrent 6

    # one page, for iterating on the prompt
    python pipeline/run_reviews.py --manifest ... --images-dir ... \
        --out-dir outputs/reviews/smoke --only review_1894-95_SP_ballet_p000

    # the annotation ablation (docs/season_reviews.md §11)
    python pipeline/run_reviews.py ... --prompt review_system_plain.txt \
        --out-dir outputs/reviews/raw_plain
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

sys.path.insert(0, str(Path(__file__).parent))

PROMPTS_DIR = Path(__file__).parent / "prompts"
DASHSCOPE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULTS = {"dashscope": "qwen3-vl-plus", "anthropic": "claude-opus-5"}

USER_INSTRUCTION = (
    "Transcribe this page. Return one JSON object matching the contract in "
    "your instructions. No prose, no markdown fence."
)


def encode_image(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return base64.b64encode(path.read_bytes()).decode("utf-8"), mime


def strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


# --------------------------------------------------------------------------
# providers


class Provider:
    def __init__(self, name: str, model: str, max_tokens: int):
        self.name, self.model, self.max_tokens = name, model, max_tokens
        load_dotenv()
        if name == "dashscope":
            from openai import AsyncOpenAI
            key = os.environ.get("DASHSCOPE_API_KEY")
            if not key:
                raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
            self.client = AsyncOpenAI(api_key=key, base_url=DASHSCOPE_URL)
        elif name == "anthropic":
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise SystemExit(
                    "anthropic SDK not installed -- run: pip install anthropic")
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise SystemExit("ANTHROPIC_API_KEY not set (check .env)")
            self.client = AsyncAnthropic(api_key=key)
        else:
            raise SystemExit(f"unknown provider {name!r}")

    async def call(self, system_prompt: str, b64: str, mime: str) -> tuple[str, dict]:
        if self.name == "dashscope":
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": USER_INSTRUCTION},
                    ]},
                ],
                max_tokens=self.max_tokens,
            )
            u = completion.usage
            usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", "") if u else "",
                "completion_tokens": getattr(u, "completion_tokens", "") if u else "",
                "total_tokens": getattr(u, "total_tokens", "") if u else "",
            }
            return completion.choices[0].message.content, usage

        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": mime, "data": b64}},
                {"type": "text", "text": USER_INSTRUCTION},
            ]}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        usage = {
            "prompt_tokens": msg.usage.input_tokens,
            "completion_tokens": msg.usage.output_tokens,
            "total_tokens": msg.usage.input_tokens + msg.usage.output_tokens,
        }
        return text, usage


async def call_with_retry(provider: Provider, system_prompt: str, b64: str,
                          mime: str, attempts: int = 4):
    for attempt in range(1, attempts + 1):
        try:
            return await provider.call(system_prompt, b64, mime)
        except Exception as e:
            if attempt == attempts:
                raise
            wait = 2 ** attempt
            print(f"    attempt {attempt} failed ({type(e).__name__}: {e}), "
                  f"retrying in {wait}s", file=sys.stderr)
            await asyncio.sleep(wait)


# --------------------------------------------------------------------------


async def process_page(provider: Provider, sem: asyncio.Semaphore, row: dict,
                       images_dir: Path, out_dir: Path, system_prompt: str) -> dict:
    page_id = row["page_id"]
    out_path = out_dir / f"{page_id}.raw.json"
    log = {"page_id": page_id, "model": provider.model, "status": "",
           "elapsed_seconds": "", "prompt_tokens": "", "completion_tokens": "",
           "total_tokens": "", "error": ""}
    if out_path.exists():
        log["status"] = "skipped"
        return log

    image_path = images_dir / Path(row["image_file"]).name
    if not image_path.exists():
        log.update(status="error", error=f"image missing: {image_path}")
        return log

    async with sem:
        t0 = time.monotonic()
        try:
            b64, mime = encode_image(image_path)
            raw_text, usage = await call_with_retry(provider, system_prompt, b64, mime)
            out_path.write_text(strip_fence(raw_text or ""), encoding="utf-8")
            log.update(status="ok",
                       elapsed_seconds=f"{time.monotonic() - t0:.1f}", **usage)
        except Exception as e:
            log.update(status="error", error=f"{type(e).__name__}: {e}",
                       elapsed_seconds=f"{time.monotonic() - t0:.1f}")
        return log


async def main_async(args) -> None:
    system_prompt = (PROMPTS_DIR / args.prompt).read_text(encoding="utf-8")
    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    if args.only:
        wanted = set(args.only)
        rows = [r for r in rows if r["page_id"] in wanted]
        if not rows:
            raise SystemExit(f"no manifest rows matched {sorted(wanted)}")
    if args.limit:
        rows = rows[: args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    provider = Provider(args.provider, args.model or DEFAULTS[args.provider],
                        args.max_tokens)
    sem = asyncio.Semaphore(args.max_concurrent)

    print(f"{len(rows)} pages | provider={args.provider} model={provider.model} "
          f"| prompt={args.prompt}")

    tasks = [process_page(provider, sem, r, args.images_dir, args.out_dir,
                          system_prompt) for r in rows]
    logs = []
    for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
        log = await coro
        logs.append(log)
        if log["status"] == "error":
            print(f"[{i}/{len(rows)}] ERROR {log['page_id']}: {log['error']}")
        elif i % 25 == 0 or i == len(rows):
            print(f"[{i}/{len(rows)}] ...")

    # Appended, never overwritten -- the tabular pipeline lost the token
    # history of a full run by overwriting this on each retry invocation.
    usage_path = args.out_dir.parent / "usage_log_reviews.csv"
    write_header = not usage_path.exists()
    with open(usage_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(logs[0].keys()))
        if write_header:
            w.writeheader()
        w.writerows(logs)

    ok = sum(1 for l in logs if l["status"] == "ok")
    skipped = sum(1 for l in logs if l["status"] == "skipped")
    errs = [l for l in logs if l["status"] == "error"]
    tot = sum(int(l["total_tokens"]) for l in logs
              if str(l["total_tokens"]).isdigit())
    print(f"\nok {ok} | skipped {skipped} | errors {len(errs)} | tokens {tot:,}")
    print(f"usage log -> {usage_path}")
    if errs:
        print("re-run the same command to retry only the failures.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--images-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--provider", choices=["dashscope", "anthropic"],
                    default="dashscope")
    ap.add_argument("--model", default=None)
    ap.add_argument("--prompt", default="review_system.txt")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--max-concurrent", type=int, default=6)
    ap.add_argument("--only", nargs="*", default=None, help="page_id(s) only")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
