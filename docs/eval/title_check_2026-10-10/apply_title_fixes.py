"""Correct Repertoire work titles whose final ъ was stored as ь (or ѣ as ё), each one read on the scan (issue #151).

    uv run python docs/eval/title_check_2026-10-10/apply_title_fixes.py FIXES.csv            # dry run
    uv run python docs/eval/title_check_2026-10-10/apply_title_fixes.py FIXES.csv --write

FIXES.csv has `performance_id,printed_title` (the title as the scan reader read it). For each row the stored
work_title is located (page raw JSON -> sessions[s-1].works[w-1], from the performance_id `<page>__sNNN__wN`) and
changed ONLY at character positions where it differs from the printed title by ь->ъ or ё->ѣ (a genre suffix such as
", оп." after the title is kept as stored). Anything else, a length mismatch, or a stored title that does not
start like the printed one is reported and nothing is written. The edit is made on the file's text (the n-th
"work_title" value), so every other byte of the file stays as it was.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "outputs" / "full_run" / "raw"
ALLOWED = {("ь", "ъ"), ("ё", "ѣ"), ("Ь", "Ъ")}


def new_title(stored: str, printed: str):
    """stored title with ь->ъ / ё->ѣ applied where it differs from printed; None if anything else differs."""
    printed = printed.strip()
    if len(stored) < len(printed):
        return None
    head, tail = stored[:len(printed)], stored[len(printed):]
    out = []
    for a, b in zip(head, printed):
        if a == b:
            out.append(a)
        elif (a, b) in ALLOWED:
            out.append(b)
        else:
            return None
    return "".join(out) + tail


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    rows = list(csv.DictReader(open(args[0], encoding="utf-8")))
    by_page = defaultdict(list)
    for r in rows:
        m = re.match(r"^(.*)__s(\d+)__w(\d+)$", r["performance_id"])
        by_page[m.group(1)].append((int(m.group(2)), int(m.group(3)), r["printed_title"], r["performance_id"]))
    problems, done = [], 0
    for page, items in sorted(by_page.items()):
        path = RAW / f"{page}.raw.json"
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
        # the ordinal of every work in file order
        ordinal, n = {}, 0
        for si, s in enumerate(doc["sessions"], 1):
            for wi, w in enumerate(s.get("works") or [], 1):
                ordinal[(si, wi)] = n
                n += 1
        spans = [m for m in re.finditer(r'"work_title":\s*"((?:[^"\\]|\\.)*)"', text)]
        if len(spans) != n:
            problems.append((page, f"{len(spans)} work_title keys in the text vs {n} works parsed")); continue
        edits = []
        for si, wi, printed, pid in items:
            k = ordinal.get((si, wi))
            if k is None:
                problems.append((pid, "no such work")); continue
            stored = doc["sessions"][si - 1]["works"][wi - 1]["work_title"]
            if json.loads('"' + spans[k].group(1) + '"') != stored:
                problems.append((pid, "text/parsed mismatch")); continue
            nt = new_title(stored, printed)
            if nt is None:
                problems.append((pid, f"stored {stored!r} differs from printed {printed!r} by more than ь->ъ / ё->ѣ")); continue
            if nt == stored:
                problems.append((pid, f"already {stored!r}")); continue
            edits.append((spans[k].start(1), spans[k].end(1), nt, stored, pid))
        for a, b, nt, stored, pid in sorted(edits, reverse=True):
            text = text[:a] + nt + text[b:]
            done += 1
            print(f"  {pid}: {stored!r} -> {nt!r}")
        if write and edits:
            path.write_text(text, encoding="utf-8")
    print(f"{'WROTE' if write else 'DRY RUN'}: {done} titles changed in {len(by_page)} pages; {len(problems)} problems")
    for p in problems:
        print("  PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
