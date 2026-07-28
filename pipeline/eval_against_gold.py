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
from collections import defaultdict
from pathlib import Path
import csv

ROSTER_FIELDS = ["family_name", "first_name", "patronymic", "heading_path", "rank_or_title",
                  "tenure_note_text", "instrument", "service_class", "subject_taught"]
SESSION_FIELDS = ["city", "session_status", "session"]
KNOWN_THEATERS = ["Маріинскій", "Александринскій", "Михайловскій", "Большой", "Малый", "Новый"]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


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
    gold = by_page(load(gold_dir / "roster_entry.csv"))
    pred = by_page(load(parsed_dir / "roster_entry.csv"))
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
                page_total += 1
                if gv == pv:
                    page_matched += 1
                else:
                    lines.append(f"    [{page_id}/{g.get('family_name','?')}] {f}: gold={gv!r} pred={pv!r}")
        lines.append(f"  {page_id}: {page_matched}/{page_total} fields match "
                      f"(overlapping {min(len(g_rows), len(p_rows))} entries)")
        total += page_total
        matched += page_matched

    return matched, total, lines


def eval_repertoire(gold_dir: Path, parsed_dir: Path) -> tuple[int, int, list[str]]:
    gold_sess = by_page(load(gold_dir / "performance_session.csv"))
    pred_sess = by_page(load(parsed_dir / "performance_session.csv"))
    gold_work, pred_work = load(gold_dir / "performance_work.csv"), load(parsed_dir / "performance_work.csv")
    gw_by_session, pw_by_session = defaultdict(list), defaultdict(list)
    for w in gold_work:
        gw_by_session[w["session_id"]].append((w["work_title"], w["genre"]))
    for w in pred_work:
        pw_by_session[w["session_id"]].append((w["work_title"], w["genre"]))

    total, matched, lines = 0, 0, []
    for page_id, g_rows in gold_sess.items():
        p_rows = pred_sess.get(page_id, [])

        def key(r):
            return (r["date_text"].split()[0], theater_key(r["theater"]), r["session"])

        g_by_key = {key(r): r for r in g_rows}
        p_by_key = {key(r): r for r in p_rows}
        page_total, page_matched, key_overlap = 0, 0, 0
        for k, g in g_by_key.items():
            p = p_by_key.get(k)
            if p is None:
                continue
            key_overlap += 1
            for f in SESSION_FIELDS:
                page_total += 1
                if g[f].strip() == p[f].strip():
                    page_matched += 1
                else:
                    lines.append(f"    [{page_id}/{k}] {f}: gold={g[f]!r} pred={p[f]!r}")
            gw, pw = gw_by_session.get(g["session_id"], []), pw_by_session.get(p["session_id"], [])
            page_total += 1
            if gw == pw:
                page_matched += 1
            else:
                lines.append(f"    [{page_id}/{k}] works: gold={gw} pred={pw}")
        lines.append(f"  {page_id}: gold_sessions={len(g_rows)} pred_sessions={len(p_rows)} "
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

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(report), encoding="utf-8")

    print(f"roster: {roster_matched}/{roster_total} ({100*roster_matched/roster_total:.1f}%)" if roster_total else "roster: n/a")
    print(f"repertoire: {rep_matched}/{rep_total} ({100*rep_matched/rep_total:.1f}%)" if rep_total else "repertoire: n/a")
    print(f"grand total: {matched}/{total} ({100*matched/total:.1f}%)")
    print(f"full report -> {args.out}")


if __name__ == "__main__":
    main()
