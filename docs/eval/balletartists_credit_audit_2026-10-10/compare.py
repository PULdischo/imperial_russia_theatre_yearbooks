"""Compare the blind readers' printed credit summaries with the stored raw JSON (issue #150).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/compare.py

Reads worklist.csv and reader_reports/chunk_*.csv, writes comparison.csv and prints a summary.
Nothing is edited here; apply_fixes.py does that, from comparison.csv, after the decisions are made.

Per entry the reader's text is split into tokens (words, numbers, punctuation) and aligned with the
stored text. The verdict is one of:
  AGREE                  identical to the stored text
  LETTERS_ONLY           same tokens, differing only in letters (e.g. a Latin c for a Cyrillic с)
  DIGITS_ONLY            same tokens, differing only in numbers
  LETTERS_AND_DIGITS     both
  STRUCTURE_DIFFERS      different token count: needs a person's eye
  NOT_USABLE             the reader said NOT FOUND / NONE PRINTED / had ‹?›
Also reported: whether the reader's own numbers add up (parts == Всего), the check that makes a digit
reading trustworthy.
"""
from __future__ import annotations

import csv
import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN = re.compile(r"[^\W\d_]+|\d+|[^\w\s]", re.U)
CY = re.compile("[а-яёѣіѳѵА-ЯЁѢІѲѴ]")
LA = re.compile("[A-Za-zα-ωΑ-Ω]")


def tokens(s: str) -> list[str]:
    return TOKEN.findall(s or "")


def adds_up(text: str) -> bool | None:
    """True/False if the printed parts add up to the printed total; None if it cannot be told.
    Mirrors quality_checks._PRINTED_PART_RE / _PRINTED_TOTAL_RE, on the part before «Въ томъ числѣ»."""
    head = (text or "").split("Всего")[0]
    parts = [int(x) for x in re.findall(r"[Вв]ъ\s+(?:\d+\s+)?[^\W\d_]+\s*[—-]?\s*(\d+)", head)]
    m = re.search(r"Всего\s*[—-]?\s*(\d+)", text or "")
    if not parts or not m:
        return None
    return sum(parts) == int(m[1])


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--worklists", nargs="+", default=["worklist.csv"])
    ap.add_argument("--out", default="comparison.csv")
    args = ap.parse_args()
    work = {}
    for wl in args.worklists:
        work.update({r["entry_id"]: r for r in csv.DictReader(open(HERE / wl, encoding="utf-8"))})
    reads = {}
    for f in sorted(glob.glob(str(HERE / "reader_reports" / "chunk_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            reads[r["entry_id"]] = r
    out = []
    missing = [e for e in work if e not in reads]
    for eid, w in work.items():
        r = reads.get(eid)
        stored = w["stored_summary"]
        if r is None:
            out.append(dict(entry_id=eid, verdict="NO_REPORT", why=w["why"], stored=stored, read="", note="", reader_adds_up="", stored_adds_up=adds_up(stored)))
            continue
        read, note = (r["printed_summary"] or "").strip(), (r.get("note") or "").strip()
        if read in ("NOT FOUND", "NONE PRINTED") or "‹?›" in read:
            verdict = "NOT_USABLE"
        elif read == stored:
            verdict = "AGREE"
        else:
            a, b = tokens(stored), tokens(read)
            if len(a) != len(b):
                verdict = "STRUCTURE_DIFFERS"
            else:
                diffs = [(x, y) for x, y in zip(a, b) if x != y]
                num = [d for d in diffs if d[0].isdigit() or d[1].isdigit()]
                let = [d for d in diffs if not (d[0].isdigit() or d[1].isdigit())]
                verdict = ("LETTERS_AND_DIGITS" if num and let else "DIGITS_ONLY" if num else "LETTERS_ONLY")
        out.append(dict(entry_id=eid, verdict=verdict, why=w["why"], stored=stored, read=read, note=note,
                        reader_adds_up=adds_up(read) if read and verdict != "NOT_USABLE" else "",
                        stored_adds_up=adds_up(stored)))
    with open(HERE / args.out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0]))
        wr.writeheader()
        wr.writerows(out)
    from collections import Counter
    print("entries:", len(out), "| without a reader report:", len(missing))
    print(Counter(o["verdict"] for o in out).most_common())
    print("reader's numbers add up:", Counter(str(o["reader_adds_up"]) for o in out if o["reader_adds_up"] != "").most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
