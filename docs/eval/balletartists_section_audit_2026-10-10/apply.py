"""Apply the BalletArtists section map (section_map.csv, built by build_map.py from the blind heading readings).

Sets heading_path and institution on every BalletArtists entry (392 pages, 8,760 entries). Nothing else is
touched: no entry is added, removed or reordered, so person links (keyed by position) are unaffected.
  institution  = the list title printed on the list's first page, "Балетная труппа." (1896-97 MSK sets it in
                 display capitals; stored in the same form as the other 41 lists)
  heading_path = the printed heading the entry stands under, verbatim with its final colon or period: a staff
                 post on the opening page(s), then "Артистки:" / "Артисты:", then (1909-11) a guest heading
Each row is checked against the raw file first (same page, position, list number and surname as when the map
was built). Dry run by default; --write edits outputs/full_run/raw after saving a copy under backup/.
usage: uv run python docs/eval/balletartists_section_audit_2026-10-10/apply.py [--write]"""
import collections, csv, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).parent
RAW = Path('outputs/full_run/raw')
WRITE = '--write' in sys.argv
by_page = collections.defaultdict(list)
for r in csv.DictReader(open(HERE / 'section_map.csv', encoding='utf-8')):
    by_page[r['page_id']].append(r)

n_h = n_i = n = 0
for page, rs in sorted(by_page.items()):
    path = RAW / f'{page}.raw.json'
    d = json.load(open(path))
    es = d['entries']
    assert len(es) == len(rs), (page, len(es), len(rs))
    for r in rs:
        e = es[int(r['idx'])]
        assert (e.get('list_number') or '') == r['list_number'] and (e.get('family_name') or '') == r['family_name'], (page, r['idx'])
        assert (e.get('heading_path') or '') == r['old_heading'] and (e.get('institution') or '') == r['old_institution'], (page, r['idx'], 'raw changed since the map was built')
        assert r['new_heading'] and r['new_institution'], (page, r['idx'])
        n += 1
        if e.get('heading_path') != r['new_heading']: n_h += 1
        if e.get('institution') != r['new_institution']: n_i += 1
        e['heading_path'] = r['new_heading']
        e['institution'] = r['new_institution']
    if WRITE:
        (HERE / 'backup').mkdir(exist_ok=True)
        shutil.copy2(path, HERE / 'backup' / path.name)
        json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'{len(by_page)} pages, {n} entries: heading_path changes {n_h}, institution changes {n_i}', 'WRITTEN' if WRITE else '(dry run)')
