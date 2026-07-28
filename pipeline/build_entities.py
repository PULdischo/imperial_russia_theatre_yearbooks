"""Stage 5d: build the `entities` schema -- the resolved, deduplicated
research layer described in docs/research_dataset.md. A third schema
alongside `raw` and `analysis`, additive only, never touching either.

Entities are built incrementally, one function per entity type, in
increasing order of difficulty (see docs/research_dataset.md): theater
(hand-seeded, ~solved already by analysis.performance_session's
theater_canonical), work (canonicalized title+genre), person (staged,
confidence-scored matching -- the hard one, built last and separately).

Usage:
    python pipeline/build_entities.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
import re
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

# Fixed namespace for this project's deterministic (uuid5) entity IDs --
# Theater and Work only (see docs/research_dataset.md's "two UUID
# strategies" section for why Person can't use this approach).
NAMESPACE = uuid.UUID("c6f6b1a0-6b1a-4b1a-9b1a-6b1a4b1a9b1a")

# (canonical_name, city, active_from_season) -- matches the theater_roster
# logic already in build_duckdb.py's completeness reconciliation. Hand-
# seeded, not inferred: a fixed 6-row table, same reasoning as
# THEATER_CITY in schemas/repertoire.py.
THEATERS = [
    ("Маріинскій", "SP", None),
    ("Александринскій", "SP", None),
    ("Михайловскій", "SP", None),
    ("Большой", "Moscow", None),
    ("Малый", "Moscow", None),
    ("Новый", "Moscow", "1898-99"),
]


def build_theater(con: duckdb.DuckDBPyConnection) -> None:
    rows = [
        (str(uuid.uuid5(NAMESPACE, f"theater:{name}")), name, city, active_from)
        for name, city, active_from in THEATERS
    ]
    con.execute("""
        CREATE OR REPLACE TABLE entities.theater (
            theater_id UUID PRIMARY KEY,
            canonical_name VARCHAR,
            city VARCHAR,
            active_from_season VARCHAR
        )
    """)
    con.executemany("INSERT INTO entities.theater VALUES (?, ?, ?, ?)", rows)
    print(f"entities.theater: {len(rows)} rows (hand-seeded)")

    # Sanity check: every theater_canonical value in analysis.performance_session
    # should resolve to exactly one entities.theater row. If this ever prints
    # a mismatch, the corpus has introduced a venue THEATERS doesn't know
    # about yet (e.g. a 7th theater in a later season) and this table needs
    # a manual update, not a code fix.
    unmatched = con.execute("""
        SELECT DISTINCT a.theater_canonical
        FROM analysis.performance_session a
        LEFT JOIN entities.theater t ON t.canonical_name = a.theater_canonical
        WHERE a.theater_canonical IS NOT NULL AND t.theater_id IS NULL
    """).fetchall()
    if unmatched:
        print(f"  WARNING: {len(unmatched)} theater_canonical value(s) with no entities.theater match: "
              f"{[u[0] for u in unmatched]}")
    else:
        print("  all theater_canonical values resolve to an entities.theater row")


_TRIM_PUNCT = " .,;:!?\"«»"
# Folding pre-reform vowel variants for MATCHING only -- canonical_title
# still stores a real verbatim spelling (the most common one seen), never
# a modernized form. Same principle as theater_canonical.
_VOWEL_FOLD = {"ѣ": "е", "і": "и", "ѳ": "ф"}  # ѣ->е, і->и, ѳ->ф


def _title_key(title: str) -> str:
    t = title.strip(_TRIM_PUNCT)
    t = re.sub(r"\s+", " ", t).lower()
    for old, new in _VOWEL_FOLD.items():
        t = t.replace(old, new)
    return t


def _genre_key(genre: str | None) -> str:
    # Genre is NOT lowercased or vowel-folded: it's frequently a different
    # language entirely (French/German works keep French/German genre
    # abbreviations, e.g. "com."/"Lustsp."), not just an orthography
    # variant of the same word -- collapsing case here would blur real
    # language-of-performance distinctions, not fix noise.
    if genre is None:
        return ""
    return re.sub(r"\s+", " ", genre.strip())


def build_work(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute("""
        SELECT work_id, work_title, genre FROM raw.performance_work
        WHERE work_title IS NOT NULL AND trim(work_title) <> ''
    """).fetchall()

    groups: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for work_id, title, genre in rows:
        key = (_title_key(title), _genre_key(genre))
        groups.setdefault(key, []).append((work_id, title, genre))

    work_rows, link_rows = [], []
    n_multi_variant = 0
    for (title_key, genre_key), members in groups.items():
        work_uuid = str(uuid.uuid5(NAMESPACE, f"work:{title_key}|{genre_key}"))
        # Canonical display form = most common verbatim (title, genre) pair
        # actually printed in this group, not a normalized/modernized one.
        variant_counts: dict[tuple[str, str], int] = {}
        for _, title, genre in members:
            variant_counts[(title, genre)] = variant_counts.get((title, genre), 0) + 1
        if len(variant_counts) > 1:
            n_multi_variant += 1
        (canonical_title, canonical_genre), _ = max(variant_counts.items(), key=lambda kv: kv[1])
        work_rows.append((work_uuid, canonical_title, canonical_genre, len(members)))
        for work_id, _, _ in members:
            link_rows.append((work_id, work_uuid))

    # Drop the dependent table first -- entities.work_link's FK reference
    # blocks CREATE OR REPLACE on entities.work otherwise, which would
    # silently break re-running this script a second time.
    con.execute("DROP TABLE IF EXISTS entities.work_link")
    con.execute("""
        CREATE OR REPLACE TABLE entities.work (
            work_id UUID PRIMARY KEY,
            canonical_title VARCHAR,
            canonical_genre VARCHAR,
            appearance_count INTEGER
        )
    """)
    con.executemany("INSERT INTO entities.work VALUES (?, ?, ?, ?)", work_rows)

    con.execute("""
        CREATE TABLE entities.work_link (
            raw_work_id VARCHAR PRIMARY KEY,
            work_id UUID REFERENCES entities.work(work_id)
        )
    """)
    con.executemany("INSERT INTO entities.work_link VALUES (?, ?)", link_rows)

    n_excluded = con.execute(
        "SELECT count(*) FROM raw.performance_work WHERE work_title IS NULL OR trim(work_title) = ''"
    ).fetchone()[0]
    print(f"entities.work: {len(work_rows)} resolved works from {len(rows)} raw appearances "
          f"({n_excluded} excluded: blank work_title, see known_issues.md)")
    print(f"  {n_multi_variant} works were printed under more than one raw spelling variant "
          f"and collapsed into one entity by canonicalization")


# Matches the printed homonym-disambiguating suffix ("Петровъ 2-й",
# "Алексѣева 1-я") -- confirmed against the real data (336/2,569 distinct
# family_name values match this exact shape: a space, digit(s), hyphen,
# "й" or "я"). Kept as its own field rather than folded into the name key,
# specifically so two different real people sharing a surname are never
# merged just because one appearance happened to drop the suffix.
_ORDINAL_RE = re.compile(r"^(.*?)\s+(\d+-(?:й|я))\.?\s*$")


def _split_ordinal(family_name: str) -> tuple[str, str | None]:
    m = _ORDINAL_RE.match(family_name.strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return family_name.strip(), None


# The ordinal usually trails family_name ("Вальтеръ 2-й"), but the model
# sometimes puts it ALONE in first_name instead -- confirmed against real
# data: 101/20,528 first_name values are exactly this shape and nothing
# else, which shifts the real first name (and patronymic, if printed) one
# field over into what's stored as `patronymic`
# ("family=Вальтеръ, first=1-й, patronymic=Викторъ Григорьевичъ"). But not
# every such row is safely recoverable this way: some really are a
# cross-reference note instead of a name at all
# ("family=Тарнке, first=1-й, patronymic=(см. оперный оркестръ)" -- "see
# the orchestra listing") -- attempting to split that into first/patronymic
# would fabricate a name from a "see also" pointer. _NAME_SHAPE guards
# against exactly that: only reinterpret patronymic as the shifted name
# when it actually looks like one (1-2 capitalized Cyrillic words, no
# parentheses/abbreviation punctuation) -- anything else is left alone,
# same "don't guess" discipline as everywhere else in this pipeline.
_BARE_ORDINAL_RE = re.compile(r"^\d+-(?:й|я)\.?$")
_NAME_SHAPE_RE = re.compile(
    r"^[А-ЯЁІѢѲѴ][а-яёіѣѳѵ\-]+(?:\s+[А-ЯЁІѢѲѴ][а-яёіѣѳѵ\-]+)?$"
)


def _extract_ordinal(
    family_name: str, first_name: str | None, patronymic: str | None
) -> tuple[str, str | None, str | None, str | None]:
    base, ordinal = _split_ordinal(family_name)
    clean_first, clean_patronymic = first_name, patronymic
    if not ordinal and first_name and _BARE_ORDINAL_RE.match(first_name.strip()):
        if patronymic and _NAME_SHAPE_RE.match(patronymic.strip()):
            ordinal = first_name.strip().rstrip(".")
            parts = patronymic.strip().split()
            clean_first, clean_patronymic = parts[0], (parts[1] if len(parts) > 1 else None)
        # else: patronymic doesn't look like a name (a cross-reference note,
        # e.g. "(см. ...)") -- leave the row exactly as printed, unresolved
        # ordinal and all, rather than fabricate a split from a non-name value.
    return base, ordinal, clean_first, clean_patronymic


def _name_key(text: str | None) -> str:
    # Blank/missing is its own equivalence class, not a wildcard -- a row
    # missing a patronymic only matches another row ALSO missing one,
    # never one that has it filled in. Conservative on purpose: this is
    # the auto-accept tier, a missed merge is far cheaper than a wrong one.
    if not text:
        return ""
    t = text.strip().lower()
    for old, new in _VOWEL_FOLD.items():
        t = t.replace(old, new)
    return re.sub(r"\s+", " ", t)


def _table_exists(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    return bool(con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
        [schema, table],
    ).fetchone())


def _snapshot_person_candidate_status(con: duckdb.DuckDBPyConnection) -> dict[tuple[str, str], str]:
    """Must be called before build_person_tier1 runs -- Tier 1 drops
    entities.person_candidate (its FK into entities.person would otherwise
    block CREATE OR REPLACE TABLE person on a second run), which would
    silently discard every human review decision on each re-run if they
    weren't captured first."""
    if not _table_exists(con, "entities", "person_candidate"):
        return {}
    # Cast to str explicitly -- DuckDB returns UUID columns as uuid.UUID
    # objects, but build_person_tier2_candidates keys its lookup on the str()
    # forms already used everywhere else in this module. A type mismatch
    # here would make every lookup silently miss and fall back to
    # "pending", discarding every human review decision on each re-run.
    return {
        (str(a), str(b)): status for a, b, status in
        con.execute("SELECT person_id_1, person_id_2, status FROM entities.person_candidate").fetchall()
    }


