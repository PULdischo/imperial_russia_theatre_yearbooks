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


# docs/work_normalization.md Problem #1, confirmed against the real data:
# 787 of 5,248 work rows had the genre abbreviation printed a second time,
# comma-appended to the title itself ("Жизнь за Царя, оп."), splitting a
# clean title from its own genre-suffixed printing into two "different"
# works. Stripped for the MATCHING key only -- canonical_title still
# displays the most common real printed variant, suffix or not.
_GENRE_SUFFIX_RE = re.compile(r",\s*[а-яА-Я\-]{1,10}\.?\s*$")


def _strip_genre_suffix(title: str) -> str:
    return _GENRE_SUFFIX_RE.sub("", title).strip()


def _fold_genre(genre: str | None) -> str | None:
    # docs/work_normalization.md Problem #5: case + trailing-period only --
    # deliberately never folds across language (com./ком. stay apart, a
    # real language-of-performance fact, not noise). Returns None for
    # blank, so blank-vs-filled is handled as "no signal" rather than as
    # its own distinct genre value.
    if not genre:
        return None
    g = re.sub(r"\s+", " ", genre.strip()).rstrip(".")
    return g.lower() or None


# docs/work_normalization.md Problem #3: on a multi-work bill, the
# extraction sometimes puts a *different* work's title from the same bill
# into the `genre` column of an adjacent row, rather than a real genre --
# worst (and, checked against several other high-variance titles, by far
# the dominant) case is "Гимнъ" (the anthem, a curtain-raiser), whose
# "genre" is one of these real work titles from the same bill 118 times.
# Hand-curated per the doc's own conclusion ("worth its own hand-curated
# fix rather than a general rule") -- a general "genre value that happens
# to also be a real title elsewhere" rule would risk flagging genuinely
# short, legitimate genre words too aggressively.
_GIMN_TITLE_KEY = "гимнъ"
_GIMN_CONTAMINATED_GENRE_FOLDS = {
    "новое дѣло", "евгеній онѣгинъ", "паяцы", "сверхъ комплекта",
    "ревизоръ", "старый закалъ", "жизнь за царя",
}

# docs/work_normalization.md Problem #4: an ordinal act/scene marker at
# the very START of the title means "this is an excerpt of a larger
# work," not a different work -- confirmed against the real data (178
# rows, 246 appearances) and deliberately anchored to the *start* of the
# string, since "карт." (a legitimate standalone genre, "tableau") appears
# throughout many genuinely-unrelated titles and a bare substring match
# produced false positives in an earlier pass. One "ordinal + marker" unit
# repeats up to twice, un-joined -- covers both "1-е и 2-е д." (one marker,
# two ordinals joined by "и") and "1-я карт. 4-го д." (two independent
# ordinal+marker pairs, scene-of-an-act, no "и" between them -- missed by
# an earlier version of this regex, confirmed via a real example that
# stayed unlinked because of it).
_ORDINAL_MARKER_UNIT = (
    r"\d+-(?:й|е|я|го)\.?\s+(?:и\s+\d+-(?:й|е|я|го)\.?\s+)?(?:д\.|дѣйств\w*|актъ|карт\.)\.?"
)
_EXCERPT_PREFIX_RE = re.compile(
    r"^(?P<note>" + _ORDINAL_MARKER_UNIT + r"(?:\s+" + _ORDINAL_MARKER_UNIT + r")?)\s*"
    r"(?:(?P<genre>[а-яА-ЯёЁ\-]{1,10}\.)\s+)?"
    r"(?P<base>.+)$"
)


