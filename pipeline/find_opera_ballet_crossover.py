"""Find where ballet and opera meet, in the season reviews and against the Repertoire.

RG, 2026-10-07: *"Confirming that these types of opera-ballet mixes are vitally
important to my research!"* This is the systematic version of that search. The
first nine instances were found by accident -- they were the residue of a
mention-matcher run that happened to flag seven opera composers -- so they
undercounted badly and missed an entire category (the season-level mixed-bill
tallies). This script replaces that accident with a sweep.

Three outputs, because the phenomenon shows up in three different shapes:

**1. Crossover passages** in the ballet reviews. Two traps here, both found the
hard way. First, the stored text keeps the printed line breaks, so a word split
across one arrives as `сопер- никамъ` or `спек- такля`; any pattern spanning a
break silently fails, and an early version of this script matched several
categories only by luck. `reflow()` joins those before matching, the same way
`build_bilingual.reflow` does. Second, the stem `опер` collides hard in this
corpus -- with `соперникъ`/`соперница` (rival, very common in ballet synopses),
with `Фебъ де Шатоперъ` (Phoebus de Chateaupers in Esmeralda), with `Поперекъ`
and `поперемѣнно`. Those are suppressed by DROP below. A second
class of hit is real but off-topic: `оперная труппа` passages listing singer
transfers, which appear in ballet reviews only because the same printed page was
scanned into both PDFs (the shared-page bleed, docs/season_reviews.md). Those
are tagged `roster_bleed` rather than dropped, so the suppression stays visible.

**2. The mixed-bill series.** Several ballet reviews open by counting the
season's performances, including how many were `смѣшанные спектакли` shared with
opera. That is a season-level number from narrative prose, and the Repertoire
tables can be made to produce the same number independently. They agree exactly
on eight of the nine seasons where the review states a ballet+opera count --
1891-92 SP 4, 1892-93 SP 11, 1893-94 Moscow 2, 1894-95 Moscow 2, 1894-95 SP 4,
1895-96 Moscow 13, 1896-97 Moscow 4, 1897-98 Moscow 3. Two independent
pipelines over two different source formats landing on the same counts is the
strongest corroboration either layer has.

The ninth is 1893-94 SP, and the shortfall is informative rather than a defect.
The review there reports `балетъ и опера--2` plus one four-way bill of
`балетъ, русская драма, опера и французская драма`, so three bills involve
opera; the database finds two. The missing one is the Greek earthquake benefit
at the Mikhailovsky, 29 April 1894, which the Repertoire records as
`Жены + Le petit Hôtel + Концертное отдѣленіе + 1-е и 2-е д. бал. Коппелія`.
The opera troupe is inside `Концертное отдѣленіе`, an entry that names no works,
so no genre test can ever see it. That is output 3.

This comparison is printed with the review's own sentence verbatim beside the
database count, deliberately not parsed into a number. Prose like
`4--вмѣстѣ съ русской драмой и 4 -- вмѣстѣ съ оперой` is exactly where an
automatic reading goes wrong quietly, and a wrong count here would look like a
data error in one of the two layers.

**3. The unnamed-programme worklist.** 128 events carry a programme entry whose
content the Repertoire does not name -- `Дивертиссементъ` (82 occurrences, in 19 of the
21 seasons the database holds), `Концертное отдѣленіе`, `Концертъ`. The reviews often itemize
exactly these, with the numbers, the composers and the casts, and it is inside
those itemizations that the opera-derived dance numbers live. Date + theatre
joins the two. This is where the reviews carry what the tables structurally
cannot.

Usage:
    uv run python pipeline/find_opera_ballet_crossover.py \
        --reviews-dir outputs/reviews/merged_full \
        --db outputs/full_run/imperial_theaters.duckdb \
        --out outputs/reviews/opera_ballet_crossover.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

csv.field_size_limit(10_000_000)

# Collisions with the stem `опер` that are not about opera at all.
DROP = re.compile(r"сопер(н|ник|ниц)|шатопер|поперек|поперём|поперем|оперш", re.I)

# Ordered: the first pattern that matches classifies the passage.
CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("dances_staged_in_opera", re.compile(
        r"танц\w*\s+(въ|для)\s+опер|поставлен\w*\s+вновь\s+танц|"
        r"въ\s+опер[ѣе]\s+въ\s+\d|крестьянскій\s+танецъ", re.I)),
    ("opera_music_for_dance", re.compile(
        r"(танц\w*|гопакъ|вальсъ|пляска)\s+изъ\s+опер|изъ\s+опер\w*\s*[«\"„]", re.I)),
    ("dancer_appeared_in_opera", re.compile(
        r"(выступал\w*|появ\w*|исполн\w*|дебютировал\w*|танцовал\w*)"
        r"[^.;]{0,200}въ\s+(королевской\s+)?опер[ѣе]", re.I)),
    ("shared_production_resources", re.compile(
        r"декорац\w*[^.]{0,120}(для\s+опер|изъ\s+опер)|"
        r"воспользовал\w*[^.]{0,120}опер", re.I)),
    ("mixed_bill", re.compile(
        r"смѣшанн\w*\s+спектакл|спектакл\w*\s+смѣшанн|"
        r"совмѣстн\w*\s+(съ\s+оперой|представлені)|"
        r"(вмѣстѣ|совмѣстно)\s+съ\s+оперой|"
        r"въ\s+одинъ\s+спектакль\s+съ[^.;]{0,60}опер|"
        r"(состоявшій|состоялъ|состояли)[^;]{0,160}опер|"
        r"въ\s+(составъ|программу)[^;]{0,160}опер|"
        r"балет\w*,?\s+(русская\s+драма,\s+)?опера|"
        r"балет\w*(\s+«[^»]{0,60}»)?\s+и\s+опера", re.I)),
    ("opera_excerpt_on_ballet_bill", re.compile(
        r"(\d+-я\s+картина|картина)[^;]{0,60}опер|"
        r"\d+-(го|е)\s+дѣйствіе?я?[^;]{0,40}опер|опернаго\s+отрывка", re.I)),
    ("gala_or_benefit_programme", re.compile(
        r"(въ\s+пользу|въ\s+память|бенефисъ)[^.]{0,400}опер|"
        r"(актъ|дѣйствіе|прологъ|увертюра)\s[^.]{0,60}опер", re.I)),
    ("season_closed_with_opera", re.compile(
        r"(сезонъ\s+(закончился|закрылся)|закончился\s+сезонъ|"
        r"послѣдній\s+спектакль)[^;]{0,120}опер", re.I)),
    ("opera_influence_noted", re.compile(
        r"реминисценц\w*[^.]{0,80}опер|мотив\w*[^.]{0,60}опер", re.I)),
    ("foreign_opera_house_credential", re.compile(
        r"(артистк?и?|танцовщица|балерин\w*)[^;]{0,60}"
        r"(парижской|берлинской|королевской|вѣнской|миланской)[^;]{0,30}опер|"
        r"(парижской|берлинской|королевской)\s+опер", re.I)),
    ("roster_bleed", re.compile(
        r"оперн\w*\s+труп|труппу?[^.]{0,30}оперн", re.I)),
    # labelled, not dropped, so the suppression stays auditable
    ("narrative_comparison", re.compile(
        r"(продажи|кассой|абонемент|барышник|публик\w*)[^;]{0,200}опер", re.I)),
]

STEM = re.compile(r"опер", re.I)
SEP = re.compile(r"\s+")

# Programme entries the Repertoire records without naming their content.
OPAQUE = (r"концертн|дивертиссемент|дивертисмент|divertissement|концерт")


HYPHEN = re.compile(r"([^\s-])-\s+")
WINDOW = 260


def reflow(text: str) -> str:
    """Join words the printed line break split, then collapse whitespace.

    Without this, `сопер- никамъ` and `спек- такля` defeat every pattern that
    spans the break -- silently, since a non-match looks identical to an absent
    phenomenon.
    """
    return SEP.sub(" ", HYPHEN.sub(r"\1", text)).strip()


def windows(text: str) -> list[str]:
    """Merged +/-WINDOW character windows around each `опер`, as passages.

    A window rather than a sentence because the prose is dense with abbreviations
    (`бал.`, `муз.`, `г-жа`, `1-го д.`) that no cheap sentence splitter survives,
    and because a season tally puts its subject well before the match.
    """
    spans: list[list[int]] = []
    for m in STEM.finditer(text):
        lo, hi = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
        if spans and lo <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], hi)
        else:
            spans.append([lo, hi])
    return [text[lo:hi].strip() for lo, hi in spans]


def all_stems_are_collisions(passage: str) -> bool:
    """True when every `опер` in the passage sits inside a collision word.

    Testing "does a collision word appear" is not enough, and testing it only
    when no category matched is worse: the Bayadere scenery list names a scene
    `Двѣ соперницы`, which carries the stem, inside a passage whose other words
    (`картина`, `дѣйствіе`) look exactly like an opera excerpt. The question has
    to be asked per occurrence.
    """
    drops = [m.span() for m in DROP.finditer(passage)]
    hits = list(STEM.finditer(passage))
    if not hits:
        return True
    return all(any(lo <= h.start() and h.end() <= hi for lo, hi in drops)
               for h in hits)


def classify(passage: str) -> str | None:
    if all_stems_are_collisions(passage):
        return None
    for name, pat in CATEGORIES:
        if pat.search(passage):
            return name
    return "unclassified"


def sweep_reviews(reviews_dir: Path, genre: str) -> list[dict]:
    with open(reviews_dir / "review_page.csv", encoding="utf-8") as f:
        pages = {r["page_id"]: r for r in csv.DictReader(f)}
    found = []
    with open(reviews_dir / "review_block.csv", encoding="utf-8") as f:
        for b in csv.DictReader(f):
            page = pages.get(b["page_id"])
            if not page or (genre and page.get("genre") != genre):
                continue
            text = reflow(b["text"] or b["caption_text"] or "")
            if not STEM.search(text):
                continue
            for sent in windows(text):
                if not STEM.search(sent):
                    continue
                kind = classify(sent)
                if kind is None:
                    continue
                found.append({
                    "season": page["season"], "city": page["city"],
                    "genre": page["genre"], "page_id": b["page_id"],
                    "block_id": b["block_id"], "category": kind,
                    "passage": sent.strip(),
                })
    return found


TALLY = re.compile(r"(въ\s+теченіе\s+сезона|балетныхъ\s+спектакл|"
                   r"спектаклей\s+было\s+дано|балетны\w*\s+(спектакл|представлен))", re.I)


def stated_tallies(rows: list[dict]) -> dict[tuple[str, str], str]:
    """The season-level tally sentence, kept VERBATIM.

    Deliberately not parsed into a number: the prose distinguishes bills shared
    with opera from bills shared with drama in the same breath
    (`4--вмѣстѣ съ русской драмой и 4 -- вмѣстѣ съ оперой`), and a misparse
    would masquerade as a discrepancy between the two layers.
    """
    out: dict[tuple[str, str], str] = {}
    for r in rows:
        if r["category"] != "mixed_bill" or not TALLY.search(r["passage"]):
            continue
        out.setdefault((r["season"], r["city"]), r["passage"])
    return out


MIXED_SQL = """
with pw as (
  select e.season, e.city, e.event_id,
    (w.parent_genre = 'ballet'
       or regexp_matches(lower(coalesce(w.canonical_genre,'')), '^(бал|ballet)')) as is_bal,
    (coalesce(w.parent_genre,'') <> 'ballet'
       and regexp_matches(lower(coalesce(p.verbatim_genre, w.canonical_genre, '')),
                          '^(оп\\.|опера|опер|op\\.|opera|opéra|оп$)')) as is_op
  from research.event e
  join research.performance p on p.event_id = e.event_id
  join research.work w on w.work_id = p.work_id),
