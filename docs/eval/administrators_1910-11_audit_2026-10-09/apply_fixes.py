"""1910-11 Administration (issue #144): remove the one note row stored as a person (p002 e018 'Дежурные врачи', printed as the note under the heading
'Дежурные врачи:'), and fix its person_link (#131 rule: delete the link, renumber the later entry on the page). Dry run unless --write."""
import sys, json, os, duckdb
sys.path.insert(0, 'docs/eval/administrators_audit_2026-10-07')
import adm_common
W = '--write' in sys.argv
pg = 'administration_1910-11_p002'; f = f'outputs/full_run/raw/{pg}.raw.json'
d = json.load(open(f)); km = dict(adm_common.kept(d['entries']))
ri = km[18]; e = d['entries'][ri]
assert e['family_name'] == 'Дежурные врачи' and not e.get('first_name') and 'вѣдѣніи придворной медицинской части' in (e.get('tenure_note_text') or ''), e
print('remove raw index', ri, e['family_name'], '|', e['tenure_note_text'])
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not W)
links = c.execute("select entry_id, cast(person_id as varchar) from entities.person_link where entry_id like ? order by 1", [pg + '__e%']).fetchall()
print(len(links), 'links on the page; e018 ->', [l for l in links if l[0].endswith('e018')], '; e019 ->', [l for l in links if l[0].endswith('e019')])
if W:
    del d['entries'][ri]
    json.dump(d, open(f + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(f + '.tmp', f)
    c.execute("delete from entities.person_link where entry_id=?", [pg + '__e018'])
    c.execute("update entities.person_link set entry_id=? where entry_id=?", [pg + '__e018', pg + '__e019'])
    print('WRITTEN')