def build_work(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute("""
        SELECT work_id, work_title, genre FROM raw.performance_work
        WHERE work_title IS NOT NULL AND trim(work_title) <> ''
    """).fetchall()

    # Group on title alone first (suffix-stripped, folded) -- genre is
    # decided per-title-group below, not baked into the grouping key from
    # the start, per docs/work_normalization.md Problem #2: a title
    # shouldn't split into "different works" just because genre was
    # blank one printing and filled the next.
    by_title: dict[str, list[tuple[str, str, str, str | None]]] = defaultdict(list)
    for work_id, title, genre in rows:
        title_key = _title_key(_strip_genre_suffix(title))
        genre_fold = _fold_genre(genre)
        if title_key == _GIMN_TITLE_KEY and genre_fold in _GIMN_CONTAMINATED_GENRE_FOLDS:
            genre_fold = None  # Problem #3: another bill item's title, not a real genre
        by_title[title_key].append((work_id, title, genre, genre_fold))

    def _pick_variant(members: list[tuple[str, str, str, str | None]]) -> tuple[str, str]:
        # Canonical display form = most common verbatim (title, genre) pair
        # actually printed in this group, not a normalized/modernized one.
        counts: dict[tuple[str, str], int] = {}
        for _, title, genre, _ in members:
            counts[(title, genre)] = counts.get((title, genre), 0) + 1
        (title, genre), _ = max(counts.items(), key=lambda kv: kv[1])
        return title, genre

    work_rows, link_rows, genre_candidate_rows = [], [], []
    title_key_to_work_ids: dict[str, list[str]] = defaultdict(list)
    n_multi_variant = n_genre_merged = 0

    for title_key, members in by_title.items():
        distinct_folds = {g for *_, g in members if g}

        if len(distinct_folds) <= 1:
            # Safe: at most one real genre in this title group (rest, if
            # any, just missing) -- merge everything into one work.
            fold = next(iter(distinct_folds), None)
            work_uuid = str(uuid.uuid5(NAMESPACE, f"work:{title_key}|{fold or ''}"))
            canonical_title, canonical_genre = _pick_variant(members)
            if len({(t, g) for _, t, g, _ in members}) > 1:
                n_multi_variant += 1
            if any(g is None for *_, g in members) and fold is not None:
                n_genre_merged += 1
            work_rows.append((work_uuid, canonical_title, canonical_genre, len(members), title_key))
            title_key_to_work_ids[title_key].append(work_uuid)
            for work_id, _, _, _ in members:
                link_rows.append((work_id, work_uuid))
        else:
            # docs/work_normalization.md Open Questions: genuinely
            # different genres under one title are real (Карменъ: оп./
            # бал.), not noise -- never silently merged. Split one work
            # row per distinct genre fold (blank-genre members get their
            # own row too, rather than guessing which real genre they
            # belong to), and record the split for human review.
            sub_groups: dict[str | None, list] = defaultdict(list)
            for m in members:
                sub_groups[m[3]].append(m)
            for fold, sub_members in sub_groups.items():
                work_uuid = str(uuid.uuid5(NAMESPACE, f"work:{title_key}|{fold or ''}"))
                canonical_title, canonical_genre = _pick_variant(sub_members)
                work_rows.append((work_uuid, canonical_title, canonical_genre, len(sub_members), title_key))
                title_key_to_work_ids[title_key].append(work_uuid)
                for work_id, _, _, _ in sub_members:
                    link_rows.append((work_id, work_uuid))
            genre_candidate_rows.append((title_key, sub_groups))

    # Problem #4: excerpt/partial-performance titles. Resolved as a second
    # pass over the now-deduplicated work rows, matching the excerpt's
    # extracted base title (folded the same way) against a real work --
    # preferring one whose own genre agrees with the excerpt's extracted
    # genre when the base title is ambiguous (split across >1 work by the
    # step above), never guessing when it isn't resolvable.
    excerpt_links: dict[str, tuple[str, str]] = {}  # work_uuid -> (parent_work_id, note)
    n_excerpt_matched = n_excerpt_unmatched = 0
    for work_uuid, canonical_title, _, _, title_key in work_rows:
        m = _EXCERPT_PREFIX_RE.match(canonical_title)
        if not m:
            continue
        base_key = _title_key(m.group("base"))
        if base_key == title_key or not base_key:
            continue  # guards against a degenerate/self match
        candidates = title_key_to_work_ids.get(base_key, [])
        parent = None
        if len(candidates) == 1:
            parent = candidates[0]
        elif len(candidates) > 1 and m.group("genre"):
            excerpt_genre_fold = _fold_genre(m.group("genre"))
            same_genre = [c for c in candidates
                          if _fold_genre(next(g for u, _, g, _, _ in work_rows if u == c)) == excerpt_genre_fold]
            if len(same_genre) == 1:
                parent = same_genre[0]
        if parent:
            excerpt_links[work_uuid] = (parent, m.group("note").strip())
            n_excerpt_matched += 1
        else:
            n_excerpt_unmatched += 1

    # Drop the dependent table first -- entities.work_link's FK reference
    # blocks CREATE OR REPLACE on entities.work otherwise, which would
    # silently break re-running this script a second time.
    con.execute("DROP TABLE IF EXISTS entities.work_link")
    con.execute("DROP TABLE IF EXISTS entities.work_genre_candidate")
    con.execute("""
        CREATE OR REPLACE TABLE entities.work (
            work_id UUID PRIMARY KEY,
            canonical_title VARCHAR,
            canonical_genre VARCHAR,
            appearance_count INTEGER,
            excerpt_of_work_id UUID,
            excerpt_note VARCHAR
        )
    """)
    # excerpt_of_work_id deliberately has no REFERENCES constraint -- it's
    # self-referential (an excerpt's parent is itself another work row),
    # and DuckDB's FK enforcement rejects a later UPDATE on a table whose
    # own primary key has *any* incoming FK, self-referential or not (same
    # reason entities.person_merge_log's docstring gives for skipping a
    # real FK into entities.person). Python already guarantees every
    # excerpt_links value is a work_id that exists in work_rows.
    con.executemany(
        "INSERT INTO entities.work VALUES (?, ?, ?, ?, NULL, NULL)",
        [(uid, t, g, n) for uid, t, g, n, _ in work_rows],
    )
    con.executemany(
        "UPDATE entities.work SET excerpt_of_work_id = ?, excerpt_note = ? WHERE work_id = ?",
        [(parent, note, uid) for uid, (parent, note) in excerpt_links.items()],
    )

    con.execute("""
        CREATE TABLE entities.work_link (
            raw_work_id VARCHAR PRIMARY KEY,
            work_id UUID REFERENCES entities.work(work_id)
        )
    """)
    con.executemany("INSERT INTO entities.work_link VALUES (?, ?)", link_rows)

    # entities.work_genre_candidate: every title split across >1 real
    # genre, for human review (docs/work_normalization.md's Open
    # Questions -- some splits are genuine adaptations, e.g. Карменъ
    # оп./бал., others are OCR noise on one genre word, e.g. Фаустъ's
    # "драм. поэма" variants -- never auto-decided here).
    con.execute("""
        CREATE TABLE entities.work_genre_candidate (
            candidate_id UUID PRIMARY KEY,
            title_key VARCHAR,
            work_id UUID REFERENCES entities.work(work_id),
            canonical_title VARCHAR,
            canonical_genre VARCHAR,
            appearance_count INTEGER
        )
    """)
    genre_candidate_insert_rows = []
    work_lookup = {uid: (t, g, n) for uid, t, g, n, _ in work_rows}
    for title_key, sub_groups in genre_candidate_rows:
        for fold, sub_members in sub_groups.items():
            work_uuid = str(uuid.uuid5(NAMESPACE, f"work:{title_key}|{fold or ''}"))
            t, g, n = work_lookup[work_uuid]
            candidate_id = str(uuid.uuid5(NAMESPACE, f"work_genre_candidate:{work_uuid}"))
            genre_candidate_insert_rows.append((candidate_id, title_key, work_uuid, t, g, n))
    con.executemany(
        "INSERT INTO entities.work_genre_candidate VALUES (?, ?, ?, ?, ?, ?)",
        genre_candidate_insert_rows,
    )

    n_excluded = con.execute(
        "SELECT count(*) FROM raw.performance_work WHERE work_title IS NULL OR trim(work_title) = ''"
    ).fetchone()[0]
    print(f"entities.work: {len(work_rows)} resolved works from {len(rows)} raw appearances "
          f"({n_excluded} excluded: blank work_title, see known_issues.md)")
    print(f"  {n_multi_variant} works were printed under more than one raw spelling variant "
          f"and collapsed into one entity by canonicalization")
    print(f"  {n_genre_merged} title groups merged a blank-genre printing into an existing "
          f"non-blank-genre work (Problem #2)")
    print(f"  {len(genre_candidate_rows)} title(s) split across >1 real genre, flagged in "
          f"entities.work_genre_candidate for human review ({len(genre_candidate_insert_rows)} rows)")
    print(f"  {n_excerpt_matched} excerpt/partial-performance titles linked to a parent work "
          f"({n_excerpt_unmatched} excerpt-shaped titles left unlinked -- ambiguous or garbled, "
          f"see docs/work_normalization.md)")


def export_work_genre_review_queue(con: duckdb.DuckDBPyConnection, out_path: Path) -> None:
    """Every title split across >1 real genre (entities.work_genre_candidate),
    grouped so a reviewer sees all the competing genre variants for one
    title together -- not a Yes/No queue like Person's, since there's no
    single pairwise decision: for each title, the researcher decides which
    (if any) of the listed work_ids are actually the same work and should
    be merged by hand, versus genuinely distinct adaptations to leave
    alone (docs/work_normalization.md's Карменъ оп./бал. example)."""
    import csv as csv_module

    rows = con.execute("""
        SELECT title_key, work_id, canonical_title, canonical_genre, appearance_count
        FROM entities.work_genre_candidate
        ORDER BY title_key, appearance_count DESC
    """).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_module.writer(f)
        w.writerow(["title_key", "work_id", "canonical_title", "canonical_genre",
                    "appearance_count", "same_work_as (list work_ids to merge, or leave blank)"])
        for title_key, work_id, title, genre, n in rows:
            w.writerow([title_key, work_id, title, genre, n, ""])
    n_titles = len({r[0] for r in rows})
    print(f"{n_titles} titles ({len(rows)} work rows) needing genre review -> {out_path} "
          f"(utf-8-sig, ready for Sheets/Excel import)")


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
            status VARCHAR,
            tenure_signal VARCHAR,
            tenure_evidence VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO entities.person_candidate VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)", rows
    )

    n_preserved = sum(1 for r in rows if r[7] != "pending")
    print(f"entities.person_candidate: {len(rows)} candidate pairs "
          f"({sum(1 for r in rows if r[6] == 'patronymic_variant')} patronymic variants, "
          f"{sum(1 for r in rows if r[6] == 'family_name_variant')} family-name variants)")
    if n_preserved:
        print(f"  {n_preserved} already-reviewed decisions preserved from a previous run")


