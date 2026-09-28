"""Translate season-review blocks into English for reading.

Output is a sidecar CSV keyed by `block_id`, which `build_bilingual.py` joins
to the Russian. Translation is kept separate from both extraction and layout
so any one of the three can be redone without the others.

**These translations are for reading and skimming only.** RG quotes from the
scan, never from the transcription or from this. Accordingly the prompt asks
for a plain, faithful rendering rather than a literary one, and asks the
model to leave proper names transliterated rather than Anglicised, because
the names are what she links to database entities.

The run is resumable: block_ids already present in the output CSV are
skipped, so an interrupted run continues where it stopped, and translating
newly-extracted pages later costs only those pages.

Usage:
    uv run python pipeline/translate_reviews.py \
        --parsed-dir outputs/reviews/pilot_parsed \
        --out outputs/reviews/translations.csv \
        [--model qwen-plus] [--max-concurrent 8] [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

csv.field_size_limit(10_000_000)

DASHSCOPE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
PLATE = {"figure"}

SYSTEM = """You translate late-19th-century Russian theatre prose into English.

The source is the Ежегодникъ Императорскихъ театровъ (Yearbook of the
Imperial Theatres), 1890s-1900s, printed in pre-1918 orthography: it uses ъ,
ѣ, і and ѳ, which modern Russian does not. Read those as the old spellings of
ordinary words. The text describes ballet and opera productions, casts, and
the action of ballets scene by scene.

Rules:
- Translate plainly and faithfully. This is for a researcher skimming the
  content, not a literary edition. Do not embellish, summarise or omit.
- Leave proper names TRANSLITERATED, not Anglicised or translated:
  Кшесинская -> Kshesinskaya, Гердтъ -> Gerdt, Преображенская ->
  Preobrazhenskaya. Keep the ordinal that follows a surname: "Петипа 1-я" ->
  "Petipa 1st", "Ивановъ 2-й" -> "Ivanov 2nd".
- г. = Mr (gospodin), г-жа = Mme, гг. = MM., г-жи = Mmes, восп-ца =
  student (of the Theatre School). Render them, don't drop them.
- Keep French and Italian titles and dance names in their original form
  (Pas de deux, Groupes et scène); do not translate them into English.
- Ballet and opera titles: give the usual English title where one plainly
  exists («Спящая красавица» -> "The Sleeping Beauty"), otherwise
  transliterate.
- If a passage begins or ends mid-sentence, translate it as it stands. Do not
  invent the missing part.
- Return ONLY the English translation. No notes, no preamble, no quotation
  marks around the whole thing."""


def block_text(b: dict) -> str:
    return (b["caption_text"] if b["block_type"] in PLATE else b["text"]) or ""


def reflow(t: str) -> str:
    t = re.sub(r"([^\s-])-\n\s*", r"\1", t)
    return re.sub(r"\s*\n\s*", " ", t).strip()


async def translate_one(client, model, sem, block_id, ru, log):
    async with sem:
        for attempt in range(4):
            try:
                r = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": ru}],
                    temperature=0.0,
                    max_tokens=4000,
                )
                u = r.usage
                log["in"] += getattr(u, "prompt_tokens", 0) or 0
                log["out"] += getattr(u, "completion_tokens", 0) or 0
                return block_id, (r.choices[0].message.content or "").strip(), ""
            except Exception as e:
                if attempt == 3:
                    return block_id, "", f"{type(e).__name__}: {e}"
                await asyncio.sleep(2 ** attempt)


async def main_async(a):
    load_dotenv()
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key, base_url=DASHSCOPE_URL)

    with open(a.parsed_dir / "review_block.csv", encoding="utf-8") as f:
        blocks = [b for b in csv.DictReader(f) if block_text(b).strip()]

    done: dict[str, str] = {}
    if a.out.exists():
        with open(a.out, encoding="utf-8") as f:
            done = {r["block_id"]: r["english"] for r in csv.DictReader(f)}
    todo = [b for b in blocks if b["block_id"] not in done]
    if a.limit:
        todo = todo[: a.limit]

    print(f"{len(blocks)} blocks total | {len(done)} already translated | "
          f"{len(todo)} to do | model={a.model}")
    if not todo:
        return

    log = {"in": 0, "out": 0}
    sem = asyncio.Semaphore(a.max_concurrent)
    t0 = time.monotonic()
    tasks = [translate_one(client, a.model, sem, b["block_id"],
                           reflow(block_text(b)), log) for b in todo]

    results, errors, n = dict(done), [], 0
    marks = {int(len(tasks) * f) for f in (0.25, 0.5, 0.75)}
    for fut in asyncio.as_completed(tasks):
        bid, en, err = await fut
        n += 1
        if err:
            errors.append((bid, err))
        else:
            results[bid] = en
        if n in marks:
            print(f"  {n}/{len(tasks)} ({100*n//len(tasks)}%) "
                  f"| {time.monotonic()-t0:.0f}s | {len(errors)} errors")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["block_id", "english"])
        for b in blocks:
            if b["block_id"] in results:
                w.writerow([b["block_id"], results[b["block_id"]]])

    print(f"\n{len(results)} translations -> {a.out}")
    print(f"{log['in']:,} input + {log['out']:,} output tokens "
          f"({log['in']+log['out']:,} total) in {time.monotonic()-t0:.0f}s")
    if errors:
        print(f"{len(errors)} failed (re-run to retry them):")
        for bid, e in errors[:5]:
            print(f"  {bid}: {e[:90]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="qwen-plus")
    ap.add_argument("--max-concurrent", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None,
                    help="translate only the first N untranslated blocks")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
