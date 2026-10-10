#!/usr/bin/env python3
"""People the ballet reviews name whom the spiski do not carry.

The signal is a *gender contradiction*: the review prints `г-жа
Галактіонова` and the only Галактіонов- in the database is the man
`Галактіоновъ`. Where the family is one Russian actually inflects
(-овъ/-ова, -скій/-ская), that is strong evidence of a real person the
rosters omit -- typically a corps dancer, which is itself a finding, since
the spiski are supposed to list the company.

Regenerated rather than hand-maintained: the first version of this
worklist was written by hand and had gone stale by 2026-10-10 --
Воскресенская had started three seasons earlier than recorded, Шульгина
spanned four seasons rather than one, and Лядова had five occurrences
across twelve years and two cities instead of one. Verdicts, notes and
scan_checked are carried over from the previous CSV by name; every
factual column is rebuilt from the database.
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from match_review_mentions import canon_gender, key_of   # noqa: E402

csv.field_size_limit(10 ** 9)

FEM_HON = re.compile(r"(?:г-жа|г-жи|г-жею|г-же|восп-ца|уч-ца|в-ца|балерин\w*|танцовщиц\w*)\s*$",
                     re.IGNORECASE)
MASC_HON = re.compile(r"(?:г\.|гг\.|г-нъ|г-да|восп-къ|уч-къ|в-къ|танцовщикъ)\s*$",
                      re.IGNORECASE)


#: Gendered ending -> the shared stem it reduces to. NORMALISING, not
#: stripping: cutting the whole suffix off would fold "Лопухина" and
#: "Лопухова" onto one key ("лопух") and they are different families. Each
#: pair keeps its stem-forming consonant.
_FAMILY_NORM = [
    ("ская", "ск"), ("цкая", "цк"), ("ский", "ск"), ("цкий", "цк"),
    ("скии", "ск"), ("цкии", "цк"), ("ской", "ск"), ("цкой", "цк"),
    ("ова", "ов"), ("ева", "ев"), ("ина", "ин"), ("ына", "ын"),
]


#: "Воронина 1-я", "Громовъ 1-й", "Лядова 2-я" -- the ordinal distinguishes
#: same-surname colleagues and is not part of the family name, so it comes
#: off before stemming or the stem carries it and never matches.
_ORDINAL = re.compile(r"\s*\d+\s*-?\s*[ейя]?\s*$")


def family_stem(folded: str) -> str:
    """Key on which a family's masculine and feminine forms coincide.

    `Галактіонова` and `Галактіоновъ` -> `галактионов`; `Барковская` and
    `Барковскій` -> `барковск`; `Лопухина` -> `лопухин`, which stays apart
    from `Лопухова` -> `лопухов`.
    """
    folded = _ORDINAL.sub("", folded).strip()
    for suf, stem in _FAMILY_NORM:
        if folded.endswith(suf) and len(folded) - len(suf) >= 3:
            return folded[: -len(suf)] + stem
    return folded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--previous", default="docs/eval/review_people_not_in_rosters.csv")
    ap.add_argument("--genre", default="Ballet")
    a = ap.parse_args()

    con = duckdb.connect(a.db, read_only=True)

    # every family the database already knows, by gender-stripped stem
    db_fam: dict[str, set[str]] = collections.defaultdict(set)
    db_people: dict[str, list[str]] = collections.defaultdict(list)
    for fam, disp, first, last in con.execute("""
            SELECT canonical_family_name, display_name,
                   first_attested_season, last_attested_season
            FROM research.person WHERE canonical_family_name IS NOT NULL""").fetchall():
        st = family_stem(key_of(fam))
        db_fam[st].add(canon_gender(fam) or "?")
        db_people[st].append(f"{disp} ({first}-{last})")

    rows = con.execute("""
        SELECT m.surface, m.season, m.city, m.page_id, m.block_id,
               m.char_start, m.char_end, b.text, b.caption_text
        FROM entities.review_mention m
        JOIN raw.review_block b USING (block_id)
        JOIN raw.review_page p ON p.page_id = m.page_id
        WHERE m.mention_type = 'person' AND m.entity_id IS NULL
          AND p.genre = ?
        ORDER BY m.page_id, m.char_start
    """, [a.genre]).fetchall()

    agg: dict[str, dict] = {}
    for surf, season, city, pid, bid, cs, ce, text, cap in rows:
        body = text or cap or ""
        before = body[max(0, cs - 14):cs]
        # The contradiction runs BOTH ways: "г-жа Галактіонова" against a
        # database holding only Галактіоновъ, and "г. Кусковъ" against a
        # database holding only Кускова. A one-directional test dropped 10
        # of the previous worklist's names.
        # canon_gender reads the ENDING, so the ordinal has to come off
        # first or "Громовъ 1-й" reads as no evidence at all.
        bare = _ORDINAL.sub("", surf).strip()
        g = ("f" if FEM_HON.search(before) else
             "m" if MASC_HON.search(before) else canon_gender(bare))
        if g not in ("f", "m"):
            continue
        st = family_stem(key_of(surf))
        # A contradiction needs BOTH sides gender-marked. `Гельцеръ`,
        # `Чекетти`, `Петипа`, `Іогансонъ`, `Кякштъ` are indeclinable, so
        # canon_gender returns None for the database side and "unknown" is
        # not "the other gender" -- treating it as one flagged 74 mentions
        # of Гельцеръ, who is of course in the rosters.
        if st not in db_fam or "?" in db_fam[st] or g in db_fam[st]:
            continue
        e = agg.setdefault(surf, {"n": 0, "sc": collections.Counter(),
                                  "pages": set(), "ctx": "", "g": g})
        e["n"] += 1
        e["sc"][(season, city)] += 1
        e["pages"].add(pid)
        if not e["ctx"]:
            e["ctx"] = re.sub(r"\s+", " ", body[max(0, cs - 95):ce + 95])
        e["same"] = "; ".join(sorted(db_people[st])[:3])

    prev = {}
    pp = Path(a.previous)
    if pp.exists():
        prev = {r["printed_in_review"]: r for r in csv.DictReader(open(pp, encoding="utf-8"))}

    out = []
    for surf, e in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
        old = prev.get(surf, {})
        out.append({
            "verdict": old.get("verdict", "") or "UNCLASSIFIED - new since the last run",
            "printed_in_review": surf,
            "review_gender": e["g"],
            "occurrences": e["n"],
            "seasons": " ".join(sorted({s for s, _ in e["sc"]})),
            "season_city": "; ".join(f"{s} {c}x{n}" for (s, c), n in sorted(e["sc"].items())),
            "pages": "|".join(sorted(e["pages"])),
            "scan_checked": old.get("scan_checked", ""),
            "same_family_in_db": e.get("same", ""),
            "note": old.get("note", ""),
            "context": e["ctx"],
        })
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)

    carried = sum(1 for r in out if not r["verdict"].startswith("UNCLASSIFIED"))
    print(f"{len(out)} name(s) -> {a.out}")
    print(f"  verdict carried over from the previous CSV : {carried}")
    print(f"  new since the last run, unclassified       : {len(out)-carried}")
    gone = sorted(set(prev) - set(agg))
    if gone:
        print(f"  in the previous CSV but NO LONGER flagged  : {len(gone)}")
        for g in gone:
            print(f"      {g!r}  (was: {prev[g]['verdict']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