def _annotate_tenure_signal(con: duckdb.DuckDBPyConnection) -> None:
    """Attaches an independent corroborating/contradicting signal to every
    Tier 2 candidate pair, run every time (not just for pending pairs) so
    the evidence behind a decision -- auto or human -- stays visible in the
    exported data: raw.service_period.start_date_undate is a real historical
    fact ("in service since 3 September 1881") that gets reprinted
    identically in every later yearbook the same person appears in, so two
    near-identical names that also share an exact start date is much
    stronger evidence than name similarity alone -- confirmed against the
    real data: 800/851 pending Tier 2 pairs (94%) shared at least one exact
    start date. tenure_signal is one of:
      - 'shared_start_date'  -- at least one exact match, strong corroboration
      - 'conflicting_dates'  -- both sides have dates, none match
      - 'no_date_data'       -- one or both sides have no service_period row
    """
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _pc_dates AS
        WITH person_dates AS (
            SELECT pl.person_id, sp.start_date_undate
            FROM entities.person_link pl
            JOIN raw.service_period sp ON sp.entry_id = pl.entry_id
            WHERE sp.start_date_undate IS NOT NULL
        ),
        d1 AS (
            SELECT pc.candidate_id, list(DISTINCT pd.start_date_undate) AS dates_1
            FROM entities.person_candidate pc
            JOIN person_dates pd ON pd.person_id = pc.person_id_1
            GROUP BY 1
        ),
        d2 AS (
            SELECT pc.candidate_id, list(DISTINCT pd.start_date_undate) AS dates_2
            FROM entities.person_candidate pc
            JOIN person_dates pd ON pd.person_id = pc.person_id_2
            GROUP BY 1
        )
        SELECT pc.candidate_id,
               coalesce(len(d1.dates_1), 0) AS n1,
               coalesce(len(d2.dates_2), 0) AS n2,
               list_intersect(d1.dates_1, d2.dates_2) AS shared_dates
        FROM entities.person_candidate pc
        LEFT JOIN d1 ON d1.candidate_id = pc.candidate_id
        LEFT JOIN d2 ON d2.candidate_id = pc.candidate_id
    """)
    con.execute("""
        UPDATE entities.person_candidate pc
        SET tenure_signal = CASE
                WHEN t.n1 = 0 OR t.n2 = 0 THEN 'no_date_data'
                WHEN len(t.shared_dates) > 0 THEN 'shared_start_date'
                ELSE 'conflicting_dates'
            END,
            tenure_evidence = CASE
                WHEN t.shared_dates IS NOT NULL AND len(t.shared_dates) > 0
                    THEN array_to_string(t.shared_dates, ', ')
                ELSE NULL
            END
        FROM _pc_dates t
        WHERE pc.candidate_id = t.candidate_id
    """)
    con.execute("DROP TABLE _pc_dates")


def apply_tenure_corroboration(con: duckdb.DuckDBPyConnection) -> None:
    """Auto-confirms (without individual human sign-off) any still-pending
    pair whose tenure_signal is 'shared_start_date' -- an explicit,
    deliberate exception to this pipeline's usual never-auto-merge rule for
    Tier 2, made because the shared-start-date signal is strong enough that
    the researcher chose to trust it directly. Kept as its own status value
    ('confirmed_tenure') rather than reusing 'confirmed' so the audit trail
    always shows whether a merge came from this rule or an explicit human
    Yes (docs/research_dataset.md)."""
    con.execute("""
        UPDATE entities.person_candidate
        SET status = 'confirmed_tenure'
        WHERE status = 'pending' AND tenure_signal = 'shared_start_date'
    """)
    n_confirmed = con.execute(
        "SELECT count(*) FROM entities.person_candidate WHERE status = 'confirmed_tenure'"
    ).fetchone()[0]
    n_pending = con.execute(
        "SELECT count(*) FROM entities.person_candidate WHERE status = 'pending'"
    ).fetchone()[0]
    print(f"entities.person_candidate: {n_confirmed} pairs auto-confirmed via shared service-start "
          f"date (tenure corroboration); {n_pending} remain pending for human review")


def reconcile_person_merges(con: duckdb.DuckDBPyConnection) -> int:
    """Turns a confirmed/confirmed_tenure/confirmed_wikidata decision into
    an actual merge -- not just a status flag -- by setting
    entities.person.superseded_by_person_id. Does NOT itself repoint
    entities.person_link (see _repoint_all_superseded, called once at the
    very end of main(), for why that has to be a separate, full-chain
    pass rather than done per-decision here).

    Uses union-find rather than resolving each pair in isolation: a person
    can appear in more than one confirmed pair (e.g. three printed spelling
    variants of one patronymic cross-match pairwise -- A-B, A-C, B-C -- all
    three seen in the real data) and naive pairwise merging would pick a
    different, inconsistent survivor depending on row order. The survivor
    of each connected component is always its lexicographically smallest
    person_id -- arbitrary, like the old single-pair rule, but now actually
    stable across reruns regardless of which id a given row lists first.

    Returns the number of person records absorbed this call. main() calls
    this in a loop to a fixed point (0 returned): once a person is absorbed
    they drop out of build_person_tier2_candidates's blocking pool entirely
    (WHERE superseded_by_person_id IS NULL), so any OTHER still-pending pair
    that happened to involve them would otherwise be silently lost instead
    of being regenerated against their new survivor on the next pass.
    """
    pairs = con.execute("""
        SELECT person_id_1, person_id_2 FROM entities.person_candidate
        WHERE status IN ('confirmed', 'confirmed_tenure', 'confirmed_wikidata')
    """).fetchall()
    if not pairs:
        return 0

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            root, child = (ra, rb) if ra < rb else (rb, ra)
            parent[child] = root

    for id1, id2 in pairs:
        union(str(id1), str(id2))

    absorbed = {node: find(node) for node in parent if find(node) != node}
    if not absorbed:
        return 0

    con.executemany("""
        UPDATE entities.person SET superseded_by_person_id = ?
        WHERE person_id = ? AND superseded_by_person_id IS NULL
    """, [(root, absorbed_id) for absorbed_id, root in absorbed.items()])

    print(f"entities.person: {len(absorbed)} person record(s) merged into "
          f"{len(set(absorbed.values()))} surviving record(s)")
    return len(absorbed)


def _repoint_all_superseded(con: duckdb.DuckDBPyConnection) -> None:
    """Repoints entities.person_link -- and recomputes attested season
    ranges -- from the FULL superseded_by_person_id chain currently in
    entities.person, not just the pairs reconcile_person_merges saw during
    this run's own Tier 2 loop. Necessary because build_person_tier1
    rebuilds person_link from scratch every run purely from each row's own
    tier1 cluster, with no knowledge of any later Tier 2/tenure/Wikidata
    merge -- and once a person is absorbed, they drop out of Tier 2's
    blocking pool entirely, so a merge decided in an EARLIER run can never
    be rediscovered as a candidate pair again to re-trigger a per-decision
    repoint. Confirmed as a real, not theoretical, bug: building
    research.person_appearance's FK against research.person (only
    non-superseded rows) failed with 3,024 person_link rows still pointing
    at an already-superseded person, entirely because of an unrelated
    rerun of this script for Work normalization silently resetting their
    repointing. Idempotent -- safe to call every run whether or not
    anything changed this time.
    """
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _final_survivor AS
        WITH RECURSIVE chain(person_id, final_id) AS (
            SELECT person_id, person_id FROM entities.person WHERE superseded_by_person_id IS NULL
            UNION ALL
            SELECT p.person_id, c.final_id
            FROM entities.person p
            JOIN chain c ON p.superseded_by_person_id = c.person_id
        )
        SELECT * FROM chain
    """)
    con.execute("""
        UPDATE entities.person_link pl
        SET person_id = fs.final_id
        FROM _final_survivor fs
        WHERE pl.person_id = fs.person_id AND pl.person_id != fs.final_id
    """)
    con.execute("""
        UPDATE entities.person p
        SET first_attested_season = seasons.first_season,
            last_attested_season = seasons.last_season
        FROM (
            SELECT pl.person_id, min(sp.season) AS first_season, max(sp.season) AS last_season
            FROM entities.person_link pl
            JOIN raw.roster_entry r ON r.entry_id = pl.entry_id
            JOIN raw.source_pages sp ON sp.page_id = r.page_id
            WHERE sp.season IS NOT NULL
            GROUP BY pl.person_id
        ) AS seasons
        WHERE p.person_id = seasons.person_id
    """)
    con.execute("DROP TABLE _final_survivor")

    n_stale = con.execute("""
        SELECT count(*) FROM entities.person_link pl
        JOIN entities.person p ON p.person_id = pl.person_id
        WHERE p.superseded_by_person_id IS NOT NULL
    """).fetchone()[0]
    print(f"entities.person_link: full-chain repoint complete "
          f"({n_stale} rows still pointing at a superseded person -- should always be 0)")


