"""Two titles misread by the extraction, corpus-wide (RG 2026-10-29: "Yes, fix them").

Every Repertoire cell stored as «Бѣшеные деньги», «Лакма» or «Лакмѣ» was read on the full-resolution embedded scans
(docs/eval/scan_audit/spelling_reads_beshenyya_lakme_2026-10-29.csv; four readers, every crop re-checked by Claude):
- all 39 «Бѣшеные деньги» (1893-94 to 1907-08) print «Бѣшеныя деньги»; with the 5 fixed in the 1904-05 title audit,
  the comedy is «Бѣшеныя» in every printing checked;
- «Лакма» (Большой 14 Oct 1902) and «Лакмѣ» (Большой 25 Nov 1905) both print «Лакмэ».
The 18 cells stored «Лакме» (1899-00 to 1902-03) really print «Лакме» and are not touched.
Only the title string changes; genre, row order and event ids are unchanged.

uv run python docs/eval/reconciliation/fix_beshenyya_lakme_titles.py [--raw-dir DIR] [--write]"""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else ROOT / "outputs/full_run/raw"
READS = ROOT / "docs/eval/scan_audit/spelling_reads_beshenyya_lakme_2026-10-29.csv"
NEW = {"Бѣшеные деньги": "Бѣшеныя деньги", "Лакма": "Лакмэ", "Лакмѣ": "Лакмэ"}
TAG = "scan 2026-10-29 (scan_audit/spelling_reads_beshenyya_lakme_2026-10-29.csv)"


def load(pg):
    p = RAW / f"{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


rows = [r for r in csv.DictReader(open(READS, encoding="utf-8")) if r["matches_stored"] == "no"]
assert len(rows) == 41, len(rows)
pages, n = {}, 0
for r in rows:
    old = r["stored_title"]; new = NEW[old]
    assert r["printed_title"].strip() == new, r
    pg, s = r["event_id"].split("__"); i = int(s[1:]) - 1
    if pg not in pages:
        pages[pg] = load(pg)
    S = pages[pg][1]["sessions"][i]
    hits = [w for w in S["works"] if w["work_title"] == old]
    assert len(hits) == 1, (r["event_id"], S["works"])
    hits[0]["work_title"] = new
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: title «{old}» -> «{new}» (misread)"
    n += 1
    print(r["event_id"], old, "->", new)

if "--write" in sys.argv:
    for p, d, fmt in pages.values():
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
print(n, "cells on", len(pages), "pages,", "WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
