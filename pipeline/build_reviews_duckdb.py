"""Land the Season Review verbatim text and its mention layer in the DuckDB file.

Closes deferred item §12.5 (docs/season_reviews.md): until now the reviews were
CSV-only, so 27,085 mentions could not be joined to the 3,243 people and 3,190
works they point at. Everything else in this project is queryable; this makes
the reviews queryable too.

Placement follows the existing four-layer architecture rather than inventing a
fifth:

- **`raw.review_page` / `raw.review_block`** -- one row per printed page and
  per printed block, verbatim, page-centric, never hand-edited. The same
  contract as `raw.person_entry` and `raw.event_entry`.
- **`entities.review_mention`** -- the record-linkage layer: a surface string,
  its candidate entity ids, the method that linked it and the confidence. This
  is working crosswalk state with review queues attached, exactly what
  `entities` already holds for `person_link` and `work_link`, and like them it
  is **not published**.

`research` gets nothing here. A mention is not a research fact; the research
fact is the assertion built from it (performer -> role -> work -> date), and
that is `build_review_assertions.py`.

DuckDB specifics that shape the DDL below. Two are already known to this
project: there is no `ALTER TABLE ADD FOREIGN KEY`, and `UPDATE` is rejected on
any table whose primary key has an incoming foreign key -- hence `CREATE TABLE`
with inline constraints plus `INSERT INTO ... SELECT`, never
`CREATE TABLE AS SELECT` plus `ALTER`. A third turned up here and is worth
adding to the list: **a foreign key cannot cross schemas** ("Creating foreign
keys across different schemas or catalogs is not supported"), so
`entities.review_mention.block_id` cannot reference `raw.review_block`. It is a
plain column, and referential integrity is asserted after loading instead.

Safe to re-run: it drops and rebuilds only its own three tables, in dependency
order, and touches nothing else in the file.

Usage:
    uv run python pipeline/build_reviews_duckdb.py \
        --reviews-dir outputs/reviews/merged_full \
        --mentions-dir outputs/reviews/mentions \
        --db outputs/reviews/db/imperial_theaters_reviews.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

# dropped in this order: children before parents
DROP_ORDER = ["entities.review_mention", "raw.review_block", "raw.review_page"]

DDL_PAGE = """
CREATE TABLE raw.review_page (
    page_id                 VARCHAR PRIMARY KEY,
    season                  VARCHAR NOT NULL,
    city                    VARCHAR NOT NULL,
    genre                   VARCHAR NOT NULL,
    printed_folio           VARCHAR,
    tailpiece_present       BOOLEAN,
    no_text                 BOOLEAN,
    copy_artifacts          VARCHAR,
    reading_order_uncertain BOOLEAN,
    n_blocks                INTEGER,
    n_chars                 INTEGER
)
"""

DDL_BLOCK = """
CREATE TABLE raw.review_block (
    block_id         VARCHAR PRIMARY KEY,
    page_id          VARCHAR NOT NULL REFERENCES raw.review_page(page_id),
    block_index      INTEGER NOT NULL,
    block_type       VARCHAR NOT NULL,
    enumerator       VARCHAR,
    figure_subtype   VARCHAR,
    caption_vertical BOOLEAN,
    footnote_marker  VARCHAR,
    text             VARCHAR,
    caption_text     VARCHAR
)
"""

DDL_MENTION = """
CREATE TABLE entities.review_mention (
    mention_id       BIGINT PRIMARY KEY,
    -- no REFERENCES: DuckDB refuses a foreign key across schemas
    -- ("Creating foreign keys across different schemas or catalogs is not
    -- supported"), the same reason entities.work.excerpt_of_work_id is a plain
    -- column. The relationship to raw.review_block is enforced by the
    -- post-load check below instead.
    block_id         VARCHAR NOT NULL,
    page_id          VARCHAR NOT NULL,
    season           VARCHAR NOT NULL,
    city             VARCHAR NOT NULL,
    mention_type     VARCHAR NOT NULL,
    char_start       INTEGER NOT NULL,
    char_end         INTEGER NOT NULL,
    surface          VARCHAR NOT NULL,
    normalised       VARCHAR,
    entity_id        VARCHAR,
    candidates_n     INTEGER,
    candidate_ids    VARCHAR,
    link_method      VARCHAR,
    link_confidence  VARCHAR,
    evidence         VARCHAR,
    rank_reason      VARCHAR
)
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-dir", required=True, type=Path)
    ap.add_argument("--mentions-dir", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    a = ap.parse_args()

    page_csv = (a.reviews_dir / "review_page.csv").as_posix()
    block_csv = (a.reviews_dir / "review_block.csv").as_posix()
    mention_csv = (a.mentions_dir / "review_mention.csv").as_posix()
    for f in (page_csv, block_csv, mention_csv):
        if not Path(f).exists():
            raise SystemExit(f"missing input: {f}")

    con = duckdb.connect(str(a.db))
    for t in DROP_ORDER:
        con.execute(f"DROP TABLE IF EXISTS {t}")

    con.execute(DDL_PAGE)
    con.execute(f"""
        INSERT INTO raw.review_page
        SELECT page_id, season, city, genre, nullif(printed_folio, ''),
               tailpiece_present, no_text, nullif(copy_artifacts, ''),
               reading_order_uncertain, n_blocks, n_chars
        FROM read_csv('{page_csv}', header=true, all_varchar=true)
    """)

    con.execute(DDL_BLOCK)
    con.execute(f"""
        INSERT INTO raw.review_block
        SELECT block_id, page_id, CAST(block_index AS INTEGER), block_type,
               nullif(enumerator, ''), nullif(figure_subtype, ''),
               CAST(nullif(caption_vertical, '') AS BOOLEAN),
               nullif(footnote_marker, ''), nullif(text, ''),
               nullif(caption_text, '')
        FROM read_csv('{block_csv}', header=true, all_varchar=true)
    """)

    con.execute(DDL_MENTION)
    # mention_id is assigned here rather than in the matcher: the CSV is a
    # report, this is the keyed store, and a stable key needs a stable order
    con.execute(f"""
        INSERT INTO entities.review_mention
        SELECT row_number() OVER (ORDER BY page_id, block_id,
                                  CAST(char_start AS INTEGER)) AS mention_id,
               block_id, page_id, season, city, mention_type,
               CAST(char_start AS INTEGER), CAST(char_end AS INTEGER),
               surface, nullif(normalised, ''), nullif(entity_id, ''),
               CAST(candidates_n AS INTEGER), nullif(candidate_ids, ''),
               link_method, link_confidence, nullif(evidence, ''),
               nullif(rank_reason, '')
        FROM read_csv('{mention_csv}', header=true, all_varchar=true)
    """)

    for t in ("raw.review_page", "raw.review_block", "entities.review_mention"):
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t:28s} {n:>8,} rows")

    # the FK DuckDB would not let us declare across schemas
    orphans = con.execute("""
        SELECT count(*) FROM entities.review_mention m
        LEFT JOIN raw.review_block b ON b.block_id = m.block_id
        WHERE b.block_id IS NULL
    """).fetchone()[0]
    if orphans:
        raise SystemExit(f"{orphans} mention(s) reference a missing block")
    print("  referential check: every mention resolves to a block")

    # the join this whole exercise exists to make possible
    linked = con.execute("""
        SELECT count(*) FROM entities.review_mention m
        JOIN research.person p ON p.person_id = m.entity_id
        WHERE m.mention_type = 'person'
    """).fetchone()[0]
    works = con.execute("""
        SELECT count(*) FROM entities.review_mention m
        JOIN research.work w ON w.work_id = m.entity_id
        WHERE m.mention_type = 'work'
    """).fetchone()[0]
    print(f"\n  person mentions joining research.person : {linked:,}")
    print(f"  work mentions joining research.work     : {works:,}")
    con.close()


if __name__ == "__main__":
    main()
