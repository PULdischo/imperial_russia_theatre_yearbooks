"""Date-only extraction from the scanned оп. 18 опись images.

RGIA's published catalogue (rgia_opis_scrape.py) is authoritative for дело
numbers and titles, but leaves 720 of 1142 дела with no date at all. Those
dates exist only in the scan's handwritten «крайние даты» column. So this
asks the model for that column and NOTHING else -- no titles, no
translation. Two reasons: the крайние даты column was by far the model's
most reliable field in the pilot (66/66 cross-pass agreement, ~85-90%
correct) while its prose transcription was ~50% wrong; and a short reply is
cheaper and leaves less room to drift.

The 422 дела that DO have catalogue dates are held back as ground truth --
rgia_dates_merge.py scores the model against them before trusting the 720.

Usage:
    python pipeline/rgia_opis_dates.py --out-dir outputs/rgia_dates --passes 2
"""
from __future__ import annotations

import argparse, asyncio, json, os, sys, time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
from rgia_opis_extract import load_image

BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"
RETRYABLE = (APIError, APITimeoutError, RateLimitError, ConnectionError, TimeoutError)
MAX_ATTEMPTS, BACKOFF = 4, 5
PASS_SCALES = [1.0, 1.5, 2.0]


class DateEntry(BaseModel):
    poryadkovy_nomer: Optional[str] = Field(None, description="Порядковый № (leftmost column), as written")
    superseded_nomer: Optional[str] = Field(None, description="The struck-through second number, if one is written with it")
    dates_raw: Optional[str] = Field(None, description="The «крайние даты» cell, verbatim; null if the cell is blank")
    year_start: Optional[int] = Field(None, description="Earliest 4-digit year in that cell")
    year_end: Optional[int] = Field(None, description="Latest 4-digit year; equal to year_start if only one")


class DatePage(BaseModel):
    foliation_right: Optional[str] = Field(None, description="Stamped number, top-right of the right-hand page")
    entries: list[DateEntry] = Field(default_factory=list)


SYSTEM = """You are reading a two-page opening of a Russian archival finding
aid (опись): RGIA, Фонд 497, опись 18. Both the left and right pages carry a
ruled table. Read BOTH.

Your ONLY job is to pair up two columns:
  * «Порядковый №» -- the running file number, leftmost column
  * «Даты начала и окончания (крайние даты)» -- the narrow dates column on
    the RIGHT of the wide «Название дел» column

Do NOT transcribe the titles. Do not translate anything. Report only numbers
and dates.

Rules:
- One entry per Порядковый №, in reading order: the whole left page, then the
  whole right page.
- Titles wrap over several ruled lines; the date belongs to the entry whose
  number is on the FIRST line of that block. Do not shift a date onto a
  neighbouring entry.
- Where an entry has two numbers stacked and one struck through (a
  renumbering), put the current/upper one in `poryadkovy_nomer` and the
  struck-through one in `superseded_nomer`.
- `dates_raw` is verbatim: "1892г.", "1880-1905", "15 февр.1882 - 25 июля
  1883", "декабрь 1884 г. - сентябрь 1886 г.".
- If the dates cell for an entry is EMPTY, set dates_raw, year_start and
  year_end all to null. Never infer a year. A blank is a real, useful answer.
- Then set year_start / year_end from the four-digit years actually written.
  A single year means both are that year.
- An entry whose number is visible but whose date cell you cannot read should
  still be reported, with null dates.
"""


async def call(client, model, uri, label):
    full = (SYSTEM + "\n\nReturn JSON matching exactly this JSON Schema (the "
            "object, not the schema itself):\n" + json.dumps(DatePage.model_json_schema()))
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            c = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": full},
                          {"role": "user", "content": [
                              {"type": "text", "text": "Report the number and dates columns."},
                              {"type": "image_url", "image_url": {"url": uri}}]}],
                response_format={"type": "json_object"})
            u = c.usage
            return c.choices[0].message.content, (getattr(u, "prompt_tokens", 0) or 0,
                                                  getattr(u, "completion_tokens", 0) or 0)
        except RETRYABLE as e:
            last = e
            if attempt < MAX_ATTEMPTS:
                w = BACKOFF * 2 ** (attempt - 1)
                print(f"  {label}: attempt {attempt} failed, retry {w}s", file=sys.stderr)
                await asyncio.sleep(w)
    raise last


async def one(client, sem, model, img: Path, pno: int, out: Path, st):
    dest = out / f"{img.stem}.pass{pno}.dates.json"
    if dest.exists() and dest.stat().st_size > 0:
        st["skip"] += 1; return
    async with sem:
        uri = await asyncio.to_thread(load_image, img, PASS_SCALES[(pno - 1) % len(PASS_SCALES)])
        try:
            raw, (pt, ct) = await call(client, model, uri, f"{img.stem} p{pno}")
        except Exception as e:
            print(f"  {img.stem} p{pno}: FAILED {e!r}", file=sys.stderr); st["fail"] += 1; return
    dest.write_text(raw, encoding="utf-8")
    st["done"] += 1; st["pt"] += pt; st["ct"] += ct


async def run(args):
    load_dotenv()
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key: raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    client = AsyncOpenAI(api_key=key, base_url=BASE_URL)
    imgs = sorted(args.images_dir.glob("img*.jpg"))
    if args.pages:
        want = {int(x) for x in args.pages.split(",")}
        imgs = [p for p in imgs if int(p.stem[3:]) in want]
    out = args.out_dir / "raw_dates"; out.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(args.max_concurrent)
    st = {"done": 0, "skip": 0, "fail": 0, "pt": 0, "ct": 0}
    tasks = [one(client, sem, args.model, p, n, out, st)
             for p in imgs for n in range(1, args.passes + 1)]
    total = len(tasks); t0 = time.time()
    print(f"{len(imgs)} images x {args.passes} passes = {total} calls", file=sys.stderr)
    for i, c in enumerate(asyncio.as_completed(tasks), 1):
        await c
        if i % 25 == 0 or i == total:
            el = time.time() - t0; eta = (total - i) / (i / el) if el and i else 0
            print(f"  {i}/{total} done={st['done']} skip={st['skip']} fail={st['fail']} "
                  f"ETA {eta/60:.1f}m", file=sys.stderr)
    print(f"\n{(time.time()-t0)/60:.1f} min; {st}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", type=Path, default=Path("pdf/RGIA_F497_Op18/images"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/rgia_dates"))
    ap.add_argument("--pages")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--max-concurrent", type=int, default=6)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
