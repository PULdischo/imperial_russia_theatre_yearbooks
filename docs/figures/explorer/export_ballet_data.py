"""Export every ballet work (research layer) for the Ballet Explorer artifact: performances per season and city, printed titles,
excerpts, productions-list entries, review counts. Reads outputs/full_run/imperial_theaters.duckdb read-only.

usage: uv run python docs/figures/explorer/export_ballet_data.py  ->  docs/figures/explorer/ballets.json"""
import json, sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
con = duckdb.connect(str(DB), read_only=True)
q = lambda s, *a: con.execute(s, a).fetchall()

works = q("""SELECT w.work_id::VARCHAR, w.canonical_title FROM research.work w
             WHERE w.art_form = 'ballet' AND w.excerpt_of_work_id IS NULL
               AND (EXISTS (SELECT 1 FROM research.performance p WHERE p.work_id = w.work_id)
                    OR EXISTS (SELECT 1 FROM research.production r WHERE r.work_id = w.work_id)
                    OR EXISTS (SELECT 1 FROM research.work x JOIN research.performance p ON p.work_id = x.work_id
                               WHERE x.excerpt_of_work_id = w.work_id))""")
perf = q("""SELECT p.work_id::VARCHAR, e.season, e.city, count(*) FROM research.performance p JOIN research.event e USING (event_id)
            GROUP BY ALL""")
titles = q("SELECT work_id::VARCHAR, verbatim_title, count(*) FROM research.performance WHERE verbatim_title IS NOT NULL GROUP BY ALL")
exc = q("""SELECT w.excerpt_of_work_id::VARCHAR, w.canonical_title, e.city, count(*) FROM research.work w
           JOIN research.performance p ON p.work_id = w.work_id JOIN research.event e USING (event_id)
           WHERE w.excerpt_of_work_id IS NOT NULL GROUP BY ALL""")
# every excerpt performance (a single act, scene or number of the ballet), for the excerpt view
xrows = q("""SELECT w.excerpt_of_work_id::VARCHAR, e.season, e.city, e.date, e.time_of_day, t.canonical_name, e.printed_page_number,
                   coalesce(p.verbatim_title, w.canonical_title), p.verbatim_genre
            FROM research.work w JOIN research.performance p ON p.work_id = w.work_id JOIN research.event e USING (event_id)
            LEFT JOIN research.theater t USING (theater_id)
            WHERE w.excerpt_of_work_id IS NOT NULL""")
lists = q("""SELECT work_id::VARCHAR, season, city, list_title, is_premiere, n_dates, printed_page_number, description_text
             FROM research.production WHERE work_id IS NOT NULL""")
cred = dict(q("SELECT work_id::VARCHAR, count(*) FROM research.review_credit WHERE work_id IS NOT NULL GROUP BY 1"))
cast = dict(q("SELECT work_id::VARCHAR, count(*) FROM research.review_assertion WHERE work_id IS NOT NULL GROUP BY 1"))
season_lists = sorted({s for s, in q("SELECT DISTINCT season FROM research.production")})
# two different ballets can share a title («Времена года», «Карнавалъ»): label each with its printed genre and first season
genre_of = dict(q("SELECT work_id::VARCHAR, canonical_genre FROM research.work"))

out = {}
for wid, t in works:
    out[wid] = dict(title=t, perf={}, xperf={}, xrows=[], titles=[], exc=[], lists=[], credits=cred.get(wid, 0), cast=cast.get(wid, 0))
for wid, s, c, n in perf:
    if wid in out:
        out[wid]['perf'].setdefault(s, {})[c] = n
for wid, t, n in titles:
    if wid in out:
        out[wid]['titles'].append([t, n])
for wid, t, c, n in exc:
    if wid in out:
        out[wid]['exc'].append([t, c, n])
for wid, s, c, d, tod, th, pp, t, g in xrows:
    if wid in out:
        out[wid]['xperf'].setdefault(s, {})
        out[wid]['xperf'][s][c] = out[wid]['xperf'][s].get(c, 0) + 1
        out[wid]['xrows'].append(dict(season=s, city=c, date=d, session=tod, theater=th, page=pp, text=t, genre=g))
for wid, s, c, lt, prem, nd, pp, desc in lists:
    if wid in out:
        out[wid]['lists'].append(dict(season=s, city=c, title=lt, premiere=bool(prem), dates=nd, page=pp, text=desc))
for w in out.values():
    w['titles'].sort(key=lambda x: -x[1]); w['exc'].sort(key=lambda x: -x[2]); w['lists'].sort(key=lambda x: (x['season'], x['city']))
    w['total'] = sum(sum(v.values()) for v in w['perf'].values())
    w['xtotal'] = len(w['xrows']); w['xrows'].sort(key=lambda r: (r['date'] or '', r['city']))
from collections import Counter
dup = Counter(w['title'] for w in out.values())
for wid, w in out.items():
    if dup[w['title']] > 1:
        first = min(list(w['perf']) + list(w['xperf']) + [l['season'] for l in w['lists']], default=None)
        w['tag'] = ', '.join(x for x in (genre_of.get(wid), first and first.replace('-', '/')) if x)
data = dict(works=sorted(out.values(), key=lambda w: w['title']), list_seasons=season_lists)
p = Path(__file__).with_name('ballets.json'); p.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(data['works']), 'ballets;', sum(w['total'] for w in out.values()), 'performances;', sum(w['xtotal'] for w in out.values()), 'excerpt performances;', p.stat().st_size // 1024, 'KB')