def _ensure_person_merge_log(con: duckdb.DuckDBPyConnection) -> None:
    """A permanent, append-only decision ledger -- deliberately separate
    from entities.person_candidate, which is a LIVE working set of
    comparisons among currently-active (non-superseded) people and gets
    rebuilt from scratch every Tier 2 iteration/rerun. The moment a person
    is absorbed by a merge they drop out of that live set entirely (correct
    -- they're resolved), which means the exact evidence a merge was based
    on (similarity score, matched tenure date) would become unrecoverable
    the instant a later iteration or rerun regenerates the table, unless
    it's copied somewhere that never gets dropped. CREATE TABLE IF NOT
    EXISTS (not OR REPLACE) and no FK into entities.person -- person gets
    recreated every Tier 1 run, and this ledger must survive that."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities.person_merge_log (
            candidate_id UUID PRIMARY KEY,
            person_id_1 UUID,
            person_id_2 UUID,
            display_1 VARCHAR,
            display_2 VARCHAR,
            similarity_score DOUBLE,
            match_reason VARCHAR,
            status VARCHAR,
            tenure_signal VARCHAR,
            tenure_evidence VARCHAR
        )
    """)


def _log_decided_candidates(con: duckdb.DuckDBPyConnection) -> None:
    """Copies any newly-decided (non-pending) row from the live
    person_candidate table into the permanent log, skipping candidate_ids
    already logged. candidate_id is deterministic (uuid5 of the sorted
    person_id pair, see build_person_tier2_candidates), so this is safe to
    call repeatedly across iterations and reruns without ever duplicating
    a log entry."""
    con.execute("""
        INSERT INTO entities.person_merge_log
        SELECT candidate_id, person_id_1, person_id_2, display_1, display_2,
               similarity_score, match_reason, status, tenure_signal, tenure_evidence
        FROM entities.person_candidate
        WHERE status != 'pending'
          AND candidate_id NOT IN (SELECT candidate_id FROM entities.person_merge_log)
    """)


