"""Keep the editorial timeline's arithmetic up to date and list what needs RG.

    uv run python pipeline/rgia_editorial_timeline.py [--check] [--rg-reads <file.json>]

Inputs (tracked): docs/rgia/editorial_acts.csv, docs/rgia/editorial_spans.csv
(design: docs/rgia/editorial_timeline_design.md).

What it changes, and only this:
  - each span's earliest_act_id/earliest_date and latest_act_id/latest_date,
    recomputed from the dated acts listed in its act_ids;
  - with --rg-reads, the acts' rg_read_date/rg_note, copied verbatim from RG's
    `rg_reads` collection in the Reading Room (ArtifactData `list rg_reads`
    with `out_dir`; pass that directory). Claude never writes to that collection.
Everything that needs judgment (undated acts, uncovered acts, brackets that
contradict the acts, spans marked established without RG-read acts, uncertain
readings) is printed as a list for RG and left alone.

It also writes the Reading Room's Timeline seed (outputs/rgia_reading_room/
seed/timeline/{acts,spans}.json) for the artifact's `timeline` collection.

--check writes nothing and exits 1 if the span arithmetic is out of date.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTS = ROOT / "docs" / "rgia" / "editorial_acts.csv"
SPANS = ROOT / "docs" / "rgia" / "editorial_spans.csv"
SEED = ROOT / "outputs" / "rgia_reading_room" / "seed" / "timeline"

SOURCES = {"autograph", "office copy", "typed copy", "another hand's note"}
READINGS = {"checked by Claude", "summary only", "uncertain"}
DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
ARITH = ("earliest_act_id", "earliest_date", "latest_act_id", "latest_date")


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def write(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(rows)


def bounds(d):
    """A partial date's lowest and highest possible values, as sortable strings."""
    lo = d + "-01-01"[len(d) - 4:] if len(d) < 10 else d
    hi = d + "-12-31"[len(d) - 4:] if len(d) < 10 else d
    return lo, hi


