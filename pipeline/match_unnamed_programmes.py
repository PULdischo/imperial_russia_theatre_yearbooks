#!/usr/bin/env python3
"""Find the review passage that itemizes a Repertoire event's unnamed programme.

The Repertoire tabulates date, theatre and receipts but prints the
programme item as a bare "Дивертиссементъ" / "Концертное отдѣленіе" --
128 events corpus-wide. The season reviews narrate the same evenings in
prose and very often DO itemize them, cast and all
(docs/eval/ballet_in_opera_and_divertissement.md). Neither layer is
recoverable from the other and the join key -- season, city, date -- is
exact.

Dates in the reviews are printed Julian, as "21-го ноября" or "21 ноября",
sometimes with the year attached. `date_undate` is already Julian (it is
VARCHAR project-wide precisely because 29 Feb 1900 exists in Julian and
`datetime.date` rejects it), so the day and month are taken as printed
with no conversion.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import duckdb

csv.field_size_limit(10 ** 9)

MONTHS_GEN = {
    1: ["января", "янв"], 2: ["февраля", "февр"], 3: ["марта", "мар"],
    4: ["апрѣля", "апреля", "апр"], 5: ["мая"], 6: ["іюня", "июня"],
    7: ["іюля", "июля"], 8: ["августа", "авг"], 9: ["сентября", "сент"],
    10: ["октября", "окт"], 11: ["ноября", "нояб"], 12: ["декабря", "дек"],
}


#: A run of days sharing one month name: "2-го, 5-го и 9-го сентября".
#: Matching only the day immediately before the month misses the first two,
#: and this is the reviews' normal way of listing the performances of a
#: production -- measured, it is where most of the recoverable dates live.
DAY = r"\d{1,2}\s*(?:-\s*(?:го|ro|тго))?"
DATE_RUN = re.compile(
    rf"(?<!\d)(?P<days>{DAY}(?:\s*(?:,|и|&)\s*{DAY})*)\s+"
    rf"(?P<month>января|янв|февраля|февр|марта|мар|апрѣля|апреля|апр|мая|"
    rf"іюня|июня|іюля|июля|августа|авг|сентября|сент|октября|окт|"
    rf"ноября|нояб|декабря|дек)", re.IGNORECASE)


def iter_dates(text: str):
    """Yield (day, month_number, match) for every date the prose prints."""
    for m in DATE_RUN.finditer(text):
        name = m.group("month").lower()
        month = next((num for num, names in MONTHS_GEN.items()
                      if any(name == n for n in names)), None)
        if month is None:
            continue
        for d in re.findall(r"\d{1,2}", m.group("days")):
            yield int(d), month, m


def reflow(text: str) -> str:
    """Rejoin words the printed line break split, then flatten newlines.

    Done BEFORE any date or title matching: the review text keeps printed
    lineation, so "21-го но-\\nября" is three tokens on the page and one
    date in the prose. (Compound hyphens that are genuinely part of a word
    are kept -- the trap recorded on 2026-10-07.)
    """
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", text or "")
    return re.sub(r"\s*\n\s*", " ", t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--events", required=True,
                    help="opera_ballet_crossover_unnamed_programme.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", type=int, default=900,
                    help="characters of context to carry either side of the date")
    a = ap.parse_args()

    con = duckdb.connect(a.db, read_only=True)
    blocks = con.execute("""
        SELECT b.block_id, p.season, p.city, p.genre, b.page_id, b.block_index,
               coalesce(b.text, b.caption_text) AS text
        FROM raw.review_block b JOIN raw.review_page p USING (page_id)
        WHERE coalesce(b.text, b.caption_text) <> ''
        ORDER BY b.page_id, b.block_index
    """).fetchall()
    # season+city -> list of (block_id, page_id, reflowed text)
    by_sc: dict[tuple, list] = {}
    for bid, season, city, genre, pid, bidx, text in blocks:
        by_sc.setdefault((season, city), []).append((bid, pid, genre, reflow(text)))

    events = list(csv.DictReader(open(a.events, encoding="utf-8")))
    out = []
    for e in events:
        y, m, d = (int(x) for x in e["date_undate"].split("-"))
        hits, seen = [], set()
        for bid, pid, genre, text in by_sc.get((e["season"], e["city"]), []):
            for day, month, mt in iter_dates(text):
                if (day, month) != (d, m) or (bid, mt.start()) in seen:
                    continue
                seen.add((bid, mt.start()))
                lo = max(0, mt.start() - a.window // 3)
                hi = min(len(text), mt.end() + a.window)
                hits.append((pid, bid, genre, text[lo:hi]))
        out.append({**e, "n_review_hits": len(hits),
                    "review_genre": "|".join(sorted({h[2] for h in hits})),
                    "review_pages": "|".join(sorted({h[0] for h in hits})),
                    "passage": "\n~~~\n".join(h[3] for h in hits[:3])})

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    found = sum(1 for r in out if r["n_review_hits"])
    print(f"{len(out)} unnamed-programme events")
    print(f"  with >=1 review passage on the same season/city/date: {found} "
          f"({100*found/len(out):.0f}%)")
    print(f"  no review passage found                             : {len(out)-found}")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
