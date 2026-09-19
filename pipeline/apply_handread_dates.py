"""Re-merges a page's ALREADY-EXTRACTED theater columns against a hand-
transcribed date sequence, for the severe date-undercount cases
(docs/eval/known_issues.md #70's addendum, 2026-09-15): a date-only call
that gets stuck reading ~3 rows regardless of resampling, on a page whose
theater columns extracted fine. No new model calls -- the theater data
already sitting in <raw-dir>/<page_id>.columns.json is reused as-is; only
the date sequence is replaced, straight from a scan read.

Input format (--dates, a JSON file): {page_id: [{"index": 1,
"date_text": "...", "session": "unspecified"}, ...]}, one entry per page.
`index` is 1-based, top to bottom, in the ORDER the hand-read rows were
transcribed -- it does not need to align with any model-internal
indexing, because merge_columnwise_page's own reconciliation (row-count
+ compound-day arithmetic) is what actually pairs a date to a theater
row, exactly as it does for every other page in this corpus. If the
hand-read count doesn't reconcile against a theater's own row count,
that theater is refused (reported unresolved), never guessed at -- the
same safety behavior as the rest of this pipeline."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import merge_columnwise_page  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, required=True,
                     help="existing raw-dir with <page_id>.columns.json (theater data reused)")
    ap.add_argument("--dates", type=Path, required=True,
                     help="JSON file: {page_id: [{index, date_text, session}, ...]}")
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    hand_dates = json.loads(args.dates.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for page_id, date_rows in hand_dates.items():
        cf = args.raw_dir / f"{page_id}.columns.json"
        if not cf.exists():
            print(f"  {page_id}: SKIPPED -- no columns.json in {args.raw_dir}")
            continue
        old = json.loads(cf.read_text(encoding="utf-8"))
        raw = old["raw"]
        theaters = raw["theaters"]

        all_sessions, merge_report, n_ok = [], [], 0
        for theater_name, theater_rows in theaters.items():
            merged = merge_columnwise_page(date_rows, theater_name, theater_rows)
            all_sessions.extend(merged.sessions)
            n_ok += merged.ok
            merge_report.append({
                "theater": theater_name, "model_said": None, "ok": merged.ok,
                "n_sessions": len(merged.sessions), "unresolved": merged.unresolved,
                "n_date_days": merged.n_date_days, "n_theater_rows": merged.n_theater_rows,
                "reason": merged.reason,
            })

        (args.out_dir / f"{page_id}.raw.json").write_text(
            json.dumps({"sessions": all_sessions}, ensure_ascii=False), encoding="utf-8")
        new_raw = {**raw, "date_rows": date_rows, "date_attempts": "hand-read",
                   "date_all_attempts": None, "date_plausible": True}
        (args.out_dir / f"{page_id}.columns.json").write_text(
            json.dumps({"merge": merge_report, "raw": new_raw}, ensure_ascii=False),
            encoding="utf-8")
        print(f"  {page_id}: {n_ok}/{len(theaters)} theaters reconciled, "
              f"{len(all_sessions)} sessions ({len(date_rows)} hand-read date rows)")


if __name__ == "__main__":
    main()
