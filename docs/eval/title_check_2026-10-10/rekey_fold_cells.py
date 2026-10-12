"""Re-key rcpt_fold_obscured_cells.csv to the current sessions (issue #151 follow-up 22).

    uv run python docs/eval/title_check_2026-10-10/rekey_fold_cells.py LOG_ITEMS.json [--write]

Session ids (`__sNNN`) are positional and moved when later fixes deleted or inserted sessions, so 10 of the 92 ids no longer pointed
at the cell the reader described.  Each row is re-matched on its page by first title (or its old id), date within a day, and an
empty or partly-read («?») receipts figure; exactly one session must qualify.  The rewritten file carries the cell's stable key
(page_id, date_text, theater, time_of_day) beside the current event_id, and whether the Binding Fold Log (its ITEMS array, saved
as LOG_ITEMS.json) already has the cell.
"""
import csv, datetime, json, re, sys
from pathlib import Path
import duckdb
ROOT = Path(__file__).resolve().parents[3]
F = Path(__file__).with_name("rcpt_fold_obscured_cells.csv")
WRITE = "--write" in sys.argv
D = datetime.date.fromisoformat
norm = lambda s: re.sub(r"[^a-zа-яѣіѳ]", "", s.lower())[:5]
items = json.load(open(sys.argv[1], encoding="utf-8"))
log = {(i["page_id"], i["date_text"].split()[0], e["theater"].strip(".")[:5]) for i in items for e in i["entries"]}
c = duckdb.connect(str(ROOT / "outputs/full_run/imperial_theaters.duckdb"), read_only=True)
rows = list(csv.DictReader(open(F, encoding="utf-8")))
out = []
for r in rows:
    page = r.get("page_id") or r["event_id"].split("__")[0]
    first = norm(r["reader_lines"].split("|")[0].split(",")[0])
    cands = c.execute("""select e.event_id, e.date_text, e.date_undate, e.time_of_day, e.theater, e.receipts_text,
        (select string_agg(performance_title, ' | ' order by cast(performance_order as int)) from raw.event_entry_performance p
          where p.event_id = e.event_id) from raw.event_entry e where page_id = ?""", [page]).fetchall()
    ok = [x for x in cands if abs((D(x[2]) - D(r["date"])).days) <= 1 and (not x[5] or "?" in x[5])
          and ((x[6] and norm(x[6].split("|")[0]) == first) or x[0] == r["event_id"])]
    titled = [x for x in ok if x[6] and norm(x[6].split("|")[0]) == first]
    ok = titled or ok
    assert len(ok) == 1, (r["item"], r["event_id"], [(x[0], x[2], x[5], x[6]) for x in ok])
    x = ok[0]
    out.append({"item": r["item"], "page_id": page, "season": r["season"], "city": r["city"], "date": x[2], "date_text": x[1],
                "theater": x[4], "time_of_day": x[3], "event_id": x[0], "stored_works": x[6] or "", "stored_receipts": x[5] or "",
                "in_fold_log": "yes" if (page, x[1].split()[0], x[4].strip(".")[:5]) in log else "no",
                "reader_receipts": r["reader_receipts"], "reader_lines": r["reader_lines"], "reader_note": r["reader_note"]})
moved = sum(1 for r, o in zip(rows, out) if r["event_id"] != o["event_id"])
print(len(out), "cells;", moved, "ids changed;", sum(o["in_fold_log"] == "no" for o in out), "not in the log;",
      sum(bool(o["stored_receipts"]) for o in out), "with a partly-read figure")
assert len({o["event_id"] for o in out}) == len(out)
if WRITE:
    with open(F, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
