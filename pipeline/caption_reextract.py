#!/usr/bin/env python3
"""Re-read figure captions from a CROPPED, upscaled band of the scan.

Why crop rather than re-prompt
------------------------------
`run_reviews.py` sends the whole page and does no client-side resizing, but
the measured prompt cost is ~5,170 tokens per page, so the service is
downscaling it to fit the vision budget. At that budget the caption face --
a small italic, roughly a third the size of the body -- falls below
legibility, which is why captions carry impossible honorific forms at 23.1%
against 0.2% in paragraphs (docs/eval/review_caption_quality.md). Cropping
the caption band buys back about 10x the effective resolution for the same
tokens. The fix is resolution, not wording.

Views
-----
Temperature is 0, so three identical crops would return three identical
answers. The views therefore differ in the CROP (band height and upscale),
which is real diversity and the same trick as the bands2/bands4 passes.

Nothing here writes to the corpus. It emits candidate readings; the gate in
`apply_caption_reextract.py` decides what is allowed to replace what.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from platefind import plates, caption_band          # noqa: E402
from run_reviews import Provider, call_with_retry, strip_fence   # noqa: E402

csv.field_size_limit(10 ** 9)

SYSTEM = """You are transcribing ONE figure caption from a page of the
Ежегодникъ Императорскихъ театровъ (1890s-1910s), printed in pre-reform
Russian orthography. The image is a tight crop of the caption, enlarged.

Transcribe it EXACTLY as printed, diplomatically:
- Keep pre-reform letters: ъ ѣ і ѳ ѵ. Do not modernise.
- Keep the printed line breaks as \\n.
- Keep « » quotes, the abbreviations бал. / оп. / муз., and ordinals
  like 2-я, 3-й exactly as set.
- The honorific before a performer's name is always one of: г. (one man),
  гг. (several men), г-жа (one woman), г-жи (several women), г-нъ, в-ца,
  восп. It is NEVER a digit. If a mark looks like "1-жа" it is "г-жа".
- Do NOT correct the printing. If a name is spelled oddly, transcribe the
  odd spelling: this source genuinely spells the same name several ways.
- If the crop shows no caption text, return an empty string.

Return one JSON object and nothing else:
{"caption": "...", "legible": true|false}"""

VIEWS = [
    {"name": "tight",  "height": 170, "scale": 4, "left": 30,  "right": 420},
    {"name": "wide",   "height": 220, "scale": 3, "left": 90,  "right": 620},
    {"name": "deep",   "height": 300, "scale": 3, "left": 50,  "right": 500},
]


def crop_b64(im: Image.Image, box, scale: int) -> tuple[str, str]:
    c = im.crop(box)
    if scale != 1:
        c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
    buf = io.BytesIO()
    c.convert("L").save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


async def read_one(prov, sem, im, box, scale, meta, out, usage):
    b64, mime = crop_b64(im, box, scale)
    async with sem:
        try:
            text, u = await call_with_retry(prov, SYSTEM, b64, mime)
        except Exception as e:
            out.append({**meta, "caption": "", "legible": False, "error": str(e)})
            return
    usage.append(u)
    try:
        obj = json.loads(strip_fence(text))
    except Exception:
        obj = {"caption": strip_fence(text), "legible": True}
    out.append({**meta, "caption": (obj.get("caption") or "").strip(),
                "legible": bool(obj.get("legible", True)), "error": ""})


async def main_async(a):
    pages = [p.strip() for p in Path(a.pages).read_text().split() if p.strip()]
    prov = Provider("dashscope", a.model, max_tokens=800, temperature=0.0)
    sem = asyncio.Semaphore(a.max_concurrent)
    rows, usage, tasks = [], [], []
    for pid in pages:
        path = Path(a.images_dir) / f"{pid}.jpg"
        if not path.exists():
            print(f"  !! missing image {path}", file=sys.stderr)
            continue
        im, P = plates(str(path))
        if not P:
            # No plate located: fall back to the whole page, which is exactly
            # what the original pass saw -- no worse, just not better.
            P = [(0, im.height, 0, im.width)]
            boxes = [(0, 0, im.width, im.height)]
            kinds = ["wholepage"]
        else:
            boxes, kinds = None, None
        for i, plate in enumerate(P):
            for v in VIEWS:
                if boxes is not None:
                    box, kind, scale = boxes[0], kinds[0], 1
                else:
                    box = caption_band(im, plate, height=v["height"],
                                       left=v["left"], right=v["right"])
                    kind, scale = v["name"], v["scale"]
                meta = {"page_id": pid, "plate_index": i, "view": kind}
                tasks.append(read_one(prov, sem, im, box, scale, meta, rows, usage))
                if boxes is not None:
                    break
    print(f"{len(tasks)} call(s) queued")
    await asyncio.gather(*tasks)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id", "plate_index", "view",
                                          "caption", "legible", "error"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["page_id"], r["plate_index"], r["view"])))
    tin = sum(int(u.get("prompt_tokens") or 0) for u in usage)
    tout = sum(int(u.get("completion_tokens") or 0) for u in usage)
    cost = (tin / 1e6 * 1.468 + tout / 1e6 * 11.743) / 7.1
    print(f"-> {out}   {len(rows)} reading(s)")
    print(f"   tokens in {tin:,} / out {tout:,}   ~${cost:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="file of page_ids, one per line")
    ap.add_argument("--images-dir", default="outputs/reviews/images")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="qwen3-vl-plus")
    ap.add_argument("--max-concurrent", type=int, default=6)
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
