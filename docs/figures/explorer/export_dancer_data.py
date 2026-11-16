"""Export one record per dancer for the Dancer Tracker artifact. Reads outputs/full_run/imperial_theaters.duckdb read-only.

Scope and rules (RG, 2026-11-16):
- Dancers = everyone in a BalletArtists list, plus ballet-department graduates who never joined a troupe list.
- Repertoire bills print no casts. A dancer's roles come from the yearly tallies in the troupe lists
  (research.person_performance_tally); each role's work is matched to the Repertoire of that season and city by title,
  and that work's dated events are shown only as POSSIBLE events, never as ones the dancer is known to have danced.
  A tally title that matches no Repertoire work of that season and city gets no events (no guessing across titles).
- Review dances (research.review_dance + review_dance_performer) and linked review mentions are what names the dancer.
- Also: graduation (Graduates list), tenure (person_tenure + tenure notes), service periods, other lists,
  assignments, jubilee/obituary entries, death. No Wikidata.

usage: uv run python docs/figures/explorer/export_dancer_data.py  ->  docs/figures/explorer/dancers/{index,shard_NN}.json"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
OUT = Path(__file__).with_name('dancers')   # dancers/index.json + dancers/shard_NN.json (each file under the 16 MB artifact limit)
N_SHARDS = 32
con = duckdb.connect(str(DB), read_only=True)


def rows(sql, *a):
    cur = con.execute(sql, a)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def clean(d):
    """JSON-friendly: dates to ISO, drop None/empty/False to keep the file small."""
    out = {}
    for k, v in d.items():
        if v is None or v == '' or v is False:
            continue
        out[k] = v.isoformat() if hasattr(v, 'isoformat') else (str(v) if not isinstance(v, (int, float, str, bool, list, dict)) else v)
    return out


def norm_title(s):
    s = (s or '').lower().replace('ѣ', 'е').replace('і', 'и').replace('ѳ', 'ф').replace('ё', 'е')
    s = re.sub(r'ъ\b', '', s)
    s = re.sub(r'[^\w ]', ' ', s)
    return ' '.join(s.split())


# ---- the dancer set
con.execute("""CREATE TEMP TABLE dset AS
    SELECT DISTINCT person_id FROM research.person_appearance WHERE entity_type = 'BalletArtists'
    UNION SELECT DISTINCT person_id FROM research.person_appearance
          WHERE entity_type = 'Graduates' AND heading_path ILIKE '%балет%'""")
IN_D = 'person_id IN (SELECT person_id FROM dset)'

people = {r['person_id']: r for r in rows(f"""
    SELECT person_id::VARCHAR person_id, display_name, first_attested_season first_season, last_attested_season last_season
    FROM research.person WHERE {IN_D}""")}
rec = {pid: dict(id=pid, name=p['display_name'], printed=set(), apps=[], tenure=[], tnotes=[], periods=[], roles=[],
                 tallies=[], dances=[], mentions=[], jub=[], death=[], assign=[])
       for pid, p in people.items()}
for pid, p in people.items():
    rec[pid].update(clean(dict(first_season=p['first_season'], last_season=p['last_season'])))

# ---- list appearances (every list, not only ballet)
for r in rows(f"""SELECT appearance_id, person_id::VARCHAR pid, printed_family_name f, printed_first_name n, printed_patronymic p,
                         season, city, entity_type AS "list", institution, heading_path heading, rank, title, service_class,
                         subject_taught subject, instrument, tenure_note_text AS "note", printed_start_text AS "start",
                         printed_service_periods n_periods, credit_summary_text credits, source_file, scan_page, printed_folio folio
                  FROM research.person_appearance WHERE {IN_D} ORDER BY season, list, city"""):
    pid = r.pop('pid')
    rec[pid]['printed'].add(', '.join(x for x in (r.pop('f'), ' '.join(y for y in (r.pop('n'), r.pop('p')) if y)) if x))
    rec[pid]['apps'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, list, city, first_season, last_season, seasons_dated, tenure_start_date start_date,
                         start_precision, basis, printed_dates, ruling, later_period_start, broken_service_printed broken
                  FROM research.person_tenure WHERE {IN_D}"""):
    rec[r.pop('pid')]['tenure'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, list, city, printed_leaving, printed_in_seasons, research_reading, service_periods,
                         discrepancy, corroboration_found, corroboration_wanted, decided
                  FROM research.person_tenure_note WHERE {IN_D}"""):
    rec[r.pop('pid')]['tnotes'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, season, list, city, period_order n, start_text, start_date, end_text, end_date,
                         end_type, date_correction
                  FROM research.service_period WHERE {IN_D} ORDER BY season, list, period_order"""):
    rec[r.pop('pid')]['periods'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, season, list, city, kind, destination, start_text, end_text, printed_line
                  FROM research.person_assignment WHERE {IN_D}"""):
    rec[r.pop('pid')]['assign'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, source, season, printed_page, source_ref, printed_text, death_date, death_precision
                  FROM research.person_death WHERE {IN_D}"""):
    rec[r.pop('pid')]['death'].append(clean(r))

