"""Track which оп. 18 дела have been requested from the researcher and which
have come back, so nothing on the 171-дело list is lost or ordered twice.

The master list `docs/rgia_request_log.csv` is the single source of truth. It
lives in docs/ deliberately: outputs/ is gitignored, and this is the only
record of what was ordered from RGIA and what came back. Tracking columns:
    batch          which request batch the дело belongs to ("" = not assigned)
    date_requested when that batch was actually sent
    date_received  when the files arrived
    notes          anything per-дело (not held, illegible, wrong file, ...)
    rg_piles       RG's sorting of a received дело, from the Reading Room's
                   sorting tray: ballet / editorial / sales / design, ";"-joined
                   (several allowed), or set_aside. Never filled by Claude.
    rg_sort_note   RG's reason, verbatim
    rg_sort_date   the date she sorted it

Usage:
    python pipeline/rgia_request_tracker.py status
    python pipeline/rgia_request_tracker.py assign --batch 2 --dela 170,172,174
    python pipeline/rgia_request_tracker.py requested --batch 1 --date 2026-09-22
    python pipeline/rgia_request_tracker.py received --dela 616,1309 --date 2026-10-05
    python pipeline/rgia_request_tracker.py note --dela 616 --text "not held"
    python pipeline/rgia_request_tracker.py note --dela 159 --replace --text "..."
    python pipeline/rgia_request_tracker.py sorting --from <out_dir>
        (copy RG's piles from the Reading Room: first pull them with
         ArtifactData `list` on collection `sorting` with that `out_dir`)
"""
from __future__ import annotations

import argparse, csv, json, re
from collections import Counter
from pathlib import Path

MASTER = Path("docs/rgia_request_log.csv")   # in docs/, not outputs/ -- outputs/ is gitignored
TRACK = ["batch", "date_requested", "date_received", "notes"]
SORT_COLS = ["rg_piles", "rg_sort_note", "rg_sort_date"]
PILES = ("ballet", "editorial", "sales", "design", "set_aside")


def load():
    rows = list(csv.DictReader(open(MASTER, encoding="utf-8")))
    cols = list(rows[0])
    for c in TRACK + SORT_COLS:
        if c not in cols: cols.append(c)
    for r in rows:
        for c in TRACK + SORT_COLS: r.setdefault(c, "")
    return rows, cols


def save(rows, cols):
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def pick(rows, dela: str):
    want = {d.strip().lstrip("Дд.").strip() for d in dela.split(",")}
    sel = [r for r in rows if r["дело"].replace("Д.", "").strip() in want]
    found = {r["дело"].replace("Д.", "").strip() for r in sel}
    missing = want - found
    if missing: raise SystemExit(f"not on the master list: {sorted(missing)}")
    return sel


def status(rows):
    n = len(rows)
    sent = [r for r in rows if r["date_requested"]]
    back = [r for r in rows if r["date_received"]]
    assigned = [r for r in rows if r["batch"]]
    print(f"master list: {n} дела")
    print(f"  assigned to a batch : {len(assigned)}")
    print(f"  requested           : {len(sent)}")
    print(f"  received            : {len(back)}")
    print(f"  NOT YET ASSIGNED    : {n - len(assigned)}")
    print("\nby batch:")
    for b, c in sorted(Counter(r["batch"] or "(unassigned)" for r in rows).items()):
        rs = [r for r in rows if (r["batch"] or "(unassigned)") == b]
        req = {r["date_requested"] for r in rs if r["date_requested"]}
        rec = sum(1 for r in rs if r["date_received"])
        print(f"  batch {b:<12} {c:>3} дела | requested {sorted(req) or '-'} | received {rec}/{c}")
    print("\nunassigned by группа:")
    for g, c in Counter(r["группа"] for r in rows if not r["batch"]).most_common():
        print(f"  {c:>3}  {g}")
    outstanding = sorted(
        (r for r in rows if r["date_requested"] and not r["date_received"]),
        key=lambda r: int(re.match(r"Д\. (\d+)", r["дело"]).group(1)))
    back_sorted = [r for r in back if r["rg_piles"]]
    print(f"\nsorted by RG: {len(back_sorted)} of {len(back)} received")
    for k in PILES:
        n = sum(k in r["rg_piles"].split(";") for r in back_sorted)
        if n: print(f"  {k:<10} {n}")
    if outstanding:
        print(f"\noutstanding (requested, not yet received): {len(outstanding)}")
        print("  " + ", ".join(r["дело"] for r in outstanding[:40]) + (" ..." if len(outstanding) > 40 else ""))


def pull_sorting(rows, src: str):
    """Copy RG's piles verbatim from an ArtifactData export of `sorting`
    (<src>/sorting/d<delo>.json). A дело with no doc there is cleared: she
    moved it back to the tray, or never sorted it."""
    folder = Path(src) / "sorting"
    if not folder.is_dir(): raise SystemExit(f"no {folder}: pull with ArtifactData list sorting out_dir={src}")
    got = {}
    for f in folder.glob("d*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        doc = doc.get("data", doc) if isinstance(doc.get("data"), dict) else doc
        piles = [p for p in doc.get("piles", []) if p]
        bad = set(piles) - set(PILES)
        if bad: raise SystemExit(f"{f.name}: unknown pile(s) {sorted(bad)}")
        got[f.stem[1:]] = (";".join(piles), doc.get("note", ""), doc.get("date", "") if piles else "")
    changed = 0
    for r in rows:
        d = r["дело"].replace("Д.", "").strip()
        new = got.get(d, ("", "", ""))
        if (r["rg_piles"], r["rg_sort_note"], r["rg_sort_date"]) != new:
            r["rg_piles"], r["rg_sort_note"], r["rg_sort_date"] = new; changed += 1
    unknown = set(got) - {r["дело"].replace("Д.", "").strip() for r in rows}
    if unknown: print(f"warning: sorting docs for дела not on the list: {sorted(unknown)}")
    print(f"{len(got)} sorting docs read; {changed} rows changed")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("sorting").add_argument("--from", dest="src", required=True)
    for name in ("assign", "requested", "received", "note"):
        s = sub.add_parser(name)
        s.add_argument("--batch"); s.add_argument("--dela"); s.add_argument("--date"); s.add_argument("--text")
        s.add_argument("--replace", action="store_true",
                       help="note: overwrite instead of appending")
    a = ap.parse_args()
    rows, cols = load()

    if a.cmd == "status":
        status(rows); return
    if a.cmd == "sorting":
        pull_sorting(rows, a.src); save(rows, cols); status(rows); return
    if a.cmd == "assign":
        for r in pick(rows, a.dela): r["batch"] = a.batch
        print(f"assigned {len(a.dela.split(','))} дела to batch {a.batch}")
    elif a.cmd == "requested":
        sel = [r for r in rows if r["batch"] == a.batch] if a.batch else pick(rows, a.dela)
        for r in sel: r["date_requested"] = a.date
        print(f"marked {len(sel)} дела requested on {a.date}")
    elif a.cmd == "received":
        sel = pick(rows, a.dela)
        for r in sel: r["date_received"] = a.date
        print(f"marked {len(sel)} дела received on {a.date}")
    elif a.cmd == "note":
        for r in pick(rows, a.dela):
            if a.replace:                     # collapse a note that has accreted
                r["notes"] = a.text
            else:
                r["notes"] = (r["notes"] + " | " + a.text).strip(" |")
        print("note replaced" if a.replace else "note added")
    save(rows, cols); status(rows)


if __name__ == "__main__":
    main()
