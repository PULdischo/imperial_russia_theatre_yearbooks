"""Load the jubilee/obituary catalogue (docs/jubilees_obituaries/) into a DuckDB file as three tables:

    raw.jubilee_obituary_entry           the catalogue verbatim: one row per catalogue row (702), every column of
                                         jubilees_obituaries_all_entries.csv plus entry_id. Nothing derived.
    entities.jubilee_obituary_person_link one row per person entry (655): the person_id it is linked to (or none),
                                         link_status, record name and the basis of the decision
                                         (jubilees_obituaries_person_links.csv, made by build/link_persons.py).
    research.jubilee_obituary            one row per catalogue row, the columns a researcher queries, with
                                         person_id resolved through entities.person.superseded_by_person_id.

entry_id is the Obsidian notes' id: sha1 of season|source_file|name (section rows) or
season|source_file|pdf_page|kind|name (all other rows, and section rows without a name), first 10 hex digits.

STANDALONE for now (2026-10-22): not called by the pipeline. research.jubilee_obituary.person_id is a plain UUID
column with NO foreign key, because build_research_model.py drops and recreates research.person and a declared
FK would block that drop. The loader checks every person_id against research.person instead. When this is wired
into the build it belongs after build_research_model.py (or inside it, with a real FK); re-run
build/link_persons.py first if people were merged or split.

Additive and safe to re-run: CREATE OR REPLACE on these three tables only.

Usage (test copy, never production without RG's go-ahead):
    uv run python docs/jubilees_obituaries/build/load_jubilees_obituaries.py --db <copy>.duckdb
"""
from __future__ import annotations

import argparse, csv, hashlib
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / 'jubilees_obituaries_all_entries.csv'
LINKS = ROOT / 'jubilees_obituaries_person_links.csv'
NON_PERSON = {'section_heading_only', 'other', 'work_milestone'}