ev as (select season, city, event_id, bool_or(is_bal) b, bool_or(is_op) o
       from pw group by 1,2,3)
select season, city, count(*) as db_mixed_bills
from ev where b and o group by 1,2 order by 1,2
"""

OPAQUE_SQL = f"""
select e.season, e.city, e.date_undate, t.canonical_name as theater,
       e.receipts_total_kopecks,
       string_agg(p.verbatim_title, ' + ' order by p.performance_order) as programme
from research.event e
join research.theater t on t.theater_id = e.theater_id
join research.performance p on p.event_id = e.event_id
where e.event_id in (select event_id from research.performance
                     where regexp_matches(lower(verbatim_title), '{OPAQUE}'))
group by 1,2,3,4,5 order by e.season, e.date_undate
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-dir", required=True, type=Path)
    ap.add_argument("--db", type=Path, default=None,
                    help="omit to skip the Repertoire cross-check")
    ap.add_argument("--genre", default="Ballet",
                    help="review genre to sweep; '' for all")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    rows = sweep_reviews(a.reviews_dir, a.genre)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["season", "city", "genre", "page_id",
                                          "block_id", "category", "passage"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["category"], r["season"], r["city"])))

    import collections
    tally = collections.Counter(r["category"] for r in rows)
    SUPPRESSED = ("roster_bleed", "narrative_comparison", "unclassified")
    substantive = sum(n for k, n in tally.items() if k not in SUPPRESSED)
    print(f"{len(rows)} passages in {a.genre or 'all'} reviews -> {a.out}")
    print(f"{substantive} substantive; the rest is labelled noise "
          f"({', '.join(SUPPRESSED)})\n")
    for k, n in tally.most_common():
        print(f"  {k:30s} {n:4d}")

    if not a.db:
        return
    import duckdb
    con = duckdb.connect(str(a.db), read_only=True)

    print("\n--- mixed bills: what the reviews state vs. what the Repertoire holds ---")
    db = {(r[0], r[1]): r[2] for r in con.execute(MIXED_SQL).fetchall()}
    stated = stated_tallies(rows)
    print("    (the review sentence is verbatim -- read the two, do not assume)")
    for key in sorted(set(db) | set(stated)):
        said = stated.get(key, "")
        print(f"\n  {key[0]} {key[1]:7s} repertoire ballet+opera bills = {db.get(key, 0)}")
        if said:
            trimmed = re.sub(r"\s+", " ", said)
            start = max(0, trimmed.lower().find("въ теченіе"))
            print(f"      review: {trimmed[start:start + 300]}")

    opaque = con.execute(OPAQUE_SQL).fetchall()
    print(f"\n--- {len(opaque)} events whose programme includes an unnamed entry ---")
    print("    (Дивертиссементъ / Концертное отдѣленіе / Концертъ -- the reviews")
    print("     itemize many of these; join on season + city + date + theater)")
    side = a.out.with_name(a.out.stem + "_unnamed_programme.csv")
    with open(side, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season", "city", "date_undate", "theater",
                    "receipts_total_kopecks", "programme"])
        w.writerows(opaque)
    print(f"    -> {side}")


if __name__ == "__main__":
    main()
