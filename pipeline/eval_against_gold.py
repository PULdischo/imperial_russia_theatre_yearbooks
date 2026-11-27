"""Stage 4: score a parsed run against docs/eval/gold. Consolidates the
ad hoc comparison scripts used during the pilot into one reusable tool, so
scoring a new prompt/model version is a rerun of this file, not a rewritten
one-off script -- and its summary line is meant to be appended to
docs/eval/run_history.csv so accuracy is tracked across runs, not just
eyeballed once and forgotten.

Roster rows are compared positionally within a page (the model has reliably
preserved printed list order every run so far -- see docs/eval/known_issues.md
if that stops holding). Repertoire rows are compared by (day-number,
theater-prefix, session) since row ORDER is not reliable there (the model
sometimes emits column-by-column instead of row-by-row) -- see
docs/eval/known_issues.md "repertoire row ordering is not stable".

Usage:
    python pipeline/eval_against_gold.py --parsed-dir outputs/pilot/parsed \
        --gold-dir docs/eval/gold --out outputs/pilot/eval_report.txt
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
import csv

ROSTER_FIELDS = ["family_name", "first_name", "patronymic", "heading_path", "rank_or_title",
                  "tenure_note_text", "instrument", "service_class", "subject_taught"]
EVENT_FIELDS = ["city", "event_status", "time_of_day"]
KNOWN_THEATERS = ["Маріинскій", "Александринскій", "Михайловскій", "Большой", "Малый", "Новый"]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def norm_tenure(s: str) -> str:
    """Compare tenure notes without their brackets and stops (RG, 2026-11-27,
    option C). The gold holds the print verbatim -- «(съ 24 мая 1847 г.).» --
    but the stored rows carry the brackets three ways (none, both, closing
    only; docs/eval/gold_refresh_2026-11-27.md), a punctuation question kept
    out of the score. A lost bracket is counted separately (see main())."""
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"\.{2,}", ".", s)
    s = re.sub(r"\.\s*;", ";", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".").strip()


def norm_heading(s: str) -> str:
    """Heading segments compared without a printed end colon or stop
    («Артистки:» = «Артистки»): stored rows keep them on some lists and not
    on others (2026-11-27, same reasoning as norm_tenure)."""
    return " / ".join(seg.strip().rstrip(":.").strip() for seg in s.split(" / "))


FIELD_NORMALIZERS = {"tenure_note_text": norm_tenure, "heading_path": norm_heading}


def by_page(rows: list[dict]) -> dict[str, list[dict]]:
    d = defaultdict(list)
    for r in rows:
        d[r["page_id"]].append(r)
    return d


def theater_key(t: str) -> str:
    t = t.strip().rstrip(".")
    for name in KNOWN_THEATERS:
        if t.startswith(name):
            return name
    return t


def eval_roster(gold_dir: Path, parsed_dir: Path) -> tuple[int, int, list[str]]:
    gold = by_page(load(gold_dir / "person_entry.csv"))
    pred = by_page(load(parsed_dir / "person_entry.csv"))
    total, matched, lines = 0, 0, []

    for page_id, g_rows in gold.items():
        p_rows = pred.get(page_id, [])
        if len(p_rows) != len(g_rows):
            note = "pred has MORE entries -- gold may be a partial transcription" \
                if len(p_rows) > len(g_rows) else "pred is MISSING entries vs gold"
            lines.append(f"  {page_id}: gold={len(g_rows)} pred={len(p_rows)} ({note})")
        page_total, page_matched = 0, 0
        for g, p in zip(g_rows, p_rows):
            for f in ROSTER_FIELDS:
                gv, pv = g.get(f, "").strip(), p.get(f, "").strip()
                norm = FIELD_NORMALIZERS.get(f, lambda s: s)
                page_total += 1
                if norm(gv) == norm(pv):
                    page_matched += 1
                else:
                    lines.append(f"    [{page_id}/{g.get('family_name','?')}] {f}: gold={gv!r} pred={pv!r}")
        lines.append(f"  {page_id}: {page_matched}/{page_total} fields match "
                      f"(overlapping {min(len(g_rows), len(p_rows))} entries)")
        total += page_total
        matched += page_matched

    return matched, total, lines


def count_lopsided_tenure(parsed_dir: Path) -> int:
    """Rows whose tenure note has a ")" with no "(" before it -- the bracket
    defect norm_tenure() hides from the score, so it is watched here instead."""
    n = 0
    for r in load(parsed_dir / "person_entry.csv"):
        t = r.get("tenure_note_text", "")
        i = t.find(")")
        if i != -1 and "(" not in t[:i]:
            n += 1
    return n


def eval_repertoire(gold_dir: Path, parsed_dir: Path) -> tuple[int, int, list[str]]:
    gold_events = by_page(load(gold_dir / "event_entry.csv"))
    pred_events = by_page(load(parsed_dir / "event_entry.csv"))
    gold_perf, pred_perf = load(gold_dir / "event_entry_performance.csv"), load(parsed_dir / "event_entry_performance.csv")
    gw_by_event, pw_by_event = defaultdict(list), defaultdict(list)
    for w in gold_perf:
        gw_by_event[w["event_id"]].append((w["performance_title"], w["genre"]))
    for w in pred_perf:
        pw_by_event[w["event_id"]].append((w["performance_title"], w["genre"]))

    total, matched, lines = 0, 0, []
    for page_id, g_rows in gold_events.items():
        p_rows = pred_events.get(page_id, [])

        def key(r):
            return (r["date_text"].split()[0], theater_key(r["theater"]), r["time_of_day"])

        g_by_key = {key(r): r for r in g_rows}
        p_by_key = {key(r): r for r in p_rows}
        page_total, page_matched, key_overlap = 0, 0, 0
        for k, g in g_by_key.items():
            p = p_by_key.get(k)
            if p is None:
                continue
            key_overlap += 1
            for f in EVENT_FIELDS:
                page_total += 1
                if g[f].strip() == p[f].strip():
                    page_matched += 1
                else:
                    lines.append(f"    [{page_id}/{k}] {f}: gold={g[f]!r} pred={p[f]!r}")
            gw, pw = gw_by_event.get(g["event_id"], []), pw_by_event.get(p["event_id"], [])
            page_total += 1
            if gw == pw:
                page_matched += 1
            else:
                lines.append(f"    [{page_id}/{k}] works: gold={gw} pred={pw}")
        lines.append(f"  {page_id}: gold_events={len(g_rows)} pred_events={len(p_rows)} "
                      f"key_overlap={key_overlap}/{len(g_by_key)} -> {page_matched}/{page_total} fields match")
        total += page_total
        matched += page_matched

    return matched, total, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--gold-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--run-id", default="", help="optional label recorded in the report header")
    args = ap.parse_args()

    roster_matched, roster_total, roster_lines = eval_roster(args.gold_dir, args.parsed_dir)
    rep_matched, rep_total, rep_lines = eval_repertoire(args.gold_dir, args.parsed_dir)
    total = roster_total + rep_total
    matched = roster_matched + rep_matched

    report = [f"run_id: {args.run_id or '(unlabeled)'}", ""]
    report.append("=== ROSTER ===")
    report += roster_lines
    report.append(f"\nROSTER TOTAL: {roster_matched}/{roster_total} "
                   f"({100*roster_matched/roster_total:.1f}%)" if roster_total else "ROSTER: no gold rows found")
    report.append("\n=== REPERTOIRE ===")
    report += rep_lines
    report.append(f"\nREPERTOIRE TOTAL: {rep_matched}/{rep_total} "
                   f"({100*rep_matched/rep_total:.1f}%)" if rep_total else "REPERTOIRE: no gold rows found")
    report.append(f"\n=== GRAND TOTAL: {matched}/{total} ({100*matched/total:.1f}%) ===")
    lopsided = count_lopsided_tenure(args.parsed_dir)
    report.append(f"\nTenure notes with a closing bracket but no opening one (whole run, "
                  f"not scored above): {lopsided}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(report), encoding="utf-8")

    print(f"roster: {roster_matched}/{roster_total} ({100*roster_matched/roster_total:.1f}%)" if roster_total else "roster: n/a")
    print(f"repertoire: {rep_matched}/{rep_total} ({100*rep_matched/rep_total:.1f}%)" if rep_total else "repertoire: n/a")
    print(f"grand total: {matched}/{total} ({100*matched/total:.1f}%)")
    print(f"tenure notes missing an opening bracket (whole run, not scored): {lopsided}")
    print(f"full report -> {args.out}")


if __name__ == "__main__":
    main()
