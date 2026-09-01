"""Fold the multi-pass raw responses from rgia_opis_batch.py into one table,
with a per-entry confidence signal derived from how far the passes disagree.

Why disagreement and not the model's own flag: on the 127 dpi opis scans
qwen3-vl-plus set `uncertain` on 0 of 57 pilot entries while getting roughly
half the titles substantively wrong. Independent passes, by contrast, diverge
exactly where the reading is shaky -- so cross-pass agreement is the usable
confidence measure. Free to re-run; never calls the API.

Outputs (into <run-dir>):
    opis_all_entries.csv    every entry, with agreement columns
    opis_in_range.csv       only entries whose dates touch --range, or undated
    opis_page_summary.csv   per-page entry counts, drift and agreement flags

Usage:
    python pipeline/rgia_opis_consolidate.py --run-dir outputs/rgia_full \
        --range 1890-1916
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rgia_opis_extract import OpisPage, in_range

PASS_LABEL = {1: "native", 2: "2x", 3: "1.5x"}


def norm(s) -> str:
    if not s:
        return ""
    s = str(s).lower().replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b) -> float:
    a, b = norm(a), norm(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def key_of(entry: dict) -> str:
    """Align entries across passes on the running file number."""
    v = entry.get("poryadkovy_nomer")
    digits = re.sub(r"\D", "", str(v or ""))
    return digits or ""


def band(x: float) -> str:
    if x >= 0.98:
        return "identical"
    if x >= 0.90:
        return "high"
    if x >= 0.70:
        return "medium"
    return "low"


def load_passes(run_dir: Path, img_no: int) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for f in sorted((run_dir / "raw").glob(f"img{img_no:03d}.pass*.raw.json")):
        n = int(re.search(r"pass(\d+)", f.name).group(1))
        text = f.read_text(encoding="utf-8").strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:])
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
        try:
            page = OpisPage.model_validate(json.loads(text))
        except Exception as e:
            print(f"  img{img_no:03d} pass{n}: unparseable ({e})", file=sys.stderr)
            continue
        out[n] = [e.model_dump() for e in page.entries]
    return out


def consolidate_page(img_no: int, passes: dict[int, list[dict]], lo: int, hi: int):
    by_key: dict[str, dict[int, dict]] = defaultdict(dict)
    for pno, entries in passes.items():
        for e in entries:
            k = key_of(e)
            if k and pno not in by_key[k]:      # keep first occurrence per pass
                by_key[k][pno] = e

    n_pass = len(passes)
    counts = {p: len(v) for p, v in passes.items()}
    drift = len(set(counts.values())) > 1

    rows = []
    for k in sorted(by_key, key=lambda x: int(x) if x.isdigit() else 0):
        variants = by_key[k]
        titles = {p: (e.get("title_ru") or "") for p, e in variants.items()}
        pids = sorted(titles)

        if len(pids) > 1:
            pairs = [sim(titles[a], titles[b])
                     for i, a in enumerate(pids) for b in pids[i + 1:]]
            min_sim, mean_sim = min(pairs), sum(pairs) / len(pairs)
            # medoid: the reading closest to the others
            best = max(pids, key=lambda p: sum(sim(titles[p], titles[q])
                                               for q in pids if q != p))
        else:
            min_sim = mean_sim = 0.0
            best = pids[0]

        chosen = variants[best]

        # a low-agreement entry may just be number drift: does this reading
        # appear at a DIFFERENT number in another pass?
        shift_hint = ""
        if min_sim < 0.70 and len(pids) > 1:
            for p, entries in passes.items():
                if p == best:
                    continue
                for e in entries:
                    if key_of(e) != k and sim(e.get("title_ru"), titles[best]) >= 0.85:
                        shift_hint = f"matches #{key_of(e)} in pass{p}"
                        break
                if shift_hint:
                    break

        def vote(field):
            vals = [variants[p].get(field) for p in pids if variants[p].get(field) is not None]
            return Counter(vals).most_common(1)[0][0] if vals else None

        ys, ye = vote("year_start"), vote("year_end")
        dates_agree = len({(variants[p].get("year_start"), variants[p].get("year_end"))
                           for p in pids}) == 1

        row = {
            "image": img_no,
            "list": img_no - 2,
            "poryadkovy_nomer": chosen.get("poryadkovy_nomer"),
            "superseded_nomer": chosen.get("superseded_nomer"),
            "side": chosen.get("side"),
            "title_ru": chosen.get("title_ru"),
            "title_en": chosen.get("title_en"),
            "dates_raw": chosen.get("dates_raw"),
            "year_start": ys,
            "year_end": ye,
            "listov": chosen.get("listov"),
            "passes_present": f"{len(pids)}/{n_pass}",
            "title_agreement": band(min_sim) if len(pids) > 1 else "single_pass",
            "agreement_score": round(min_sim, 3) if len(pids) > 1 else "",
            "dates_agree": "yes" if dates_agree else "no",
            "number_drift_on_page": "yes" if drift else "no",
            "shift_hint": shift_hint,
            "chosen_from": PASS_LABEL.get(best, f"pass{best}"),
            "variants_ru": " ||| ".join(titles[p] for p in pids if p != best),
        }
        row["in_research_range"] = in_range({"year_start": ys, "year_end": ye}, lo, hi)
        # The work queue: in-period entries whose reading is not settled. NOTE the
        # chosen title is the MEDOID -- the most typical of the passes, which is
        # not the most correct one when two passes share an error (obs.: #398 chose
        # "Список партий" over the correct "Список портных"). For anything below
        # `identical`, variants_ru is the authoritative column, not title_ru.
        row["review_priority"] = (
            "verify" if row["in_research_range"] in ("yes", "unknown")
            and row["title_agreement"] != "identical" else "")
        rows.append(row)

    summary = {
        "image": img_no, "list": img_no - 2,
        "passes_parsed": n_pass,
        "entries_per_pass": "/".join(str(counts[p]) for p in sorted(counts)),
        "number_drift": "yes" if drift else "no",
        "entries": len(rows),
        "low_agreement": sum(1 for r in rows if r["title_agreement"] == "low"),
        "in_range": sum(1 for r in rows if r["in_research_range"] == "yes"),
    }
    return rows, summary


def write_csv(rows, path: Path, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=Path("outputs/rgia_full"))
    ap.add_argument("--range", default="1890-1916")
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.range.split("-"))

    imgs = sorted({int(re.search(r"img(\d+)", f.name).group(1))
                   for f in (args.run_dir / "raw").glob("img*.raw.json")})
    all_rows, summaries = [], []
    for n in imgs:
        passes = load_passes(args.run_dir, n)
        if not passes:
            continue
        rows, summary = consolidate_page(n, passes, lo, hi)
        all_rows.extend(rows)
        summaries.append(summary)

    cols = ["image", "list", "poryadkovy_nomer", "superseded_nomer", "side",
            "title_ru", "title_en", "dates_raw", "year_start", "year_end", "listov",
            "in_research_range", "title_agreement", "agreement_score", "dates_agree",
            "review_priority", "passes_present", "number_drift_on_page", "shift_hint",
            "chosen_from", "variants_ru"]
    write_csv(all_rows, args.run_dir / "opis_all_entries.csv", cols)
    in_r = [r for r in all_rows if r["in_research_range"] in ("yes", "unknown")]
    write_csv(in_r, args.run_dir / "opis_in_range.csv", cols)
    write_csv(summaries, args.run_dir / "opis_page_summary.csv", list(summaries[0]) if summaries else [])

    tot = len(all_rows)
    print(f"pages consolidated : {len(summaries)}")
    print(f"entries total      : {tot}")
    print(f"  in {lo}-{hi}      : {sum(1 for r in all_rows if r['in_research_range']=='yes')}")
    print(f"  undated          : {sum(1 for r in all_rows if r['in_research_range']=='unknown')}")
    print(f"  out of range     : {sum(1 for r in all_rows if r['in_research_range']=='no')}")
    if tot:
        for b in ("identical", "high", "medium", "low", "single_pass"):
            c = sum(1 for r in all_rows if r["title_agreement"] == b)
            print(f"  agreement {b:<11}: {c:>5} ({100*c/tot:.1f}%)")
        print(f"  dates agree      : {sum(1 for r in all_rows if r['dates_agree']=='yes')} "
              f"/ {tot}")
        print(f"  NEEDS EYES ON    : {sum(1 for r in all_rows if r['review_priority']=='verify')}"
              f"  (in-period, reading unsettled)")
        print(f"  pages w/ drift   : {sum(1 for s in summaries if s['number_drift']=='yes')}")
    print(f"\n-> {args.run_dir}/opis_all_entries.csv, opis_in_range.csv, opis_page_summary.csv")


if __name__ == "__main__":
    main()