def export_person_review_queue(con: duckdb.DuckDBPyConnection, out_path: Path) -> None:
    """Sheets-ready review queue (docs/research_dataset.md's non-coder
    interface): one row per pending candidate pair, a blank decision column
    the researcher fills in with Yes/No/Unsure. Re-import with
    apply_person_merges() after review. Includes the tenure_signal/evidence
    columns so the researcher can see why a pair landed in the hard
    (non-auto-confirmable) bucket -- conflicting dates vs. no date data at
    all are very different situations to review."""
    import csv as csv_module

    rows = con.execute("""
        SELECT candidate_id, display_1, display_2, similarity_score, match_reason,
               tenure_signal, tenure_evidence
        FROM entities.person_candidate WHERE status = 'pending'
        ORDER BY match_reason, similarity_score DESC
    """).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_module.writer(f)
        w.writerow(["candidate_id", "person_1", "person_2", "similarity", "reason",
                    "tenure_signal", "tenure_evidence", "decision (Yes/No/Unsure)"])
        for candidate_id, d1, d2, score, reason, tsig, tev in rows:
            w.writerow([candidate_id, d1, d2, f"{score:.2f}", reason, tsig, tev or "", ""])
    print(f"{len(rows)} pending candidates -> {out_path} (utf-8-sig, ready for Sheets/Excel import)")


