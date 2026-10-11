"""Classify the structure differences by what the stored sessions hold (issue #151 follow-up 15).

    uv run python docs/eval/title_check_2026-10-10/align/triage_structure.py      # after compare_structure.py

C_dark     read: one undivided dash; stored: two sessions, neither with works (a closure day stored as morning+evening)
C_content  read: one undivided cell; stored: two sessions, at least one with works  -> cascade-origin candidate (false split)
D_halfdash read: two halves, one of them a dash; stored: one session
D_other    read: two halves, both populated or unknown; stored: one session          -> merged halves / dropped half candidate
A          the reader omitted the row (not a data finding)
E          anything else
Writes align/triage.csv.
"""
import csv, re, collections
from pathlib import Path
import duckdb
HERE = Path(__file__).resolve().parent
con = duckdb.connect(str(HERE.parents[3] / "outputs/full_run/imperial_theaters.duckdb"), read_only=True)
R = list(csv.DictReader(open(HERE / "discrepancies.csv", encoding="utf-8")))


def info(ev):
    return con.execute("""select e.event_status, e.receipts_text, count(p.performance_id), string_agg(p.performance_title,' | ' order by p.performance_order)
        from raw.event_entry e left join raw.event_entry_performance p using(event_id) where e.event_id=? group by 1,2""", [ev]).fetchone()


rows = []
for r in R:
    rn = int(r["read_subcells"]) if r["read_subcells"] else None
    sn = int(r["stored_sessions"]) if r["stored_sessions"] else None
    st = [info(r["page_id"] + "__" + x.split(":")[0]) for x in (r["stored_events"] or "").split(",") if x]
    st = [s for s in st if s]
    if rn is None:
        c = "A"
    elif sn is None:
        c = "B"
    elif rn == 1 and sn >= 2:
        c = "C_dark" if all(s[2] == 0 for s in st) else "C_content"
    elif rn >= 2 and sn == 1:
        c = "D_halfdash" if re.search(r"dash|пуст", r["read_note"], re.I) else "D_other"
    else:
        c = "E"
    rows.append((c, r, st))
with open(HERE / "triage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["class", "page_id", "theater", "label", "read_subcells", "read_kind", "stored_events", "stored_status", "stored_works", "stored_receipts", "stored_titles", "read_note"])
    for c, r, st in rows:
        w.writerow([c, r["page_id"], r["theater"], r["label"], r["read_subcells"], r["read_kind"], r["stored_events"],
                    "/".join(str(s[0]) for s in st), "/".join(str(s[2]) for s in st), "/".join(str(s[1]) for s in st),
                    " // ".join((s[3] or "")[:60] for s in st), r["read_note"]])
print(collections.Counter(c for c, _, _ in rows))
