"""Stage 5f (optional, additive): links entities.person records to Wikidata
items where a confident match exists. Purely additive -- never touches
raw/analysis, never rewrites a person's own name fields, same
non-destructive philosophy as the rest of `entities`. Not part of
build_entities.py's rebuild cycle: this is a separate, slower, external-API
script you run deliberately, and entities.person_wikidata_link is created
with CREATE TABLE IF NOT EXISTS so reruns are additive (already-linked
people are skipped, not re-queried).

Wikidata's read API (wbsearchentities) is fully public, no auth needed --
see https://www.wikidata.org/wiki/Wikidata:MCP for the interactive-agent
version of this same data; this script hits the same underlying API
directly for a systematic batch job instead.

Scope: this project's roster spans thousands of administrative/rank-and-file
staff who will almost never have a Wikidata entry. Rather than query
everyone, --pilot restricts to people whose printed role (rank_or_title /
heading_path) suggests real historical notability (ballet masters,
kapellmeisters/conductors, ballerinas, directors, designers, composers,
soloists) -- confirmed against the real data to surface genuine hits (e.g.
violinist Leopold Auer) rather than mostly-empty searches.

Confidence policy (deliberately conservative -- a wrong Wikidata link is a
visible, citable error for a researcher): auto-accept only when there is
exactly one search result, its label/alias exactly matches the modernized
search name, its description names a theater/music/dance-related
occupation, AND if the description gives birth/death years, they don't
contradict the person's own attested season range. Anything else (zero
results, multiple candidates, or a single candidate missing/contradicting
that evidence) goes to a CSV for human review, not into the entities table.

Usage:
    python pipeline/link_wikidata.py --db outputs/full_run/imperial_theaters.duckdb \
        --pilot --export-review-queue outputs/full_run/wikidata_review_queue.csv
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import duckdb

from build_entities import NAMESPACE, _ensure_person_merge_log, _log_decided_candidates, reconcile_person_merges

USER_AGENT = "ImperialTheaterYearbooksResearch/1.0 (research project; contact: aj7878@princeton.edu)"
WD_API = "https://www.wikidata.org/w/api.php"
REQUEST_DELAY_SECONDS = 0.4  # polite pacing against a free public API, not a rate-limit requirement

# Notable-role keywords, matched against raw.person_entry.heading_path /
# rank_or_title -- confirmed against the real data (964 distinct active
# people match at least one of these, out of ~3,275 total) rather than
# assumed. This is a recall-oriented filter for --pilot, not a precision
# one: it's fine to include some people who turn out to have no Wikidata
# entry, since a zero-result search just gets skipped.
NOTABLE_ROLE_KEYWORDS = [
    "Солист", "Директор", "Художни", "Композитор",
    "Балетмейстер", "Капельмейстер", "Балерин", "Управляющ",
]

# Pre-1918 -> modern Russian orthography, for Wikidata search only --
# entities.person's own canonical_* fields keep the real printed spelling
# (build_entities.py's _VOWEL_FOLD does the same fold for a different
# purpose: Tier 1/2 name-matching keys).
_VOWEL_FOLD = {"ѣ": "е", "і": "и", "ѳ": "ф", "ѵ": "и"}

_OCCUPATION_KEYWORDS = [
    # Russian
    "балет", "танцовщ", "артист", "актёр", "актер", "певец", "певица",
    "дирижёр", "дирижер", "композитор", "хореограф", "музыкант", "оперн",
    "театр", "скрипач", "пианист",
    # English (Wikidata often falls back to an English description when no
    # Russian one exists, as with Leopold Auer -- confirmed live)
    "ballet", "dancer", "actor", "actress", "singer", "conductor",
    "composer", "choreographer", "musician", "opera", "theatre", "theater",
    "violin", "cello", "pianist", "playwright", "designer",
]

_YEAR_RANGE_RE = re.compile(r"\((\d{4})[–\-](\d{4})?\)")


def _modernize(name: str | None) -> str:
    if not name:
        return ""
    t = name
    for old, new in _VOWEL_FOLD.items():
        t = t.replace(old, new).replace(old.upper(), new.upper())
    t = re.sub(r"[ъЪ]\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _season_year(season: str | None) -> int | None:
    if not season:
        return None
    m = re.match(r"^(\d{4})", season)
    return int(m.group(1)) if m else None


def _wd_search(name: str) -> list[dict]:
    params = {
        "action": "wbsearchentities", "search": name, "language": "ru",
        "type": "item", "limit": 5, "format": "json",
    }
    url = WD_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8")).get("search", [])
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def select_pilot_persons(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    cond = " OR ".join(
        f"r.heading_path ILIKE '%{kw}%' OR r.rank_or_title ILIKE '%{kw}%'"
        for kw in NOTABLE_ROLE_KEYWORDS
    )
    return con.execute(f"""
        SELECT DISTINCT p.person_id, p.display_name, p.canonical_family_name,
               p.canonical_first_name, p.canonical_patronymic,
               p.first_attested_season, p.last_attested_season
        FROM raw.person_entry r
        JOIN entities.person_link pl ON pl.entry_id = r.entry_id
        JOIN entities.person p ON p.person_id = pl.person_id
        WHERE p.superseded_by_person_id IS NULL AND ({cond})
        ORDER BY p.display_name
    """).fetchall()


def _extract_years(description: str) -> tuple[int | None, int | None]:
    m = _YEAR_RANGE_RE.search(description or "")
    if not m:
        return None, None
    birth = int(m.group(1))
    death = int(m.group(2)) if m.group(2) else None
    return birth, death


def _dates_plausible(birth: int | None, death: int | None,
                      first_season: str | None, last_season: str | None) -> bool:
    first_year, last_year = _season_year(first_season), _season_year(last_season)
    if birth is not None and first_year is not None and birth > first_year:
        return False  # can't have been employed before being born
    if death is not None and first_year is not None and death < first_year:
        return False  # can't have been employed after dying
    return True


def link_persons(con: duckdb.DuckDBPyConnection, persons: list[tuple]) -> tuple[list[dict], list[dict]]:
    """Returns (auto_accepted, needs_review) lists of dicts."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities.person_wikidata_link (
            person_id UUID PRIMARY KEY,
            wikidata_qid VARCHAR,
            wikidata_label VARCHAR,
            wikidata_description VARCHAR,
            match_evidence VARCHAR
        )
    """)
    already_linked = {
        str(r[0]) for r in con.execute("SELECT person_id FROM entities.person_wikidata_link").fetchall()
    }

    auto_accepted, needs_review = [], []
    for i, (person_id, display_name, fam, first, pat, first_season, last_season) in enumerate(persons, 1):
        person_id = str(person_id)
        if person_id in already_linked:
            continue

        modern_fam = _modernize(re.sub(r"\s+\d+-(?:й|я)\.?$", "", fam or ""))
        modern_first, modern_pat = _modernize(first), _modernize(pat)
        search_name = " ".join(p for p in (modern_first, modern_pat, modern_fam) if p)
        if not search_name:
            continue

        try:
            results = _wd_search(search_name)
        except Exception as e:
            print(f"  [{i}/{len(persons)}] {display_name}: search failed ({e}), skipping")
            continue
        time.sleep(REQUEST_DELAY_SECONDS)

        if not results:
            continue

        if len(results) > 1:
            needs_review.append({
                "person_id": person_id, "display_name": display_name,
                "reason": "multiple_candidates",
                "candidates": [(r["id"], r.get("label", ""), r.get("description", "")) for r in results],
            })
            continue

        r = results[0]
        qid, label, description = r["id"], r.get("label", ""), r.get("description", "")
        match_text = (r.get("match", {}) or {}).get("text", "")
        exact_label_match = match_text.strip().lower() == search_name.strip().lower()
        has_occupation = any(kw in description.lower() for kw in _OCCUPATION_KEYWORDS)
        birth, death = _extract_years(description)
        dates_ok = _dates_plausible(birth, death, first_season, last_season)

        if exact_label_match and has_occupation and dates_ok:
            auto_accepted.append({
                "person_id": person_id, "display_name": display_name,
                "wikidata_qid": qid, "wikidata_label": label, "wikidata_description": description,
                "match_evidence": f"exact name match, occupation-consistent description"
                                  + (f", dates ({birth}-{death or '?'}) consistent" if birth else ""),
            })
        else:
            reason = []
            if not exact_label_match:
                reason.append("label_not_exact")
            if not has_occupation:
                reason.append("no_occupation_signal")
            if not dates_ok:
                reason.append("dates_contradict")
            needs_review.append({
                "person_id": person_id, "display_name": display_name,
                "reason": ",".join(reason),
                "candidates": [(qid, label, description)],
            })

        if i % 50 == 0:
            print(f"  ...{i}/{len(persons)} processed "
                  f"({len(auto_accepted)} auto-accepted so far)")

    if auto_accepted:
        con.executemany(
            "INSERT INTO entities.person_wikidata_link VALUES (?, ?, ?, ?, ?)",
            [(a["person_id"], a["wikidata_qid"], a["wikidata_label"],
              a["wikidata_description"], a["match_evidence"]) for a in auto_accepted],
        )

    return auto_accepted, needs_review


def export_review_queue(needs_review: list[dict], out_path: Path) -> None:
    import csv as csv_module

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_module.writer(f)
        w.writerow(["person_id", "display_name", "reason", "candidate_qid", "candidate_label",
                    "candidate_description", "decision (QID or No)"])
        for row in needs_review:
            for qid, label, desc in row["candidates"]:
                w.writerow([row["person_id"], row["display_name"], row["reason"], qid, label, desc, ""])
    print(f"{len(needs_review)} people needing review -> {out_path} (utf-8-sig, ready for Sheets/Excel import)")


def merge_shared_wikidata_qids(con: duckdb.DuckDBPyConnection) -> int:
    """Two different entities.person records that both resolved to the same
    Wikidata QID is independent evidence they're the same real person --
    seen in the real data specifically for the ordinal-suffix split case
    (the printed '1-й' disambiguator only appears in years there was an
    actual homonym in print to disambiguate from, so the same real person
    can land in two different Tier 1 clusters across different yearbooks).
    Recorded as its own entities.person_candidate status
    ('confirmed_wikidata') and merged through the same
    reconcile_person_merges() machinery as tenure merges -- same
    non-destructive guarantee (superseded_by_person_id, never deletion),
    same union-find handling if a QID is ever shared by more than two
    records. Safe to call repeatedly: skips any pair already recorded
    (candidate_id is deterministic, same uuid5 scheme as
    build_person_tier2_candidates)."""
    _ensure_person_merge_log(con)
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities.person_candidate (
            candidate_id UUID PRIMARY KEY,
            person_id_1 UUID, person_id_2 UUID,
            display_1 VARCHAR, display_2 VARCHAR, similarity_score DOUBLE,
            match_reason VARCHAR, status VARCHAR, tenure_signal VARCHAR, tenure_evidence VARCHAR
        )
    """)

    groups = con.execute("""
        SELECT wikidata_qid, list(person_id) AS person_ids, min(wikidata_label) AS label
        FROM entities.person_wikidata_link
        GROUP BY wikidata_qid HAVING count(*) > 1
    """).fetchall()
    display = dict(con.execute("SELECT person_id, display_name FROM entities.person").fetchall())
    display = {str(k): v for k, v in display.items()}

    n_pairs = 0
    for qid, person_ids, label in groups:
        person_ids = [str(p) for p in person_ids]
        anchor = person_ids[0]
        for other in person_ids[1:]:
            id1, id2 = (anchor, other) if anchor < other else (other, anchor)
            candidate_id = str(uuid.uuid5(NAMESPACE, f"person_candidate:{id1}|{id2}"))
            if con.execute("SELECT 1 FROM entities.person_candidate WHERE candidate_id = ?",
                            [candidate_id]).fetchone():
                continue
            con.execute("""
                INSERT INTO entities.person_candidate VALUES
                    (?, ?, ?, ?, ?, NULL, ?, 'confirmed_wikidata', NULL, ?)
            """, [candidate_id, id1, id2, display.get(id1, ""), display.get(id2, ""),
                  "wikidata_qid_match", f"both linked to Wikidata {qid} ({label})"])
            n_pairs += 1

    if n_pairs:
        _log_decided_candidates(con)
    print(f"entities.person_candidate: {n_pairs} pair(s) confirmed via a shared Wikidata QID")
    return reconcile_person_merges(con)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--pilot", action="store_true",
                     help="restrict to notable-role people (see NOTABLE_ROLE_KEYWORDS) instead of everyone")
    ap.add_argument("--export-review-queue", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None, help="cap the number of people processed (for testing)")
    ap.add_argument("--merge-shared-qids", action="store_true",
                     help="merge entities.person records that resolved to the same Wikidata QID, then exit "
                          "(no searching) -- run this after a linking pass, not instead of one")
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS entities")

    if args.merge_shared_qids:
        merge_shared_wikidata_qids(con)
        con.close()
        return

    if not args.pilot:
        raise SystemExit("Only --pilot is implemented so far; full-corpus linking needs a separate go-ahead.")

    persons = select_pilot_persons(con)
    if args.limit:
        persons = persons[: args.limit]
    print(f"pilot pool: {len(persons)} notable-role people")

    auto_accepted, needs_review = link_persons(con, persons)

    print(f"\n{len(auto_accepted)} auto-accepted (written to entities.person_wikidata_link)")
    for a in auto_accepted[:10]:
        print(f"  {a['display_name']} -> {a['wikidata_qid']} ({a['wikidata_label']}: {a['wikidata_description']})")
    if len(auto_accepted) > 10:
        print(f"  ... and {len(auto_accepted) - 10} more")

    if args.export_review_queue:
        export_review_queue(needs_review, args.export_review_queue)

    con.close()


if __name__ == "__main__":
    main()
