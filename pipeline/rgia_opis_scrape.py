"""Pull RGIA's OWN catalogue of Ф. 497 оп. 18 -- all 1142 дела with authoritative
titles and крайние даты -- straight from fgurgia.ru's AJAX tree endpoint.

This supersedes VLM transcription of the scanned опись: the archive has already
published the finding aid as clean text, with full-precision dates ("23 августа
1881 г. - 14 апреля 1894 г.") that the handwritten крайние даты column only
gives as years. Use the page images for verification, not for reading.

The endpoint needs no auth or cookies. `parentId` is the опись object id
(оп. 18 = 2845981; описи 1..19 run 2845947 + 2*(n-1)); `objectType` is
"<objectId>-1050"; the leading path number is a context id that is NOT
session-bound in practice.

Usage:
    python pipeline/rgia_opis_scrape.py --out outputs/rgia_catalogue/opis18_dela.csv
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = ("https://fgurgia.ru/ajax/tree/188295?page={page}&nPage=1&id=0"
        "&parentId={parent}&objectType={parent}-1050&showPageList=true&completeWorkId=-1")
RESEARCH_START, RESEARCH_END = 1890, 1916


def fetch(page: int, parent: int) -> list:
    req = urllib.request.Request(
        BASE.format(page=page, parent=parent),
        headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_node(node: dict) -> dict | None:
    if not node.get("id"):
        return None                      # the pager pseudo-node
    pairs = re.findall(r'dataLabel">(.*?)</div><div class="dataWrap">(.*?)</div>',
                       node["text"], re.S)
    rec = {html.unescape(k).strip(): html.unescape(re.sub("<[^>]+>", "", v)).strip()
           for k, v in pairs}
    shifr = rec.get("Шифр", "")
    m = re.search(r"Д\.\s*(\d+)", shifr)
    dates = rec.get("Крайние даты", "")
    years = [int(y) for y in re.findall(r"\b(1[6-9]\d\d)\b", dates)]
    return {
        "object_id": node["id"],
        "shifr": shifr,
        "delo_no": int(m.group(1)) if m else None,
        "title_ru": rec.get("Заголовок", ""),
        "dates_raw": dates,
        "year_start": min(years) if years else None,
        "year_end": max(years) if years else None,
        "url": f"https://fgurgia.ru/object/{node['id']}",
    }


def in_range(r: dict, lo: int, hi: int) -> str:
    ys, ye = r["year_start"], r["year_end"]
    if ys is None and ye is None:
        return "unknown"
    ys, ye = ys or ye, ye or ys
    return "yes" if ys <= hi and ye >= lo else "no"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", type=int, default=2845981, help="опись object id")
    ap.add_argument("--pages", type=int, default=0, help="0 = follow the pager")
    ap.add_argument("--range", default=f"{RESEARCH_START}-{RESEARCH_END}")
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--out", type=Path, default=Path("outputs/rgia_catalogue/opis18_dela.csv"))
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.range.split("-"))

    first = fetch(1, args.parent)
    total_pages = args.pages
    if not total_pages:
        # pager node text is "cur,first,prev,next,last"
        bits = (first[0].get("text") or "").split(",")
        total_pages = int(bits[-1]) if bits and bits[-1].strip().isdigit() else 1
    print(f"опись object {args.parent}: {total_pages} pages", file=sys.stderr)

    rows, seen = [], set()
    for page in range(1, total_pages + 1):
        nodes = first if page == 1 else fetch(page, args.parent)
        got = 0
        for n in nodes:
            r = parse_node(n)
            if r and r["object_id"] not in seen:
                seen.add(r["object_id"])
                r["in_research_range"] = in_range(r, lo, hi)
                rows.append(r)
                got += 1
        print(f"  page {page}/{total_pages}: +{got} (total {len(rows)})", file=sys.stderr)
        if page < total_pages:
            time.sleep(args.delay)

    rows.sort(key=lambda r: (r["delo_no"] is None, r["delo_no"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["delo_no", "shifr", "title_ru", "dates_raw", "year_start", "year_end",
            "in_research_range", "object_id", "url"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    n_yes = sum(1 for r in rows if r["in_research_range"] == "yes")
    n_unk = sum(1 for r in rows if r["in_research_range"] == "unknown")
    print(f"\n{len(rows)} дела -> {args.out}")
    print(f"  in {lo}-{hi} : {n_yes}")
    print(f"  undated    : {n_unk}")
    print(f"  out of range: {len(rows)-n_yes-n_unk}")


if __name__ == "__main__":
    main()