for r in rows(f"""SELECT person_id::VARCHAR pid, season, kind, relevance, name_verbatim, role, troupe_city, dates, evidence_verbatim,
                         evidence_english, notes, source_type, source_file, pdf_page, printed_page, author
                  FROM research.jubilee_obituary WHERE {IN_D} ORDER BY season"""):
    rec[r.pop('pid')]['jub'].append(clean(r))

# ---- Repertoire index: (season, city) -> normalised title -> work ids; (season, city, work) -> events
work_title = {r['w']: r['t'] for r in rows("SELECT work_id::VARCHAR w, canonical_title t FROM research.work")}
title_idx = defaultdict(lambda: defaultdict(set))
ev_by = defaultdict(dict)
for r in rows("""SELECT e.season, e.city, p.verbatim_title vt, w.canonical_title ct, w.work_id::VARCHAR w, e.event_id::VARCHAR ev,
                        e.date, e.date_verbatim dv, e.time_of_day tod, t.canonical_name th
                 FROM research.performance p JOIN research.event e USING (event_id) JOIN research.work w USING (work_id)
                 LEFT JOIN research.theater t ON t.theater_id = e.theater_id"""):
    for t in (r['vt'], r['ct']):
        title_idx[(r['season'], r['city'])][norm_title(t)].add(r['w'])
    ev_by[(r['season'], r['city'], r['w'])][r['ev']] = [str(r['date']) if r['date'] else None, r['dv'], r['tod'], r['th']]

events_out = {}   # shared lookup "season|city|work" -> sorted events, so dancers sharing a work don't repeat it

# ---- tallies: roles (matched to a work) and category/total lines
for r in rows(f"""SELECT person_id::VARCHAR pid, season, list, city, tally_order AS "o", tally_kind AS "kind", label, role_name, times_text,
                         "times", count_shared_with AS "shared"
                  FROM research.person_performance_tally WHERE {IN_D} ORDER BY season, city, tally_order"""):
    pid = r.pop('pid')
    if r['kind'] == 'role':
        ws = sorted(title_idx[(r['season'], r['city'])].get(norm_title(r['label']), ()))
        if ws:
            r['works'] = []
            for w in ws:
                key = f"{r['season']}|{r['city']}|{w}"
                if key not in events_out:
                    events_out[key] = sorted(ev_by[(r['season'], r['city'], w)].values(), key=lambda e: (e[0] or '', e[1] or ''))
                r['works'].append([w, key])
        rec[pid]['roles'].append(clean(r))
    else:
        rec[pid]['tallies'].append(clean(r))

