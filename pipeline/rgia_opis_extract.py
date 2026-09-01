"""Transcribe + translate one page-image of RGIA's Fond 497, opis 18 finding
aid (the опись), and flag which дела fall in a research date range.

Each image is a two-page opening of a ruled ledger whose columns are:
порядковый № | делопроизводственный № | Название дел | крайние даты |
количество листов | отметки. Unlike the yearbooks, this is a SOVIET-ERA
finding aid — modern orthography. Transcribe what is on the card; do not
"restore" pre-1918 spelling.

Usage:
    python pipeline/rgia_opis_extract.py --image pdf/RGIA_F497_Op18/images/img047.jpg \
        --out-dir outputs/rgia_pilot
    python pipeline/rgia_opis_extract.py --images-dir pdf/RGIA_F497_Op18/images \
        --pages 38,47,107 --out-dir outputs/rgia_pilot --scale 2
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
from extract import load_client, _strip_code_fence, DEFAULT_MODEL

RESEARCH_START, RESEARCH_END = 1890, 1916


class OpisEntry(BaseModel):
    side: str = Field(description="'left' or 'right' page of the opening")
    poryadkovy_nomer: Optional[str] = Field(
        None, description="Порядковый № (running file number), as written")
    superseded_nomer: Optional[str] = Field(
        None, description="A second/struck-through number written with it, if any")
    delo_nomer: Optional[str] = Field(None, description="Делопроизводственный № if present")
    title_ru: str = Field(description="Название дела, verbatim, modern orthography as written")
    title_en: str = Field(description="Faithful English translation of title_ru")
    dates_raw: Optional[str] = Field(None, description="Крайние даты column, verbatim")
    year_start: Optional[int] = Field(None, description="Earliest year in dates_raw")
    year_end: Optional[int] = Field(None, description="Latest year in dates_raw; = year_start if one year")
    listov: Optional[str] = Field(None, description="Количество листов column")
    otmetki: Optional[str] = Field(None, description="Отметки column")
    uncertain: bool = Field(False, description="True if handwriting could not be read confidently")


class OpisPage(BaseModel):
    foliation_left: Optional[str] = Field(None, description="Stamped number on the left page, if visible")
    foliation_right: Optional[str] = Field(None, description="Stamped листъ number top-right of right page")
    entries: list[OpisEntry] = Field(default_factory=list)


SYSTEM_PROMPT = """You are transcribing a page-image from a Russian archival
finding aid (опись) held at RGIA: Фонд 497 (Дирекция императорских театров),
опись 18. The image is a photograph of a two-page opening of a ruled ledger.
Both the left and the right page carry an independent table. Read BOTH.

Each table has these columns, left to right:
  Порядковый №  |  Делопроизводственный №  |  Название дел и других единиц
  хранения  |  Даты начала и окончания (крайние даты)  |  Количество листов
  |  Отметки

Rules:
- The entries are handwritten Russian cursive. Transcribe `title_ru` EXACTLY as
  written, preserving the writer's spelling, abbreviations (имп., С.П.Б., etc.)
  and punctuation. This is a Soviet-era finding aid in MODERN orthography — do
  not add ъ/ѣ/і, and do not modernize either. Copy what is there.
- Titles often run over several ruled lines; join them into ONE entry. A new
  entry starts only where a new number appears in the Порядковый № column.
- Some entries carry two numbers stacked, one of them struck through (a
  renumbering). Put the current/upper one in `poryadkovy_nomer` and the
  struck-through one in `superseded_nomer`.
- `title_en` is a faithful, plain English translation of `title_ru`. Translate
  proper names as they are (П.И. Чайковский -> P.I. Tchaikovsky). Keep theatre
  and institution names recognisable.
- `dates_raw` is the крайние даты column verbatim (e.g. "1892г.", "1880-1905",
  "15 февр.1882 - 25 июля 1883"). Then set `year_start` / `year_end` to the
  four-digit years. If only one year is given, set both to it. If the column is
  blank, leave all three null — do NOT infer a date from the title.
- Set `uncertain` true for any entry you could not read confidently. The scan is
  low resolution (~127 dpi); an honest `uncertain` flag is far more useful than
  a confident guess.
- Report the stamped page numbers you can see in `foliation_left` /
  `foliation_right`.
- Transcribe every entry visible on both pages, in reading order: all of the
  left page first, then all of the right page.
"""


def encode_pil(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def load_image(path: Path, scale: float) -> str:
    im = Image.open(path).convert("RGB")
    if scale and scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return encode_pil(im)


def in_range(e: dict, lo: int, hi: int) -> str:
    ys, ye = e.get("year_start"), e.get("year_end")
    if ys is None and ye is None:
        return "unknown"
    ys = ys if ys is not None else ye
    ye = ye if ye is not None else ys
    return "yes" if ys <= hi and ye >= lo else "no"


def extract_page(client, model: str, image_path: Path, scale: float) -> dict:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nReturn JSON matching "
             "exactly this JSON Schema (the object, not the schema):\n"
             + json.dumps(OpisPage.model_json_schema())},
            {"role": "user", "content": [
                {"type": "text", "text": "Transcribe and translate this opening."},
                {"type": "image_url", "image_url": {"url": load_image(image_path, scale)}},
            ]},
        ],
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content
    return {"raw_text": raw, "parsed": json.loads(_strip_code_fence(raw))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path)
    ap.add_argument("--images-dir", type=Path, default=Path("pdf/RGIA_F497_Op18/images"))
    ap.add_argument("--pages", help="comma-separated image numbers, e.g. 38,47,107")
    ap.add_argument("--scale", type=float, default=1.0, help="upscale factor before sending")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/rgia_pilot"))
    ap.add_argument("--range", default=f"{RESEARCH_START}-{RESEARCH_END}")
    args = ap.parse_args()

    lo, hi = (int(x) for x in args.range.split("-"))
    if args.image:
        targets = [args.image]
    elif args.pages:
        targets = [args.images_dir / f"img{int(n):03d}.jpg" for n in args.pages.split(",")]
    else:
        targets = sorted(args.images_dir.glob("img*.jpg"))

    client = load_client()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []

    for path in targets:
        img_no = int(re.search(r"(\d+)", path.stem).group(1))
        print(f"[{path.name}] calling {args.model} (scale={args.scale}) ...", file=sys.stderr)
        try:
            res = extract_page(client, args.model, path, args.scale)
        except Exception as exc:
            print(f"[{path.name}] FAILED: {exc}", file=sys.stderr)
            continue
        (args.out_dir / f"{path.stem}.raw.json").write_text(res["raw_text"], encoding="utf-8")
        page = OpisPage.model_validate(res["parsed"])
        for e in page.entries:
            row = e.model_dump()
            row["image"] = img_no
            row["list_expected"] = img_no - 2          # листъ = image - 2
            row["foliation_read"] = page.foliation_right
            row["in_research_range"] = in_range(row, lo, hi)
            all_rows.append(row)
        n_rel = sum(1 for r in all_rows if r["image"] == img_no and r["in_research_range"] == "yes")
        print(f"[{path.name}] {len(page.entries)} entries, {n_rel} in {lo}-{hi}", file=sys.stderr)

    if all_rows:
        cols = ["image", "list_expected", "foliation_read", "side", "poryadkovy_nomer",
                "superseded_nomer", "delo_nomer", "title_ru", "title_en", "dates_raw",
                "year_start", "year_end", "listov", "otmetki", "uncertain",
                "in_research_range"]
        out = args.out_dir / "opis_entries.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in all_rows:
                w.writerow({c: r.get(c, "") for c in cols})
        print(f"\n{len(all_rows)} entries -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
