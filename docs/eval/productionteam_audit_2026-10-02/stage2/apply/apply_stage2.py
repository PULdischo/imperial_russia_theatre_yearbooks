import sys, json, collections
sys.path.insert(0, '/tmp/audit8')
import engine_pt as E
prop = json.load(open('/tmp/audit8/proposal.json'))
fc = json.load(open('/tmp/audit9/final_chain.json'))
city = json.load(open('/tmp/audit9/city.json'))
log = []; fails = []
# phase 6: homoglyph surnames
ns = {'__name__': 'phase', 'E': E}
sys.argv_save = sys.argv; sys.argv = ['phase6']
exec(open('/tmp/audit8/phase6.py').read(), ns); sys.argv = sys.argv_save
fails += ns['fails']; log += ns['log']
n_inst = n_hp = 0
for pg, rows in prop.items():
    es = E.load(pg)['entries']
    for r in rows:
        i = int(r['e'][1:]) - 1; x = es[i]
        # expected-old assertion: raw must equal what the proposal was computed from
        if (x.get('institution'), x.get('heading_path')) != (r['old_inst'], r['old_hp']):
            fails.append((pg, r['e'], 'raw drifted', x.get('institution'), x.get('heading_path'))); continue
        new_inst = city[f"{pg}|{r['e']}"]; new_hp = fc[pg][r['e']][1] or None
        if x.get('institution') != new_inst: log.append((pg, r['e'], 'institution', x.get('institution'), new_inst)); x['institution'] = new_inst; n_inst += 1
        if x.get('heading_path') != new_hp: log.append((pg, r['e'], 'heading_path', x.get('heading_path'), new_hp)); x['heading_path'] = new_hp; n_hp += 1
print(len(log), 'changes (', n_inst, 'institution,', n_hp, 'heading_path );', len(fails), 'fails')
for f in fails[:20]: print(f)
if '--write' in sys.argv and not fails:
    E.write_all(); json.dump(log, open('/tmp/audit9/stage2_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN', len(E._c), 'pages')