def entry_id(d):
    if d['source_type'] == 'section' and d['name_verbatim']:
        s = f"{d['season']}|{d['source_file']}|{d['name_verbatim']}"
    else:
        s = f"{d['season']}|{d['source_file']}|{d['pdf_page']}|{d['kind']}|{d['name_verbatim']}"
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, type=Path)
    args = ap.parse_args()
    if 'full_run' in str(args.db.resolve()):
        raise SystemExit('refusing to write to outputs/full_run: test on a copy (RG has not approved production)')

    cat = list(csv.DictReader(open(CATALOGUE, encoding='utf-8')))
    cols = list(cat[0].keys())
    for i, d in enumerate(cat, 1):
        d['entry_id'] = entry_id(d); d['catalogue_row'] = str(i)
    ids = [d['entry_id'] for d in cat]
    if len(set(ids)) != len(ids):
        raise SystemExit('entry_id is not unique in the catalogue')
    links = list(csv.DictReader(open(LINKS, encoding='utf-8')))
    person_ids = {d['entry_id'] for d in cat if d['kind'] not in NON_PERSON}
    link_ids = {l['entry_id'] for l in links}
    if link_ids != person_ids:
        raise SystemExit(f'person links out of date with the catalogue ({len(person_ids - link_ids)} entries unlinked, '
                         f'{len(link_ids - person_ids)} links to no entry): re-run build/link_persons.py')

    con = duckdb.connect(str(args.db))
    for s in ('raw', 'entities', 'research'):
        con.execute(f'CREATE SCHEMA IF NOT EXISTS {s}')
    con.execute('CREATE OR REPLACE TABLE raw.jubilee_obituary_entry (entry_id VARCHAR PRIMARY KEY, catalogue_row INTEGER, '
                + ', '.join(f'{c} VARCHAR' for c in cols) + ')')
    con.executemany(f'INSERT INTO raw.jubilee_obituary_entry VALUES ({", ".join(["?"] * (len(cols) + 2))})',
                    [[d['entry_id'], int(d['catalogue_row'])] + [d[c] or None for c in cols] for d in cat])

    con.execute("""CREATE OR REPLACE TABLE entities.jubilee_obituary_person_link (
        entry_id VARCHAR PRIMARY KEY, person_id UUID, link_status VARCHAR, record_name VARCHAR,
        record_seasons VARCHAR, record_source VARCHAR, basis VARCHAR)""")
    con.executemany('INSERT INTO entities.jubilee_obituary_person_link VALUES (?, ?, ?, ?, ?, ?, ?)',
                    [[l['entry_id'], l['person_id'] or None, l['link_status'], l['record_name'] or None,
                      l['record_seasons'] or None, l['record_source'] or None, l['basis'] or None] for l in links])

    con.execute("""CREATE OR REPLACE TABLE research.jubilee_obituary (
        entry_id VARCHAR PRIMARY KEY,
        season VARCHAR, kind VARCHAR, relevance VARCHAR, is_person BOOLEAN,
        person_id UUID,                -- research.person (no declared FK; see the loader's docstring)
        link_status VARCHAR,           -- linked / no_record; NULL for rows that are not about one person
        name_verbatim VARCHAR, name_latin VARCHAR, role VARCHAR, troupe_city VARCHAR, dates VARCHAR,
        evidence_verbatim VARCHAR, evidence_english VARCHAR, notes VARCHAR, see_also VARCHAR,
        source_type VARCHAR, source_file VARCHAR, pdf_page VARCHAR, printed_page VARCHAR,
        length VARCHAR, author VARCHAR, portrait VARCHAR, tier_basis VARCHAR, date_check VARCHAR, tier_check VARCHAR)""")
    con.execute("""
        WITH RECURSIVE sup(person_id, live_id, depth) AS (
            SELECT person_id, person_id, 0 FROM entities.person
            UNION ALL
            SELECT s.person_id, p.superseded_by_person_id, s.depth + 1
            FROM sup s JOIN entities.person p ON p.person_id = s.live_id
            WHERE p.superseded_by_person_id IS NOT NULL AND s.depth < 20),
        live AS (SELECT person_id, arg_max(live_id, depth) AS live_id FROM sup GROUP BY person_id)
        INSERT INTO research.jubilee_obituary
        SELECT e.entry_id, e.season, e.kind, e.relevance,
               e.kind NOT IN ('section_heading_only', 'other', 'work_milestone'),
               coalesce(lv.live_id, l.person_id), l.link_status,
               e.name_verbatim, e.name_latin, e.role, e.troupe_city, e.dates,
               e.evidence_verbatim, e.evidence_english, e.notes, e.see_also,
               e.source_type, e.source_file, e.pdf_page, e.printed_page,
               e.length, e.author, e.portrait, e.tier_basis, e.date_check, e.tier_check
        FROM raw.jubilee_obituary_entry e
        LEFT JOIN entities.jubilee_obituary_person_link l USING (entry_id)
        LEFT JOIN live lv ON lv.person_id = l.person_id
        ORDER BY e.catalogue_row""")

    # integrity
    q = lambda s: con.execute(s).fetchone()[0]
    checks = {
        'rows': (q('SELECT count(*) FROM research.jubilee_obituary'), len(cat)),
        'person entries': (q('SELECT count(*) FROM research.jubilee_obituary WHERE is_person'), len(person_ids)),
        'person_id not in research.person': (q("""SELECT count(*) FROM research.jubilee_obituary j
            LEFT JOIN research.person p USING (person_id) WHERE j.person_id IS NOT NULL AND p.person_id IS NULL"""), 0),
        'linked without person_id': (q("SELECT count(*) FROM research.jubilee_obituary WHERE link_status = 'linked' AND person_id IS NULL"), 0),
        'person_id but not linked': (q("SELECT count(*) FROM research.jubilee_obituary WHERE link_status <> 'linked' AND person_id IS NOT NULL"), 0),
        'person entry without a link row': (q('SELECT count(*) FROM research.jubilee_obituary WHERE is_person AND link_status IS NULL'), 0),
    }
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    if bad:
        raise SystemExit(f'integrity check failed: {bad}')
    moved = q("""SELECT count(*) FROM research.jubilee_obituary j JOIN entities.jubilee_obituary_person_link l USING (entry_id)
                 WHERE j.person_id <> l.person_id""")
    for k, (got, _) in checks.items():
        print(f'{k}: {got}')
    print(f'person_ids moved to a merged record: {moved}')
    print('linked:', q("SELECT count(*) FROM research.jubilee_obituary WHERE link_status = 'linked'"),
          '| distinct people:', q('SELECT count(DISTINCT person_id) FROM research.jubilee_obituary'))


if __name__ == '__main__':
    main()
