"""Rows for docs/eval/review_mention_links.csv from RG's pupil-link ruling (2026-11-07): 'relink' -> the one graduate of that surname
and gender within six seasons; 'unlink' -> empty person_id. occurrence in the matcher's row order."""
import csv, collections, duckdb, json
D = 'docs/eval/review_pupil_links_2026-11-07'
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
acts = {r['mention_id']: r for r in csv.DictReader(open(f'{D}/pupil_links.csv', encoding='utf-8')) if r['action']}
meta = {str(m): (b, a, s) for m, b, a, s in c.sql(f"select mention_id, block_id, char_start, surface from entities.review_mention where mention_id in ({','.join(acts)})").fetchall()}
blocks = {v[0] for v in meta.values()}
seen = collections.Counter(); occ = {}
for r in csv.DictReader(open('outputs/reviews/mentions/review_mention.csv', encoding='utf-8')):
    if r['mention_type'] != 'person' or r['block_id'] not in blocks: continue
    k = (r['block_id'], r['surface']); occ[(r['block_id'], r['surface'], int(r['char_start']))] = seen[k]; seen[k] += 1
links = {(r['block_id'], r['surface'], r['occurrence']): r for r in csv.DictReader(open('docs/eval/review_mention_links.csv', encoding='utf-8'))}
new, clash = [], []
for mid, r in acts.items():
    bid, a, surf = meta[mid]; key = (bid, surf, str(occ[(bid, surf, a)]))
    pid = r['proposed_id'] if r['action'] == 'relink' else ''
    if key in links: clash.append((mid, key, links[key]['person_id'], links[key]['decided_by'][:60])); continue
    ev = (f"pupil ({r['marker']}) {r['season']} {r['city']} p.{r['page']}; was linked to {r['linked_now']} (first listed {r['first_listed']})"
          + (f"; graduate {r['proposed']}" if pid else '; no single graduate of that surname and gender') + f" (mention {mid})")
    new.append({'block_id': bid, 'surface': surf, 'occurrence': key[2], 'person_id': pid,
                'decided_by': f"RG 2026-11-07, pupil links: {'relink to the one graduate' if pid else 'unlink'}", 'evidence': ev})
json.dump(new, open(f'{D}/new_links.json', 'w'), ensure_ascii=False)
print('rows', len(new), '| relink', sum(1 for n in new if n['person_id']), '| unlink', sum(1 for n in new if not n['person_id']), '| clashes', len(clash))
for x in clash: print('  CLASH', x)