# ---- review dances naming the dancer
for r in rows(f"""SELECT p.performer_person_id pid, d.season, d.city, d.printed_folio folio, d.date_undate AS "date", d.dance_surface dance,
                         d.work_surface, d.work_id::VARCHAR work_id, d.source, d.n_performers, p.is_alternate alternate,
                         p.performer_surface surface, d.printed_text AS "text"
                  FROM research.review_dance d JOIN research.review_dance_performer p USING (dance_id)
                  WHERE p.performer_person_id IN (SELECT person_id::VARCHAR FROM dset) ORDER BY d.season, d.city, d.printed_folio"""):
    pid = r.pop('pid')
    if r.get('work_id'):
        r['work'] = work_title.get(r['work_id'])
    rec[pid]['dances'].append(clean(r))

# ---- linked review mentions: a window of the passage around each mention, overlapping windows merged
W = 160
mrows = rows(f"""SELECT m.person_id::VARCHAR pid, m.block_id, m.season, m.city, m.char_start s, m.char_end e, m.surface,
                        m.role_name, coalesce(b.text, b.caption_text) AS "text", b.block_type = 'figure' AS caption, pg.printed_folio folio, pg.genre
                 FROM research.review_mention m JOIN research.review_passage b USING (block_id)
                 JOIN research.review_page pg ON pg.page_id = m.page_id
                 WHERE m.{IN_D} ORDER BY m.season, pg.printed_folio, m.block_id, m.char_start""")
groups = defaultdict(list)
for r in mrows:
    groups[(r['pid'], r['block_id'])].append(r)
for (pid, _), ms in groups.items():
    text = ms[0]['text'] or ''
    spans = []
    for m in ms:
        a, b = max(0, m['s'] - W), min(len(text), m['e'] + W)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], b); spans[-1][2].append(m)
        else:
            spans.append([a, b, [m]])
    for a, b, mm in spans:
        snippet = text[a:b]
        rec[pid]['mentions'].append(clean(dict(
            season=mm[0]["season"], city=mm[0]["city"], folio=mm[0]["folio"], genre=mm[0]["genre"], caption=mm[0]["caption"],
            pre=a > 0, post=b < len(text), text=snippet,
            hl=[[m['s'] - a, m['e'] - a] for m in mm],
            roles=sorted({m['role_name'] for m in mm if m['role_name']}) or None)))

out = []
for pid, r in rec.items():
    r['printed'] = sorted(r['printed'] - {r['name']})
    for sec in ('tallies', 'roles', 'periods'):   # the troupe list is the default; only other lists say so
        for x in r[sec]:
            if x.get('list') == 'BalletArtists':
                del x['list']
    out.append({k: v for k, v in r.items() if v not in ([], None, '')})
out.sort(key=lambda r: r['name'])

OUT.mkdir(exist_ok=True)
for old in OUT.glob('shard_*.json'):
    old.unlink()
shards = defaultdict(list)
index = []
for i, r in enumerate(out):
    sh = i % N_SHARDS
    shards[sh].append(r)
    apps = r.get('apps', [])
    index.append(dict(id=r['id'], name=r['name'], printed=r.get('printed', []), shard=sh,
                      first=r.get('first_season'), last=r.get('last_season'),
                      cities=sorted({a['city'] for a in apps if a.get('list') == 'BalletArtists' and a.get('city')}),
                      grad=any(a.get('list') == 'Graduates' for a in apps),
                      n=[len(r.get(k, [])) for k in ('roles', 'dances', 'mentions')]))
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
(OUT / 'index.json').write_text(dump(dict(dancers=index, events=events_out, built_from=str(DB.name))))
for sh, rs in shards.items():
    (OUT / f'shard_{sh:02d}.json').write_text(dump({r['id']: r for r in rs}))
sizes = sorted(p.stat().st_size for p in OUT.glob('*.json'))
print(f'{len(out)} dancers, {len(events_out)} season/city/work event lists, {sum(sizes)/1e6:.1f} MB in {len(sizes)} files '
      f'(largest {sizes[-1]/1e6:.2f} MB) -> {OUT}')
