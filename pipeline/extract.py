"""Call a Qwen-VL model via DashScope's OpenAI-compatible endpoint on one page
image, parse the JSON response against our pydantic schema, and flatten it
into rows matching docs/schema.md's flat tables.

Usage (single page, smoke test):
    python pipeline/extract.py --image path/to/page.png --kind roster \
        --page-id administration_1890-91_p000 --entity-type Administration \
        --out-dir outputs/smoke

    python pipeline/extract.py --image path/to/page.png --kind repertoire \
        --page-id repertoire_1890-91_p000 --season 1890-91 --city SP \
        --out-dir outputs/smoke
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from schemas import (
    RosterPage, RepertoirePage, flatten_roster_page, flatten_repertoire_page,
)

PROMPTS_DIR = Path(__file__).parent / "prompts"
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-vl-plus"


def load_client() -> OpenAI:
    load_dotenv()
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY not set (check .env)")
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def encode_image(image_path: Path) -> str:
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    ext = image_path.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else f"image/{ext}"
    return f"data:{mime};base64,{data}"


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def call_model(client: OpenAI, model: str, system_prompt: str, schema: dict,
                image_data_uri: str) -> dict:
    full_system = (
        f"{system_prompt}\n\nReturn JSON matching exactly this JSON Schema "
        f"(the top-level object, not the schema itself):\n{json.dumps(schema)}"
    )
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this page."},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            },
        ],
        response_format={"type": "json_object"},
    )
    raw_text = completion.choices[0].message.content
    cleaned = _strip_code_fence(raw_text)
    return {"raw_text": raw_text, "parsed": json.loads(cleaned)}


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, type=Path)
    ap.add_argument("--kind", required=True, choices=["roster", "repertoire"])
    ap.add_argument("--page-id", required=True)
    ap.add_argument("--entity-type", default="")
    ap.add_argument("--season", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/smoke"))
    args = ap.parse_args()

    client = load_client()
    image_data_uri = encode_image(args.image)

    if args.kind == "roster":
        system_prompt = (PROMPTS_DIR / "roster_system.txt").read_text(encoding="utf-8")
        schema = RosterPage.model_json_schema()
    else:
        system_prompt = (PROMPTS_DIR / "repertoire_system.txt").read_text(encoding="utf-8")
        schema = RepertoirePage.model_json_schema()

    print(f"Calling {args.model} on {args.image.name} ...", file=sys.stderr)
    result = call_model(client, args.model, system_prompt, schema, image_data_uri)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.out_dir / f"{args.page_id}.raw.json"
    raw_path.write_text(result["raw_text"], encoding="utf-8")
    print(f"Raw response saved: {raw_path}", file=sys.stderr)

    if args.kind == "roster":
        page = RosterPage.model_validate(result["parsed"])
        tables = flatten_roster_page(args.page_id, args.entity_type, page)
    else:
        page = RepertoirePage.model_validate(result["parsed"])
        tables = flatten_repertoire_page(args.page_id, args.season, args.city, page)

    for table_name, rows in tables.items():
        out_path = args.out_dir / f"{args.page_id}.{table_name}.csv"
        write_csv(rows, out_path)
        print(f"{table_name}: {len(rows)} rows -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
