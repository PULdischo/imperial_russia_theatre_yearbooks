"""Merge the reading agents' part files for one or more дела into the tracked
page triage, checking that every PDF page is covered exactly once.

    uv run python pipeline/rgia_merge_triage.py --dela 160,161,162

Reads  outputs/rgia_dela/<delo>/triage/part*.jsonl  (one JSON object per page)
Writes docs/rgia/dela/<delo>.jsonl                  (sorted, one line per page)

A дело is written only if it passes: no unparseable lines, no missing pages
(checked against the extracted page images), all required keys present.
"editorial" is recomputed as "any ed_* sub-tag is true" so the two can never
disagree. Nothing else in a row is altered.
"""
import argparse
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUB = ("ed_contributors", "ed_illustrations", "ed_print_finance", "ed_editors")
REQUIRED = ("page", "folio", "doc_type", "script", "date", "from_to", "gist", "key_names",
            "legibility", "relevance", "why", "ballet") + SUB


def merge(delo):
    src = ROOT / "outputs" / "rgia_dela" / delo
    n_pages = len(glob.glob(str(src / "pages" / "o*")))
    rows, problems = {}, []
    for f in sorted(glob.glob(str(src / "triage" / "part*.jsonl"))):
        for i, line in enumerate(open(f, encoding="utf-8"), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{Path(f).name}:{i} not valid JSON")
                continue
            miss = [k for k in REQUIRED if k not in r]
            if miss:
                problems.append(f"page {r.get('page')}: missing keys {miss}")
                continue
            if r["page"] in rows:
                problems.append(f"page {r['page']} appears twice")
            r["delo"] = delo
            for k in SUB + ("ballet",):
                r[k] = bool(r[k])
            r["editorial"] = any(r[k] for k in SUB)
            if r["relevance"] not in ("high", "medium", "low"):
                problems.append(f"page {r['page']}: relevance {r['relevance']!r}")
            rows[r["page"]] = r
    missing = [p for p in range(1, n_pages + 1) if p not in rows]
    extra = [p for p in rows if not 1 <= p <= n_pages]
    if missing:
        problems.append(f"missing pages {missing}")
    if extra:
        problems.append(f"pages outside 1..{n_pages}: {extra}")
    if problems:
        print(f"Д. {delo}: NOT written -- " + "; ".join(problems))
        return False
    out = ROOT / "docs" / "rgia" / "dela" / f"{delo}.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for p in sorted(rows):
            fh.write(json.dumps(rows[p], ensure_ascii=False) + "\n")
    v = list(rows.values())
    print(f"Д. {delo}: {len(v)} pages | high {sum(r['relevance'] == 'high' for r in v)}"
          f" | ballet {sum(r['ballet'] for r in v)} | editorial {sum(r['editorial'] for r in v)}"
          f" (" + ", ".join(f"{k[3:]} {sum(r[k] for r in v)}" for k in SUB) + ")")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dela", required=True, help="comma-separated дело numbers")
    a = ap.parse_args()
    ok = [merge(d.strip()) for d in a.dela.split(",")]
    raise SystemExit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
