"""Merge the reading agents' entry-level part files for a register дело
(Д. 189, Д. 190) into docs/rgia/dela/<delo>_items.jsonl.

    uv run python pipeline/rgia_merge_items.py --dela 189,190

Reads  outputs/rgia_dela/<delo>/items/part*.jsonl   (one JSON object per entry)
Writes docs/rgia/dela/<delo>_items.jsonl            (sorted by page, then order read)

Checks, and refuses to write a дело that fails: unparseable lines, missing keys,
pages outside the дело, and -- reported but not fatal, since a register legitimately
has blank pages -- pages with no entries and gaps or repeats in the entry numbering.
"""
import argparse, glob, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ("ed_contributors", "ed_illustrations", "ed_print_finance", "ed_editors")
REQUIRED = ("delo", "page", "entry_no", "day", "month_year", "content_ru", "content_en",
            "key_names", "ballet", "legibility", "notes") + SUB


def merge(delo: str) -> None:
    src = ROOT / "outputs" / "rgia_dela" / delo
    n_pages = len(glob.glob(str(src / "pages" / "o*")))
    rows, problems = [], []
    for f in sorted(glob.glob(str(src / "items" / "part*.jsonl"))):
        for i, line in enumerate(open(f, encoding="utf-8"), 1):
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append(f"{Path(f).name}:{i} unparseable ({e})"); continue
            missing = [k for k in REQUIRED if k not in r]
            if missing:
                problems.append(f"{Path(f).name}:{i} missing {missing}"); continue
            if not (1 <= int(r["page"]) <= n_pages):
                problems.append(f"{Path(f).name}:{i} page {r['page']} outside 1..{n_pages}")
                continue
            r["editorial"] = any(bool(r.get(k)) for k in SUB)
            rows.append(r)
    if problems:
        print(f"Д.{delo}: NOT written -- {len(problems)} problem(s)")
        for p in problems[:10]: print("   ", p)
        return
    rows.sort(key=lambda r: int(r["page"]))
    out = ROOT / "docs" / "rgia" / "dela" / f"{delo}_items.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    pages_with = {int(r["page"]) for r in rows}
    empty = [p for p in range(1, n_pages + 1) if p not in pages_with]
    print(f"Д.{delo}: {len(rows)} entries over {len(pages_with)}/{n_pages} pages -> {out}")
    print(f"   ballet {sum(1 for r in rows if r['ballet'])} | editorial {sum(1 for r in rows if r['editorial'])}")
    if empty: print(f"   pages with no entries ({len(empty)}): {empty[:20]}{' ...' if len(empty)>20 else ''}")

    # A дело can hold more than one numbered sequence: Д. 189 has a separate 1892
    # free-copies register bound in as folio 9, numbered 1-7 of its own, and Д. 190
    # has a block re-entered from the previous year's journal. So don't check one
    # flat run -- split where the numbering restarts, and check each run separately.
    seq, runs = [], []
    for r in rows:
        m = re.match(r"\d+", str(r["entry_no"]) or "")
        if not m:
            continue
        n = int(m.group())
        if seq and n <= seq[-1][0]:
            runs.append(seq); seq = []
        seq.append((n, int(r["page"])))
    if seq: runs.append(seq)
    for i, run in enumerate(runs, 1):
        nums = [n for n, _ in run]
        lo, hi = min(nums), max(nums)
        gaps = [n for n in range(lo, hi) if n not in set(nums)]
        dupes = [n for n, c in Counter(nums).items() if c > 1]
        label = f"   run {i}: NN {lo}-{hi} on pp. {run[0][1]}-{run[-1][1]} ({len(nums)} entries)"
        print(label)
        if gaps:  print(f"      MISSING numbers ({len(gaps)}): {gaps[:20]}{' ...' if len(gaps)>20 else ''}")
        if dupes: print(f"      REPEATED numbers ({len(dupes)}): {sorted(dupes)[:20]}")
    if len(runs) > 1:
        print(f"   ({len(runs)} separate numbered sequences -- expected where another "
              f"register is bound in or a block was re-entered from another year)")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dela", required=True)
    for d in ap.parse_args().dela.split(","): merge(d.strip())


if __name__ == "__main__":
    main()