def build_person_tier1(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute("""
        SELECT r.entry_id, r.family_name, r.first_name, r.patronymic, p.season
        FROM raw.roster_entry r
        JOIN raw.source_pages p ON p.page_id = r.page_id
        WHERE r.family_name IS NOT NULL AND trim(r.family_name) <> ''
    """).fetchall()

    # Incremental registry: a person's UUID must survive across re-runs
    # (docs/research_dataset.md's "person can't be uuid5'd from name text"
    # rationale) -- reuse an existing tier1_key -> person_id mapping if the
    # registry already exists, only minting new UUIDs for genuinely new keys.
    existing: dict[str, str] = {}
    # A confirmed Tier 2 merge (apply_person_merges) sets superseded_by on a
    # specific person_id -- CREATE OR REPLACE would otherwise wipe that back
    # to NULL on every re-run, silently un-doing every past merge decision.
    existing_superseded: dict[str, str] = {}
    if _table_exists(con, "entities", "person"):
        # str() the person_id explicitly -- DuckDB returns UUID columns as
        # uuid.UUID objects, and every other lookup keyed on person_id in
        # this module (existing_superseded, person_candidate, etc.) uses
        # str() consistently. A UUID-vs-str mismatch here means
        # existing_superseded.get(person_id) below silently misses on every
        # lookup -- exactly the bug that just wiped every past merge.
        existing = {
            tier1_key: str(person_id) for tier1_key, person_id in con.execute(
                "SELECT tier1_key, person_id FROM entities.person WHERE tier1_key IS NOT NULL"
            ).fetchall()
        }
        existing_superseded = {
            str(person_id): str(superseded_by) for person_id, superseded_by in con.execute(
                "SELECT person_id, superseded_by_person_id FROM entities.person "
                "WHERE superseded_by_person_id IS NOT NULL"
            ).fetchall()
        }

    clusters: dict[str, list[tuple[str, str, str, str, str]]] = defaultdict(list)
    n_ordinal_recovered = 0
    for entry_id, family_name, first_name, patronymic, season in rows:
        base, ordinal, clean_first, clean_patronymic = _extract_ordinal(family_name, first_name, patronymic)
        if clean_first != first_name or clean_patronymic != patronymic:
            n_ordinal_recovered += 1
        tier1_key = "|".join(
            [_name_key(base), ordinal or "", _name_key(clean_first), _name_key(clean_patronymic)]
        )
        clusters[tier1_key].append((entry_id, family_name, first_name, patronymic, season))

    person_rows, link_rows = [], []
    n_multi = 0
    for tier1_key, members in clusters.items():
        person_id = existing.get(tier1_key) or str(uuid.uuid4())
        if len(members) > 1:
            n_multi += 1
        # Canonical display uses the corrected (base, ordinal, clean_first)
        # triple consistently -- so the canonical family/first name is
        # always the same shape regardless of which raw appearance the
        # ordinal happened to land on.
        corrected_variants = []
        for _, family_name, first_name, patronymic, _ in members:
            base, ordinal, clean_first, clean_patronymic = _extract_ordinal(family_name, first_name, patronymic)
            corrected_variants.append((base, ordinal, clean_first, clean_patronymic))
        variant_counts = Counter(corrected_variants)
        (base, ordinal, first_name, patronymic), _ = variant_counts.most_common(1)[0]
        seasons = sorted({m[4] for m in members if m[4]})
        display_name = base + (f" {ordinal}" if ordinal else "")
        name_parts = [p for p in (first_name, patronymic) if p]
        if name_parts:
            display_name += ", " + " ".join(name_parts)
        person_rows.append((
            person_id, display_name, base, first_name, patronymic, ordinal,
            seasons[0] if seasons else None, seasons[-1] if seasons else None,
            tier1_key, existing_superseded.get(person_id),
        ))
        for entry_id, *_ in members:
            link_rows.append((entry_id, person_id, "exact_normalized", 1.0))

    # Same drop-dependent-first fix as build_work -- any table with an FK
    # into person (person_link, and person_candidate once Tier 2 has run)
    # would otherwise block CREATE OR REPLACE on person on a second run.
    con.execute("DROP TABLE IF EXISTS entities.person_link")
    con.execute("DROP TABLE IF EXISTS entities.person_candidate")
    con.execute("""
        CREATE OR REPLACE TABLE entities.person (
            person_id UUID PRIMARY KEY,
            display_name VARCHAR,
            canonical_family_name VARCHAR,
            canonical_first_name VARCHAR,
            canonical_patronymic VARCHAR,
            ordinal_suffix VARCHAR,
            first_attested_season VARCHAR,
            last_attested_season VARCHAR,
            tier1_key VARCHAR,
            superseded_by_person_id UUID
        )
    """)
    con.executemany("INSERT INTO entities.person VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", person_rows)

    con.execute("""
        CREATE TABLE entities.person_link (
            entry_id VARCHAR PRIMARY KEY,
            person_id UUID REFERENCES entities.person(person_id),
            match_method VARCHAR,
            match_confidence DOUBLE
        )
    """)
    con.executemany("INSERT INTO entities.person_link VALUES (?, ?, ?, ?)", link_rows)

    n_excluded = con.execute(
        "SELECT count(*) FROM raw.roster_entry WHERE family_name IS NULL OR trim(family_name) = ''"
    ).fetchone()[0]
    print(f"entities.person (Tier 1): {len(person_rows)} resolved people from {len(rows)} roster appearances "
          f"({n_excluded} excluded: blank family_name)")
    print(f"  {n_multi} people matched by exact normalized name across more than one appearance")
    print(f"  {n_ordinal_recovered} appearances had their ordinal suffix recovered from first_name "
          f"instead of family_name")


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


# Small typo-scale edits only (1-2 characters) -- this is meant to catch
# spelling slips like Григорьевичъ/Тригорьевичъ, not surface loosely
# similar-but-different names. Every candidate here still requires the
# OTHER two of the three name components (see the two blocking strategies
# below) to match exactly first, so this threshold only has to discriminate
# within an already narrow, plausible set -- it doesn't have to do the
# whole job alone.
MAX_EDIT_DISTANCE = 2


def build_person_tier2_candidates(
    con: duckdb.DuckDBPyConnection, existing_status: dict[tuple[str, str], str]
) -> None:
    persons = con.execute("""
        SELECT person_id, display_name, tier1_key FROM entities.person
        WHERE superseded_by_person_id IS NULL AND tier1_key IS NOT NULL
    """).fetchall()

    parsed = []
    for person_id, display_name, tier1_key in persons:
        fam, ordinal, first, pat = tier1_key.split("|")
        parsed.append((str(person_id), display_name, fam, ordinal, first, pat))

    # Two targeted blocking strategies, not one loose fuzzy pass over all
    # ~3,900 people (a full O(n^2) compare would surface far too much noise
    # for a human reviewer to work through). Each blocks on 2 of the 3 name
    # components matching EXACTLY, and only fuzzy-compares the third --
    # narrows candidates to pairs already plausible on 2/3 of the name,
    # same discipline as requiring ordinal_suffix to match exactly in Tier 1.
    by_fam_first_ord: dict[tuple, list] = defaultdict(list)   # -> compare patronymic
    by_first_pat_ord: dict[tuple, list] = defaultdict(list)   # -> compare family name
    for p in parsed:
        _, _, fam, ordinal, first, pat = p
        by_fam_first_ord[(fam, first, ordinal)].append(p)
        by_first_pat_ord[(first, pat, ordinal)].append(p)

    candidates: dict[tuple[str, str], tuple[float, str]] = {}

    def consider(p1, p2, field_idx: int, reason: str) -> None:
        id1, id2 = p1[0], p2[0]
        if id1 == id2:
            return
        dist = _levenshtein(p1[field_idx], p2[field_idx])
        if 0 < dist <= MAX_EDIT_DISTANCE:
            key = (id1, id2) if id1 < id2 else (id2, id1)
            score = 1 - dist / max(len(p1[field_idx]), len(p2[field_idx]), 1)
            if key not in candidates or score > candidates[key][0]:
                candidates[key] = (score, reason)

    for group in by_fam_first_ord.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                consider(group[i], group[j], 5, "patronymic_variant")  # index 5 = pat
    for group in by_first_pat_ord.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                consider(group[i], group[j], 2, "family_name_variant")  # index 2 = fam

    display = {p[0]: p[1] for p in parsed}

    rows = []
    for (id1, id2), (score, reason) in candidates.items():
        candidate_id = str(uuid.uuid5(NAMESPACE, f"person_candidate:{id1}|{id2}"))
        status = existing_status.get((id1, id2), "pending")
        rows.append((candidate_id, id1, id2, display[id1], display[id2], score, reason, status))

    con.execute("DROP TABLE IF EXISTS entities.person_candidate")
    con.execute("""
        CREATE TABLE entities.person_candidate (
            candidate_id UUID PRIMARY KEY,
            person_id_1 UUID REFERENCES entities.person(person_id),
            person_id_2 UUID REFERENCES entities.person(person_id),
            display_1 VARCHAR,
            display_2 VARCHAR,
            similarity_score DOUBLE,
            match_reason VARCHAR,
            status VARCHAR
        )
    """)
    con.executemany("INSERT INTO entities.person_candidate VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    n_preserved = sum(1 for r in rows if r[7] != "pending")
    print(f"entities.person_candidate: {len(rows)} candidate pairs "
          f"({sum(1 for r in rows if r[6] == 'patronymic_variant')} patronymic variants, "
          f"{sum(1 for r in rows if r[6] == 'family_name_variant')} family-name variants)")
    if n_preserved:
        print(f"  {n_preserved} already-reviewed decisions preserved from a previous run")


def export_person_review_queue(con: duckdb.DuckDBPyConnection, out_path: Path) -> None:
    """Sheets-ready review queue (docs/research_dataset.md's non-coder
    interface): one row per pending candidate pair, a blank decision column
    the researcher fills in with Yes/No/Unsure. Re-import with
    apply_person_merges() after review."""
    import csv as csv_module

    rows = con.execute("""
        SELECT candidate_id, display_1, display_2, similarity_score, match_reason
        FROM entities.person_candidate WHERE status = 'pending'
        ORDER BY match_reason, similarity_score DESC
    """).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_module.writer(f)
        w.writerow(["candidate_id", "person_1", "person_2", "similarity", "reason",
                    "decision (Yes/No/Unsure)"])
        for candidate_id, d1, d2, score, reason in rows:
            w.writerow([candidate_id, d1, d2, f"{score:.2f}", reason, ""])
    print(f"{len(rows)} pending candidates -> {out_path} (utf-8-sig, ready for Sheets/Excel import)")


def apply_person_merges(con: duckdb.DuckDBPyConnection, decisions_path: Path) -> None:
    """Reads a reviewed copy of the export above (decision column filled in)
    and applies confirmed merges: the later-registered person_id is marked
    superseded_by the earlier one. Non-destructive -- both UUIDs keep
    working as citation-stable references (docs/research_dataset.md)."""
    import csv as csv_module

    decisions = list(csv_module.DictReader(open(decisions_path, encoding="utf-8-sig")))
    n_confirmed = n_rejected = 0
    for row in decisions:
        decision = row["decision (Yes/No/Unsure)"].strip().lower()
        if decision not in ("yes", "no"):
            continue
        status = "confirmed" if decision == "yes" else "rejected"
        con.execute(
            "UPDATE entities.person_candidate SET status = ? WHERE candidate_id = ?",
            [status, row["candidate_id"]],
        )
        if decision == "yes":
            n_confirmed += 1
        else:
            n_rejected += 1

    to_merge = con.execute("""
        SELECT person_id_1, person_id_2 FROM entities.person_candidate WHERE status = 'confirmed'
    """).fetchall()
    for id1, id2 in to_merge:
        # person_id_1 is arbitrarily kept as the survivor -- doesn't matter
        # which side wins, since both UUIDs remain valid, working references
        # afterward via superseded_by_person_id (never deleted, never reused).
        con.execute("""
            UPDATE entities.person SET superseded_by_person_id = ?
            WHERE person_id = ? AND superseded_by_person_id IS NULL
        """, [id1, id2])

    print(f"applied {n_confirmed} confirmed merges, {n_rejected} rejected, "
          f"from {len(decisions)} reviewed rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--export-review-queue", type=Path, default=None,
                     help="write the pending Tier 2 candidate review queue to this CSV path")
    ap.add_argument("--apply-decisions", type=Path, default=None,
                     help="apply a reviewed copy of the review queue CSV (decision column filled in)")
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS entities")

    build_theater(con)
    build_work(con)
    candidate_status = _snapshot_person_candidate_status(con)
    build_person_tier1(con)
    build_person_tier2_candidates(con, candidate_status)
    if args.apply_decisions:
        apply_person_merges(con, args.apply_decisions)
    if args.export_review_queue:
        export_person_review_queue(con, args.export_review_queue)

    con.close()
    print(f"\nentities schema updated in {args.db}")


if __name__ == "__main__":
    main()