def export_tenure_audit(con: duckdb.DuckDBPyConnection, out_path: Path) -> None:
    """Full list of every pair auto-confirmed by apply_tenure_corroboration,
    for the researcher to spot-check the rule itself -- not to collect a
    decision (these are already applied/merged). Reads from the permanent
    person_merge_log, not the live person_candidate table: by the time this
    runs, later Tier 2 iterations may already have rebuilt person_candidate
    without these rows (their people are no longer in the active blocking
    pool once absorbed) -- the log is the only place this history survives."""
    import csv as csv_module

    rows = con.execute("""
        SELECT candidate_id, display_1, display_2, similarity_score, match_reason, tenure_evidence
        FROM entities.person_merge_log WHERE status = 'confirmed_tenure'
        ORDER BY match_reason, similarity_score DESC
    """).fetchall()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv_module.writer(f)
        w.writerow(["candidate_id", "person_1", "person_2", "similarity", "name_match_reason",
                    "shared_service_start_date", "auto_accept_reason"])
        for candidate_id, d1, d2, score, reason, evidence in rows:
            w.writerow([candidate_id, d1, d2, f"{score:.2f}", reason, evidence,
                        "shared exact printed service-start date"])
    print(f"{len(rows)} tenure-auto-confirmed pairs -> {out_path} (utf-8-sig, for spot-check review)")


