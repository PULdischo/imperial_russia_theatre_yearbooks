"""Stage 2b: institution := printed list title (per season, from /tmp/audit9/titles.json);
heading_path := '<city> / <chain>' (city = the institution value stage 2 wrote)."""
import sys, json, glob
sys.path.insert(0, '/tmp/audit8')
import engine_pt as E
titles = json.load(open('/tmp/audit9/titles.json'))      # {"1890-91": "...", ...} (optionally {"1890-91_p003": ...} per-page overrides)
CITIES = ('С.-ПЕТЕРБУРГЪ', 'МОСКВА')
log = []; fails = []
for f in sorted(glob.glob(E.R + 'productionteam_*.raw.json')):
    pg = f.split('/')[-1][:-9]; season = pg.split('_')[1]; page = pg.split('_', 1)[1]
    t = titles.get(page) or titles.get(season)
    if not t: fails.append((pg, 'no title')); continue
    for i, x in enumerate(E.load(pg)['entries']):
        c, hp = x.get('institution'), x.get('heading_path')
        if c not in CITIES: fails.append((pg, 'e%03d' % (i + 1), 'institution not a city', c)); continue
        if not hp or hp.split(' / ')[0] in CITIES: fails.append((pg, 'e%03d' % (i + 1), 'hp empty/already has city', hp)); continue
        log.append((pg, 'e%03d' % (i + 1), 'institution', c, t)); log.append((pg, 'e%03d' % (i + 1), 'heading_path', hp, c + ' / ' + hp))
        x['institution'] = t; x['heading_path'] = c + ' / ' + hp
print(len(log) // 2, 'rows;', len(fails), 'fails')
for z in fails[:20]: print(z)
if '--write' in sys.argv and not fails:
    E.write_all(); json.dump(log, open('/tmp/audit9/stage2b_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN')
