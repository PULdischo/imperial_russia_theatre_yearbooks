"""Check Claude's grouped runs for a received дело and build the Reading Room
seed for them.

A *run* is a stretch of neighbouring PDF pages dealing with the same business
(one correspondence, one ledger, one manuscript article ...). RG sorts each run
into Keep piles (ballet / editorial / sales / design, several allowed) or Set
aside, one дело at a time, on the Reading Room's tray. Claude's runs and
suggestions live in docs/rgia/runs/<delo>.json:

    {"delo": 163, "runs": [
        {"start": 1, "end": 3, "title": "...", "dates": "...",
         "piles": ["set_aside"], "why": "...", "unsure": false}, ...]}

RG's decisions (and any split/merge of the boundaries) live only in the
artifact's `run_sorting` collection; Claude never writes there.

    uv run python pipeline/rgia_runs.py --dela 163 [--dela 160 ...]

Checks, all fatal:
  * the runs cover every page of the дело exactly once, in order;
  * piles are from the fixed set; set_aside is never combined with a Keep pile;
  * BALLET SAFETY (RG 2026-11-24, "careful not to miss ballet-related stuff"):
    every page that looks ballet-related -- tagged ballet in the triage, or
    whose summary/names mention ballet, dance, a dancer's school (Театральное
    училище), or name a ballet from docs/rgia/ballet_titles.txt in «...» --
    must sit in a run whose piles include "ballet". Those pages are listed on
    the run card so RG sees each one.

Writes outputs/rgia_reading_room/seed/runs/d<delo>.json for the artifact's
`runs` collection.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIAGE = ROOT / "docs" / "rgia" / "dela"
RUNS = ROOT / "docs" / "rgia" / "runs"
TITLES = ROOT / "docs" / "rgia" / "ballet_titles.txt"
OUT = ROOT / "outputs" / "rgia_reading_room" / "seed" / "runs"
PILES = ("ballet", "editorial", "sales", "design", "set_aside")

KEYWORDS = re.compile(
    r"балет|балерин|танц|хореогр|кордебалет|балетм|Петип|"
    r"театральн\w* училищ|училищ|ballet|danc|choreo|Theatre School|pupil",
    re.I)


def norm(s: str) -> str:
    """Fold pre-reform letters and case so «Коппелія» matches «Коппелия»."""
    s = s.lower().replace("ѣ", "е").replace("і", "и").replace("ѳ", "ф").replace("ѵ", "и").replace("ё", "е")
    return re.sub(r"ъ\b", "", s)


def title_pattern():
    titles = [norm(t.strip()) for t in TITLES.read_text(encoding="utf-8").splitlines()
              if t.strip() and not t.startswith("#")]
    titles = sorted({t for t in titles if len(t) >= 4}, key=len, reverse=True)
    return re.compile(r"«\s*(?:" + "|".join(re.escape(t) for t in titles) + r")", re.I)


def ballet_signal(p: dict, titles_re) -> str:
    """Why a page counts as ballet-related ('' if it does not)."""
    if p.get("ballet"):
        return "tagged ballet"
    text = " ".join([p.get("gist", ""), p.get("why", ""), " ".join(p.get("key_names", []))])
    m = KEYWORDS.search(text)
    if m:
        return f"mentions «{m.group(0)}»"
    m = titles_re.search(norm(text))
    if m:
        return f"names a ballet title ({m.group(0).strip('« ')})"
    return ""


def check(delo: str, titles_re) -> dict:
    pages = {p["page"]: p for p in
             (json.loads(l) for l in (TRIAGE / f"{delo}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    spec = json.loads((RUNS / f"{delo}.json").read_text(encoding="utf-8"))
    runs, errors, expect = spec["runs"], [], 1
    for r in runs:
        if r["start"] != expect:
            errors.append(f"run {r['start']}-{r['end']}: expected to start at p. {expect}")
        if r["end"] < r["start"]:
            errors.append(f"run {r['start']}-{r['end']}: ends before it starts")
        expect = r["end"] + 1
        bad = set(r["piles"]) - set(PILES)
        if bad or not r["piles"]:
            errors.append(f"run {r['start']}-{r['end']}: bad piles {r['piles']}")
        if "set_aside" in r["piles"] and len(r["piles"]) > 1:
            errors.append(f"run {r['start']}-{r['end']}: set_aside combined with a Keep pile")
        bp = []
        for n in range(r["start"], r["end"] + 1):
            if n not in pages:
                continue
            why = ballet_signal(pages[n], titles_re)
            if why:
                bp.append({"page": n, "signal": why})
        r["ballet_pages"] = bp
        r["n_pages"] = r["end"] - r["start"] + 1
        r["n_high"] = sum(pages.get(n, {}).get("relevance") == "high" for n in range(r["start"], r["end"] + 1))
        r["n_editorial"] = sum(bool(pages.get(n, {}).get("editorial")) for n in range(r["start"], r["end"] + 1))
        if bp and "ballet" not in r["piles"]:
            errors.append(f"BALLET SAFETY: run {r['start']}-{r['end']} has ballet-related pages "
                          f"{[b['page'] for b in bp]} but is not in the ballet pile")
    last = max(pages)
    if expect != last + 1:
        errors.append(f"runs end at p. {expect - 1}, but the дело has {last} pages")
    if errors:
        raise SystemExit(f"Д. {delo}:\n  " + "\n  ".join(errors))
    return {"delo": int(delo), "runs": runs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dela", action="append", required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    titles_re = title_pattern()
    for d in a.dela:
        doc = check(d, titles_re)
        (OUT / f"d{d}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        nb = sum(len(r["ballet_pages"]) for r in doc["runs"])
        print(f"Д. {d}: {len(doc['runs'])} runs, {nb} ballet-related pages, all in ballet runs -> {OUT / f'd{d}.json'}")
        for r in doc["runs"]:
            flag = " [unsure]" if r.get("unsure") else ""
            print(f"  pp. {r['start']}-{r['end']:<4} {'+'.join(r['piles']):<24} ballet pp. {[b['page'] for b in r['ballet_pages']] or '-'}{flag}  {r['title'][:70]}")


if __name__ == "__main__":
    main()
