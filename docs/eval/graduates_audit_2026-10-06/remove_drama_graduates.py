"""RG decision 2026-10-06: the Graduates source is ballet-only -- remove every drama-course graduate row. Only graduates_1890-91_p005 (20 rows) and _p006 (8 rows) hold drama
graduates (the later seasons' drama graduates were already removed as page leaks in #135). Removes the raw entries and the person_link rows (all entries on both pages go, so no
later entry is renumbered). Dry run unless --write."""
import sys, json, os, duckdb
write = '--write' in sys.argv
RAW = 'outputs/full_run/raw/'
pages = {'graduates_1890-91_p005': 20, 'graduates_1890-91_p006': 8}
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=not write)
tot = 0
for pg, n in pages.items():
    d = json.load(open(RAW + pg + '.raw.json'))
    assert len(d['entries']) == n, (pg, len(d['entries']))
    hp = {(e.get('heading_path') or '') for e in d['entries']}
    assert all((h == '' or 'Ученицы' in h or 'Ученики' in h or 'Ученикъ' in h) for h in hp), hp
    links = [r[0] for r in c.execute("select entry_id from entities.person_link where entry_id like ?", [pg + '__e%']).fetchall()]
    assert len(links) == n, (pg, len(links))
    print(pg, 'entries', n, 'links', len(links))
    tot += n
    if write:
        d['entries'] = []
        tmp = RAW + pg + '.raw.json.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, RAW + pg + '.raw.json')
        c.execute("delete from entities.person_link where entry_id like ?", [pg + '__e%'])
print('rows removed:', tot, '(WRITTEN)' if write else '(dry run)')
