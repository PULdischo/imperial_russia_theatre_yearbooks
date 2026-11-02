"""Unlink Wikidata matches RG rejected (person field audit, 2026-11-02) and record each as 'No' in
entities.wikidata_decision, so link_wikidata.py never re-offers the candidate. apply_wikidata_decisions.py records a 'No'
but does not remove an existing link; this does both. Then rebuild the research layer.
usage: uv run python docs/eval/apply_wikidata_rejections_2026-11-02.py [--write]"""
import csv, sys, duckdb
from pathlib import Path
rows = list(csv.DictReader(open(Path(__file__).parent / 'wikidata_rejections_person_field_audit_2026-11-02.csv', encoding='utf-8')))
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only='--write' not in sys.argv)
for r in rows:
    link = con.execute("select wikidata_qid from entities.person_wikidata_link where cast(person_id as varchar)=?", [r['person_id']]).fetchone()
    assert link and link[0] == r['candidate_qid'], (r['display_name'], link)
    print(r['display_name'], 'linked to', link[0], '-> remove + record No')
    if '--write' in sys.argv:
        con.execute("delete from entities.person_wikidata_link where cast(person_id as varchar)=?", [r['person_id']])
        con.execute("delete from entities.wikidata_decision where cast(person_id as varchar)=? and candidate_qid=?", [r['person_id'], r['candidate_qid']])
        con.execute("insert into entities.wikidata_decision values (?,?,?,?,?)",
                    [r['person_id'], r['candidate_qid'], 'No', '2026-11-02', r['reason']])
print(len(rows), 'rows', '| WRITTEN' if '--write' in sys.argv else '| dry run')
