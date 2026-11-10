"""Export ballet performances by composer for the Ballet Composers artifact. Reads outputs/full_run/imperial_theaters.duckdb read-only.

Composers come from the productions lists only (research.production_credit, role_category = 'music'). A performance in season S and
city C is attributed to the composers printed in that ballet's own list entry for S and C; where there is no such entry (no list
that season, or the ballet is not in it) it falls back to every composer any list credits for the ballet. A ballet with several
composers counts in full under each. Excerpts (works with excerpt_of_work_id) count under the parent ballet's composers.

usage: uv run python docs/figures/explorer/export_composer_data.py  ->  docs/figures/explorer/composers.json"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
con = duckdb.connect(str(DB), read_only=True)
q = lambda s, *a: con.execute(s, a).fetchall()

# ballets performed (in full or as excerpts) or listed
works = dict(q("""SELECT w.work_id::VARCHAR, w.canonical_title FROM research.work w
                  WHERE w.art_form = 'ballet' AND w.excerpt_of_work_id IS NULL"""))
# two different ballets can share a title («Времена года», «Карнавалъ»): label each with its printed genre and first season
genre_of = dict(q("SELECT work_id::VARCHAR, canonical_genre FROM research.work"))
first_of = dict(q("""SELECT coalesce(w.excerpt_of_work_id, w.work_id)::VARCHAR, min(e.season) FROM research.performance p
                     JOIN research.work w USING (work_id) JOIN research.event e USING (event_id) GROUP BY 1"""))
dup = Counter(works.values())
tag = {w: ', '.join(x for x in (genre_of.get(w), (first_of.get(w) or '').replace('-', '/')) if x)
       for w, t in works.items() if dup[t] > 1}
# full performances and excerpt performances, per parent ballet, season, city
perf = q("""SELECT coalesce(w.excerpt_of_work_id, w.work_id)::VARCHAR, w.excerpt_of_work_id IS NOT NULL, e.season, e.city, count(*)
            FROM research.performance p JOIN research.work w USING (work_id) JOIN research.event e USING (event_id)
            WHERE w.art_form = 'ballet' GROUP BY ALL""")
credits = q("""SELECT p.work_id::VARCHAR, p.season, p.city, pc.person_id::VARCHAR, pc.role_text, pc.name_printed,
                      p.printed_page_number, p.list_title
               FROM research.production_credit pc JOIN research.production p USING (production_id)
               WHERE pc.role_category = 'music' AND p.work_id IS NOT NULL""")
people = {pid: dict(name=dn, wd=wl, qid=qid) for pid, dn, wl, qid in
          q("SELECT person_id::VARCHAR, display_name, wikidata_label, wikidata_qid FROM research.person")}
list_seasons = sorted(s for s, in q("SELECT DISTINCT season FROM research.production"))

by_entry = defaultdict(set)     # (work, season, city) -> composers printed in that entry
by_work = defaultdict(set)      # work -> every composer any list credits
entries = defaultdict(list)     # (composer, work) -> printed credits
forms = defaultdict(lambda: defaultdict(int))
for wid, s, c, pid, role, name, page, lt in credits:
    by_entry[(wid, s, c)].add(pid); by_work[wid].add(pid)
    entries[(pid, wid)].append(dict(season=s, city=c, role=role, name=name, page=page))
    forms[pid][name] += 1

comp = {}   # composer -> {ballet -> {'f': {season: {city: n}}, 'x': ...}}
uncredited = defaultdict(lambda: dict(f=0, x=0, where=set()))
for wid, is_x, s, c, n in perf:
    if wid not in works:
        continue
    who = by_entry.get((wid, s, c)) or by_work.get(wid)
    if not who:
        uncredited[wid]['x' if is_x else 'f'] += n
        uncredited[wid]['where'].add(s + ' ' + c)
        continue
    basis = 'entry' if (wid, s, c) in by_entry else 'fallback'
    for pid in who:
        b = comp.setdefault(pid, {}).setdefault(wid, dict(f={}, x={}, basis={}))
        d = b['x' if is_x else 'f'].setdefault(s, {}); d[c] = d.get(c, 0) + n
        b['basis'].setdefault(s, {})[c] = basis
# composers credited in a list but with no performances still appear
for (pid, wid) in entries:
    comp.setdefault(pid, {}).setdefault(wid, dict(f={}, x={}, basis={}))

out = []
for pid, ballets in comp.items():
    bl = []
    for wid, b in ballets.items():
        others = sorted(people[o]['name'] for o in by_work[wid] if o != pid)
        bl.append(dict(title=works.get(wid, '?'), tag=tag.get(wid), f=b['f'], x=b['x'], basis=b['basis'], others=others,
                       credits=sorted(entries.get((pid, wid), []), key=lambda e: (e['season'], e['city'])),
                       ftotal=sum(sum(v.values()) for v in b['f'].values()), xtotal=sum(sum(v.values()) for v in b['x'].values())))
    bl.sort(key=lambda b: (-b['ftotal'], b['title']))
    p = people[pid]
    out.append(dict(name=p['name'], wd=p['wd'], qid=p['qid'], forms=sorted(forms[pid].items(), key=lambda x: -x[1]), ballets=bl,
                    ftotal=sum(b['ftotal'] for b in bl), xtotal=sum(b['xtotal'] for b in bl)))
out.sort(key=lambda c: c['name'])
unc = sorted(([works[w] + (f' ({tag[w]})' if w in tag else ''), v['f'], v['x'], sorted(v['where'])] for w, v in uncredited.items()), key=lambda x: -x[1])
data = dict(composers=out, uncredited=unc, list_seasons=list_seasons)
path = Path(__file__).with_name('composers.json')
path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(out), 'composers;', sum(len(c['ballets']) for c in out), 'composer-ballet pairs;', len(unc), 'performed ballets with no music credit;',
      path.stat().st_size // 1024, 'KB')
