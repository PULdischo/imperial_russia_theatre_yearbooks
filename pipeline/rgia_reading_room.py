"""Build the data for the RGIA Reading Room artifact (one page tracking every
requested дело and, for each one received, a page-by-page reading guide).

    uv run python pipeline/rgia_reading_room.py

Inputs (both tracked in git):
  docs/rgia_request_log.csv        what was requested / received (rgia_request_tracker.py)
  docs/rgia/dela/<delo>.jsonl      page triage for each received дело

Outputs, under outputs/rgia_reading_room/ (regenerable):
  seed/dela/d<delo>.json           one document per дело for the artifact's `dela` collection
  seed/pages/d<delo>[_k].json      the triage rows, chunked to stay under the 256 KiB doc cap
  sprites/<delo>.jpg               every page of a дело tiled into one thumbnail sheet

The seed files are written into the artifact's database with the ArtifactData
tool (`file_path` per document). The reader's own marks (read / key / skip and
notes) live only in the artifact's `marks` collection; pull them back with
ArtifactData `list` on `marks` before relying on them anywhere else.
"""
import csv
import glob
import json
import re
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "rgia_request_log.csv"
TRIAGE = ROOT / "docs" / "rgia" / "dela"
DELA_IMG = ROOT / "outputs" / "rgia_dela"
OUT = ROOT / "outputs" / "rgia_reading_room"

CELL_W, CELL_H, COLS = 150, 190, 10   # sprite geometry; the page reads these from the дело doc
CHUNK_BYTES = 200_000
EDITORIAL_SUBTAGS = ("ed_contributors", "ed_illustrations", "ed_print_finance", "ed_editors")


def sprite(delo, n_pages):
    thumbs = DELA_IMG / str(delo) / "thumbs"
    if not thumbs.exists():
        return None
    rows = (n_pages + COLS - 1) // COLS
    sheet = np.full((rows * CELL_H, COLS * CELL_W, 3), 235, np.uint8)
    for p in range(1, n_pages + 1):
        f = thumbs / f"p{p:03d}.jpg"
        if not f.exists():
            continue
        im = cv2.imread(str(f))
        s = min(CELL_W / im.shape[1], CELL_H / im.shape[0])
        im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        r, c = divmod(p - 1, COLS)
        y = r * CELL_H + (CELL_H - im.shape[0]) // 2
        x = c * CELL_W + (CELL_W - im.shape[1]) // 2
        sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
    out = OUT / "sprites" / f"{delo}.jpg"
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return out.name


def main():
    for d in ("seed/dela", "seed/pages", "sprites"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    for old in glob.glob(str(OUT / "seed" / "pages" / "*.json")):
        Path(old).unlink()

    with open(LOG, encoding="utf-8-sig") as fh:
        log = list(csv.DictReader(fh))

    n_triaged = 0
    for row in log:
        delo = re.sub(r"\D", "", row["дело"])
        doc = {
            "delo": int(delo),
            "title": row["заголовок"],
            "group": row["группа"],
            "why": row["why_of_interest"],
            "dates": row["даты по описи (прочитано вручную)"] or row["крайние даты (RGIA)"],
            "leaves": row["количество листов"],
            "link": row["ссылка"],
            "batch": row["batch"],
            "requested": row["date_requested"],
            "received": row["date_received"],
            "notes": row["notes"],
            "triaged": False,
        }
        tf = TRIAGE / f"{delo}.jsonl"
        if tf.exists():
            pages = [json.loads(l) for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()]
            pages.sort(key=lambda r: r["page"])
            chunks, cur = [], []
            for p in pages:
                cur.append(p)
                if len(json.dumps(cur, ensure_ascii=False).encode()) > CHUNK_BYTES:
                    chunks.append(cur[:-1])
                    cur = [p]
            chunks.append(cur)
            ids = []
            for k, ch in enumerate(chunks):
                pid = f"d{delo}" + (f"_{k + 1}" if k else "")
                ids.append(pid)
                (OUT / "seed" / "pages" / f"{pid}.json").write_text(
                    json.dumps({"delo": int(delo), "rows": ch}, ensure_ascii=False), encoding="utf-8")
            n_pdf = max(p["page"] for p in pages)
            doc.update({
                "triaged": True,
                "page_docs": ids,
                "n_pages": n_pdf,
                "n_high": sum(p.get("relevance") == "high" for p in pages),
                "n_ballet": sum(bool(p.get("ballet")) for p in pages),
                "n_editorial": sum(bool(p.get("editorial")) for p in pages),
                **{f"n_{k}": sum(bool(p.get(k)) for p in pages) for k in EDITORIAL_SUBTAGS},
                "sprite": sprite(delo, n_pdf),
                "sprite_geom": {"w": CELL_W, "h": CELL_H, "cols": COLS},
            })
            n_triaged += 1
        (OUT / "seed" / "dela" / f"d{delo}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"{len(log)} дела written; {n_triaged} with page triage -> {OUT}")


if __name__ == "__main__":
    main()