def apply_person_merges(con: duckdb.DuckDBPyConnection, decisions_path: Path) -> None:
    """Reads a reviewed copy of the export above (decision column filled in)
    and records confirmed/rejected decisions on entities.person_candidate.
    Does not itself apply the merge -- reconcile_person_merges() does that
    for every confirmed pair (this function's and apply_tenure_corroboration's
    alike) right after, unconditionally, every pipeline run."""
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

    print(f"recorded {n_confirmed} confirmed, {n_rejected} rejected, "
          f"from {len(decisions)} reviewed rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--export-review-queue", type=Path, default=None,
                     help="write the pending Tier 2 candidate review queue to this CSV path")
    ap.add_argument("--apply-decisions", type=Path, default=None,
                     help="apply a reviewed copy of the review queue CSV (decision column filled in)")
    ap.add_argument("--export-tenure-audit", type=Path, default=None,
                     help="write the tenure-auto-confirmed pairs to this CSV for spot-check review")
    ap.add_argument("--export-work-genre-review", type=Path, default=None,
                     help="write titles split across >1 real genre to this CSV for human review")
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS entities")
    _ensure_person_merge_log(con)

    build_theater(con)
    build_work(con)
    candidate_status = _snapshot_person_candidate_status(con)
    build_person_tier1(con)

    # Looped to a fixed point rather than run once: reconcile_person_merges
    # absorbs people out of the active pool, and build_person_tier2_candidates
    # only ever compares currently-active people. Without looping, a still-
    # pending pair whose OTHER member gets absorbed by an unrelated merge
    # this same run would silently vanish instead of being regenerated
    # against its new survivor -- confirmed against the real data (11 of the
    # first pass's 51 pending pairs pointed at an already-superseded person).
    # Monotonic (absorbed people never come back), so this always terminates;
    # the cap is just a sanity backstop against a future logic bug looping.
    MAX_TIER2_ITERATIONS = 10
    decisions_applied = False
    for iteration in range(1, MAX_TIER2_ITERATIONS + 1):
        build_person_tier2_candidates(con, candidate_status)
        _annotate_tenure_signal(con)
        apply_tenure_corroboration(con)
        if args.apply_decisions and not decisions_applied:
            apply_person_merges(con, args.apply_decisions)
            decisions_applied = True
        _log_decided_candidates(con)
        n_merged = reconcile_person_merges(con)
        candidate_status = _snapshot_person_candidate_status(con)
        if not n_merged:
            break
    else:
        print(f"  WARNING: person-merge reconciliation did not reach a fixed point "
              f"after {MAX_TIER2_ITERATIONS} iterations -- investigate before trusting "
              f"entities.person_candidate")

    _repoint_all_superseded(con)

    if args.export_review_queue:
        export_person_review_queue(con, args.export_review_queue)
    if args.export_tenure_audit:
        export_tenure_audit(con, args.export_tenure_audit)
    if args.export_work_genre_review:
        export_work_genre_review_queue(con, args.export_work_genre_review)

    con.close()
    print(f"\nentities schema updated in {args.db}")


if __name__ == "__main__":
    main()
