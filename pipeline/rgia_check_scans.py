"""Check the «Наличие отсканированных листов» flag on every дело of оп. 18,
and capture any per-дело attributes the tree listing omits.

Resumable: appends to the CSV and skips object_ids already recorded.
"""
from __future__ import annotations
import argparse, csv, html, json, re, sys, time, urllib.request
from pathlib import Path

def attrs(oid: str) -> dict:
    req = urllib.request.Request(
        f"https://fgurgia.ru/ajax/obj/{oid}/188295?children=false",
        headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
    d = json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))
    out = {}
    for a in d.get("attributes", []):
        name = (a.get("name") or a.get("systemName") or "").strip()
        txt = html.unescape(re.sub("<[^>]+>", "", str(a.get("text") or ""))).strip()
        if name and txt:
            out[name] = txt
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("outputs/rgia_catalogue/opis18_dela.csv"))
    ap.add_argument("--out", type=Path, default=Path("outputs/rgia_catalogue/opis18_scans.csv"))
    ap.add_argument("--delay", type=float, default=0.15)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.src, encoding="utf-8")))
    done = set()
    if args.out.exists():
        done = {r["object_id"] for r in csv.DictReader(open(args.out, encoding="utf-8"))}
    cols = ["delo_no", "shifr", "object_id", "scans_available", "dates_attr", "extra_attrs"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    new = not args.out.exists()
    with open(args.out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new: w.writeheader()
        for i, r in enumerate(rows, 1):
            if r["object_id"] in done: continue
            try: a = attrs(r["object_id"])
            except Exception as e:
                print(f"  Д.{r['delo_no']}: {e!r}", file=sys.stderr); continue
            known = {"Шифр","Название фонда","Опись","Заголовок","Крайние даты",
                     "Наличие отсканированных листов"}
            w.writerow({
                "delo_no": r["delo_no"], "shifr": r["shifr"], "object_id": r["object_id"],
                "scans_available": a.get("Наличие отсканированных листов", ""),
                "dates_attr": a.get("Крайние даты", ""),
                "extra_attrs": "; ".join(f"{k}={v[:60]}" for k, v in a.items() if k not in known),
            })
            f.flush()
            if i % 100 == 0: print(f"  {i}/{len(rows)}", file=sys.stderr)
            time.sleep(args.delay)
    print("done", file=sys.stderr)

if __name__ == "__main__":
    main()
