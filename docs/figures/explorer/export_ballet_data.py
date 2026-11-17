"""Export every ballet work (research layer) for the Ballet Explorer artifact: performances per season and city, printed titles,
excerpts, productions-list entries, review counts,
box-office receipts of every event with a full performance, and per-season city baselines. Reads outputs/full_run/imperial_theaters.duckdb read-only.

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
    out[wid] = dict(id=wid, title=t, perf={}, xperf={}, xrows=[], titles=[], exc=[], lists=[], credits=cred.get(wid, 0), cast=cast.get(wid, 0))
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
# a list entry filed under an excerpt the list prints under its own title («Оживленный садъ», «Ѳетида и Пелей») is shown
# under the whole ballet, marked as an excerpt entry
parent_of = dict(q("SELECT work_id::VARCHAR, excerpt_of_work_id::VARCHAR FROM research.work WHERE excerpt_of_work_id IS NOT NULL"))
for wid, s, c, lt, prem, nd, pp, desc in lists:
    top = parent_of.get(wid, wid)
    if top in out:
        out[top]['lists'].append(dict(season=s, city=c, title=lt, premiere=bool(prem), dates=nd, page=pp, text=desc,
                                      excerpt=top != wid))
for w in out.values():
    w['titles'].sort(key=lambda x: -x[1]); w['exc'].sort(key=lambda x: -x[2]); w['lists'].sort(key=lambda x: (x['season'], x['city']))
    w['total'] = sum(sum(v.values()) for v in w['perf'].values())
    w['xtotal'] = len(w['xrows']); w['xrows'].sort(key=lambda r: (r['date'] or '', r['city']))
# ---- box office: every event with a FULL performance of the ballet (excerpts excluded). Receipts are printed once per event,
# so an event whose bill has other works ("shared bill", n_works > 1) carries a receipt for the whole bill, never split.
KIND = """CASE WHEN e.is_benefit THEN 'benefit' WHEN e.is_charity THEN 'charity' WHEN e.is_free THEN 'free'
               WHEN e.is_reduced_price THEN 'reduced' WHEN e.is_student_performance THEN 'school' ELSE '' END"""
box = q(f"""SELECT DISTINCT p.work_id::VARCHAR, e.event_id, e.season, e.city, e.date, e.date_verbatim, e.time_of_day,
                   e.receipts_total_kopecks, e.receipts_verbatim, e.receipts_source, e.n_works, {KIND}, e.printed_page_number
            FROM research.performance p JOIN research.event e USING (event_id) JOIN research.work w USING (work_id)
            WHERE w.art_form = 'ballet' AND w.excerpt_of_work_id IS NULL""")
bill = {}
for eid, wid, t in q("""SELECT p.event_id, p.work_id::VARCHAR, coalesce(w.canonical_title, p.verbatim_title) FROM research.performance p
                        LEFT JOIN research.work w USING (work_id) WHERE NOT coalesce(p.is_ceremonial, false)
                        ORDER BY p.event_id, p.performance_order"""):
    bill.setdefault(eid, []).append((wid, t))
for wid, eid, s, c, d, dv, tod, r, rv, src, nw, kind, pp in box:
    if wid not in out:
        continue
    others = [t for w2, t in bill.get(eid, []) if w2 != wid] if nw > 1 else []
    out[wid].setdefault('box', []).append(dict(season=s, city=c, date=d, dv=dv, tod=tod, r=r, rv=rv,
        fix=src not in (None, 'parsed'), shared=nw > 1, others=others, kind=kind, page=pp))
for w in out.values():
    w.setdefault('box', []).sort(key=lambda r: (r['date'] or '', r['city']))
# city baselines: per season and city, mean receipt of ORDINARY events (no benefit/charity/free/reduced/school wording) with any
# full ballet on the bill -- 'solo' = the ballet was the only work, 'all' = every such event; each event counted once
base = {}
for s, c, kind_solo, avg, n in q(f"""
        WITH b AS (SELECT DISTINCT e.event_id, e.season, e.city, e.n_works, e.receipts_total_kopecks r
                   FROM research.event e JOIN research.performance p USING (event_id) JOIN research.work w USING (work_id)
                   WHERE w.art_form = 'ballet' AND w.excerpt_of_work_id IS NULL AND e.receipts_total_kopecks IS NOT NULL
                     AND {KIND} = '')
        SELECT season, city, 'solo', avg(r), count(*) FROM b WHERE n_works = 1 GROUP BY 1, 2
        UNION ALL SELECT season, city, 'all', avg(r), count(*) FROM b GROUP BY 1, 2"""):
    base.setdefault(f'{s}|{c}', {})[kind_solo] = [round(avg), n]
# seasons in which the Repertoire prints no receipts at all (any work), so "no receipt" there is the source, not a gap
no_receipt_seasons = [s for s, in q("""SELECT season FROM research.event GROUP BY 1 HAVING count(receipts_total_kopecks) = 0""")]
# "every season at a glance" (same counting as Ballet Seasons by City, export_season_data.py): per season and city, each ballet's
# events = every event that gave any of it (full or an excerpt), full = events with the whole ballet; excerpts count under their ballet
from collections import defaultdict
g_any, g_full = defaultdict(set), defaultdict(set)
for top, is_x, s, c, ev in q("""SELECT coalesce(w.excerpt_of_work_id, w.work_id)::VARCHAR, w.excerpt_of_work_id IS NOT NULL, e.season, e.city,
                                      e.event_id::VARCHAR
                               FROM research.performance p JOIN research.work w USING (work_id) JOIN research.event e USING (event_id)
                               WHERE w.art_form = 'ballet'"""):
    g_any[(s, c, top)].add(ev)
    if not is_x: g_full[(s, c, top)].add(ev)
glance = {}
for (s, c, top), evs in g_any.items():
    glance.setdefault(f'{s}|{c}', []).append([top, len(evs), len(g_full[(s, c, top)])])
for v in glance.values(): v.sort(key=lambda x: (-x[1], x[0]))
from collections import Counter
dup = Counter(w['title'] for w in out.values())
for wid, w in out.items():
    if dup[w['title']] > 1:
        first = min(list(w['perf']) + list(w['xperf']) + [l['season'] for l in w['lists']], default=None)
        w['tag'] = ', '.join(x for x in (genre_of.get(wid), first and first.replace('-', '/')) if x)
seasons = sorted({s for s, in q("SELECT DISTINCT season FROM research.event")})
data = dict(works=sorted(out.values(), key=lambda w: w['title']), list_seasons=season_lists, seasons=seasons,
            box_base=base, no_receipt_seasons=no_receipt_seasons, glance=glance)
p = Path(__file__).with_name('ballets.json'); p.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(data['works']), 'ballets;', sum(w['total'] for w in out.values()), 'performances;', sum(w['xtotal'] for w in out.values()), 'excerpt performances;', p.stat().st_size // 1024, 'KB')