def load_rg_reads(path):
    path = Path(path)
    if path.is_dir():  # ArtifactData `list rg_reads` with out_dir: <dir>/rg_reads/<act_id>.json
        files = sorted(path.rglob("*.json"))
        return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in files}
    data = json.loads(path.read_text(encoding="utf-8"))
    docs = data.get("docs", data) if isinstance(data, dict) else data
    if isinstance(docs, dict):  # {act_id: {date, note}}
        return {k: v for k, v in docs.items()}
    out = {}
    for d in docs:  # [{id, data:{...}}] or [{id, date, note}]
        out[d.get("id") or d.get("doc_id")] = d.get("data", d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rg-reads")
    a = ap.parse_args()

    acols, acts = read(ACTS)
    scols, spans = read(SPANS)
    problems, for_rg, changes = [], [], []

    by_id = {}
    for r in acts:
        if r["act_id"] in by_id:
            problems.append(f"duplicate act_id {r['act_id']}")
        by_id[r["act_id"]] = r
        if r["source"] not in SOURCES:
            problems.append(f"{r['act_id']}: source {r['source']!r} not one of {sorted(SOURCES)}")
        if r["claude_reading"] not in READINGS:
            problems.append(f"{r['act_id']}: claude_reading {r['claude_reading']!r} not one of {sorted(READINGS)}")
        for f in ("date_normalised", "rg_read_date"):
            if r[f] and not DATE.match(r[f]):
                problems.append(f"{r['act_id']}: {f} {r[f]!r} is not YYYY, YYYY-MM or YYYY-MM-DD")

    if a.rg_reads:
        for aid, v in load_rg_reads(a.rg_reads).items():
            if aid not in by_id:
                for_rg.append(f"RG-read note for unknown act {aid}: {v}")
                continue
            r = by_id[aid]
            for f, k in (("rg_read_date", "date"), ("rg_note", "note")):
                new = (v.get(k) or "").strip()
                if new != r[f]:
                    changes.append(f"{aid} {f}: {r[f]!r} -> {new!r} (from RG's rg_reads)")
                    r[f] = new

    covered = set()
    for s in spans:
        ids = [x for x in s["act_ids"].split(";") if x]
        covered.update(ids)
        missing = [x for x in ids if x not in by_id]
        if missing:
            problems.append(f"{s['span_id']}: act_ids not in acts: {missing}")
        members = [by_id[x] for x in ids if x in by_id]
        dated = [m for m in members if m["date_normalised"]]
        new = dict.fromkeys(ARITH, "")
        if dated:
            first = min(dated, key=lambda m: bounds(m["date_normalised"])[0])
            last = max(dated, key=lambda m: bounds(m["date_normalised"])[1])
            new = {"earliest_act_id": first["act_id"], "earliest_date": first["date_normalised"],
                   "latest_act_id": last["act_id"], "latest_date": last["date_normalised"]}
            # a partial date that overlaps the chosen end makes the order a judgment call
            for end, pick, side in (("earliest", first, 0), ("latest", last, 1)):
                rivals = [m["act_id"] for m in dated if m is not pick
                          and bounds(m["date_normalised"])[0] <= bounds(pick["date_normalised"])[1]
                          and bounds(m["date_normalised"])[1] >= bounds(pick["date_normalised"])[0]
                          and len(m["date_normalised"]) != len(pick["date_normalised"])]
                if rivals:
                    for_rg.append(f"{s['span_id']} ({s['person']}): {end} act {pick['act_id']} "
                                  f"({pick['date_normalised']}) may be tied with partly dated {rivals}")
        for f in ARITH:
            if s[f] != new[f]:
                changes.append(f"{s['span_id']} {f}: {s[f]!r} -> {new[f]!r}")
                s[f] = new[f]

        undated = [m["act_id"] for m in members if not m["date_normalised"]]
        if undated:
            for_rg.append(f"{s['span_id']} ({s['person']}): undated acts {undated} could move a "
                          f"bracket; dating them is a judgment")
        if s["not_before"] and new["earliest_date"] and bounds(new["earliest_date"])[1] < bounds(s["not_before"])[0]:
            for_rg.append(f"{s['span_id']}: act {new['earliest_act_id']} ({new['earliest_date']}) is "
                          f"earlier than not_before {s['not_before']}: contradiction")
        if s["not_after"] and new["latest_date"] and bounds(new["latest_date"])[0] > bounds(s["not_after"])[1]:
            for_rg.append(f"{s['span_id']}: act {new['latest_act_id']} ({new['latest_date']}) is "
                          f"later than not_after {s['not_after']}: contradiction")
        unread = [m["act_id"] for m in members if not m["rg_read_date"]]
        if s["status"] == "established" and (unread or not s["rg_ruling"]):
            for_rg.append(f"{s['span_id']}: marked established but acts not RG-read {unread}"
                          + ("" if s["rg_ruling"] else " and no RG ruling"))

    uncovered = [r["act_id"] for r in acts if r["act_id"] not in covered]
    if uncovered:
        for_rg.append(f"acts in no span (a new span is a judgment): {uncovered}")

    n_rg = sum(bool(r["rg_read_date"]) for r in acts)
    unread_names = sorted({r["act_id"] for r in acts if not r["rg_read_date"]})
    print(f"{len(acts)} acts ({n_rg} RG-read), {len(spans)} spans")
    for title, items in (("Problems in the files", problems), ("Arithmetic updates", changes),
                         ("For RG (not changed)", for_rg)):
        print(f"\n{title}: {len(items) or 'none'}")
        for x in items:
            print("  -", x)
    print(f"\nActs awaiting RG's reading: {len(unread_names)}")

    if a.check:
        sys.exit(1 if (problems or any(not c.startswith("A") for c in changes)) else 0)
    if problems:
        sys.exit("Not writing: fix the problems above first.")
    if changes:
        write(ACTS, acols, acts)
        write(SPANS, scols, spans)
    SEED.mkdir(parents=True, exist_ok=True)
    (SEED / "acts.json").write_text(json.dumps({"rows": acts}, ensure_ascii=False), encoding="utf-8")
    (SEED / "spans.json").write_text(json.dumps({"rows": spans}, ensure_ascii=False), encoding="utf-8")
    print(f"Timeline seed written to {SEED.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
