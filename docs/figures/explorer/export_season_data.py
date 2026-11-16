"""Export ballets by season and city for the Season by City artifact. Reads outputs/full_run/imperial_theaters.duckdb read-only.

Rules (RG, 2026-11-16):
- Ballet only (research.work.art_form = 'ballet').
- Excerpts count under the ballet they come from (excerpt_of_work_id), in their own column. An event that gave the ballet in
  full counts as a full event even if it also gave an excerpt; "excerpt events" are events with an excerpt and no full
  performance, so full + excerpt = every event that gave any of the ballet. An excerpt alone counts the ballet as given in
  that city for the both-cities highlight.
- Creators come only from that season's productions-list entry for the same city (research.production_credit). No entry,
  no creators: nothing is borrowed from other seasons. Each credit shows its role group and the person's display name;
  the printed wording travels with it for the hover.
- The list's printed total is shown beside the Repertoire counts. A total that equals neither the full count nor full +
  excerpt is flagged. A list entry filed under an excerpt («Оживленный садъ») is compared with that excerpt's own events.
- List entries with no Repertoire events, and list entries not linked to any work, are kept as rows with zero events.

usage: uv run python docs/figures/explorer/export_season_data.py  ->  docs/figures/explorer/seasons.json"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
con = duckdb.connect(str(DB), read_only=True)
q = lambda s, *a: con.execute(s, a).fetchall()

title = dict(q("SELECT work_id::VARCHAR, canonical_title FROM research.work"))
genre = dict(q("SELECT work_id::VARCHAR, canonical_genre FROM research.work"))
parent_of = dict(q("SELECT work_id::VARCHAR, excerpt_of_work_id::VARCHAR FROM research.work WHERE excerpt_of_work_id IS NOT NULL"))
top_ballets = dict(q("SELECT work_id::VARCHAR, canonical_title FROM research.work WHERE art_form = 'ballet' AND excerpt_of_work_id IS NULL"))
first_of = dict(q("""SELECT coalesce(w.excerpt_of_work_id, w.work_id)::VARCHAR, min(e.season) FROM research.performance p
                     JOIN research.work w USING (work_id) JOIN research.event e USING (event_id) GROUP BY 1"""))
dup = Counter(top_ballets.values())   # two ballets sharing a title («Времена года») get a genre + first-season tag
tag = {w: ', '.join(x for x in (genre.get(w), (first_of.get(w) or '').replace('-', '/')) if x) for w, t in top_ballets.items() if dup[t] > 1}

# every (parent ballet, own work, season, city, event, is_excerpt) the Repertoire records
rows = q("""SELECT coalesce(w.excerpt_of_work_id, w.work_id)::VARCHAR, w.work_id::VARCHAR, w.excerpt_of_work_id IS NOT NULL,
                   e.season, e.city, e.event_id::VARCHAR, w.canonical_title
            FROM research.performance p JOIN research.work w USING (work_id) JOIN research.event e USING (event_id)
            WHERE w.art_form = 'ballet'""")
full_ev, any_ev, own_ev = defaultdict(set), defaultdict(set), defaultdict(set)
ex_titles = defaultdict(Counter)
city_ev = defaultdict(set)
for top, own, is_x, s, c, ev, t in rows:
    k = (s, c, top)
    any_ev[k].add(ev); own_ev[(s, c, own)].add(ev); city_ev[(s, c)].add(ev)
    if is_x: ex_titles[k][t] += 1
    else: full_ev[k].add(ev)

people = dict(q("SELECT person_id::VARCHAR, display_name FROM research.person"))
credits = defaultdict(list)
cred_rows = q("""SELECT pc.production_id::VARCHAR, pc.person_id::VARCHAR, pc.role_category, pc.role_text, pc.name_printed
                 FROM research.production_credit pc ORDER BY pc.production_id, pc.credit_order""")
for prod, pid, role, rtext, printed in cred_rows:
    credits[prod].append(dict(role=role, name=people.get(pid) or printed, printed=' '.join(x for x in (rtext, printed) if x)))

entries = defaultdict(list)   # (season, city, parent ballet or 'list:'+title) -> list entries
for prod, wid, s, c, lt, num, prem, tot, page in q(
        """SELECT production_id::VARCHAR, work_id::VARCHAR, season, city, list_title, list_number, is_premiere, printed_total,
                  printed_page_number FROM research.production"""):
    top = parent_of.get(wid, wid) if wid else 'list:' + lt
    own = len(own_ev[(s, c, wid)]) if wid and wid in parent_of else None
    entries[(s, c, top)].append(dict(list_title=lt, number=num, premiere=bool(prem), total=tot, page=page,
                                     excerpt=wid in parent_of if wid else False, own_events=own,
                                     linked=wid is not None, credits=credits.get(prod, [])))

seasons = sorted({s for s, c in city_ev} | {k[0] for k in entries})
list_seasons = sorted({k[0] for k in entries})
out = {}
for s in seasons:
    cities = {}
    for c in ('SP', 'Moscow'):
        keys = {k[2] for k in any_ev if k[:2] == (s, c)} | {k[2] for k in entries if k[:2] == (s, c)}
        bl = []
        for top in keys:
            k = (s, c, top)
            f, a = len(full_ev[k]), len(any_ev[k])
            ents = entries.get(k, [])
            for e in ents:   # flag a printed total that matches neither Repertoire count
                ref = [e['own_events']] if e['excerpt'] else [f, a]
                e['mismatch'] = e['total'] is not None and e['total'] not in ref
            bl.append(dict(id=top, title=top_ballets.get(top) or top.removeprefix('list:'), tag=tag.get(top),
                           full=f, excerpt=a - f, events=a,
                           excerpt_titles=[t for t, _ in ex_titles[k].most_common()], entries=ents))
        cities[c] = dict(ballets=bl, ballet_events=len(city_ev[(s, c)]))
    performed = {c: {b['id'] for b in cities[c]['ballets'] if b['events']} for c in cities}
    both = performed['SP'] & performed['Moscow']
    for c in cities:
        for b in cities[c]['ballets']:
            b['both'] = b['id'] in both
    out[s] = dict(cities=cities, has_list=s in list_seasons, shared=len(both))

data = dict(seasons=seasons, list_seasons=list_seasons, exported=__import__('datetime').date.today().strftime('%-d %b %Y'), data=out)
path = Path(__file__).with_name('seasons.json')
path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(seasons), 'seasons;', sum(len(v['cities'][c]['ballets']) for v in out.values() for c in v['cities']), 'season-city-ballet rows;',
      sum(v['shared'] for v in out.values()), 'shared season-ballets;',
      sum(e['mismatch'] for v in out.values() for c in v['cities'].values() for b in c['ballets'] for e in b['entries']), 'flagged totals;',
      path.stat().st_size // 1024, 'KB')
