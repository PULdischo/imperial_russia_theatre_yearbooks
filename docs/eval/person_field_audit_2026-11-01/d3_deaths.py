"""D3: deaths in the jubilee/obituary catalogue vs the roster's stored deaths (no scans). Read-only.
For every catalogue death notice linked to a person: is a died end stored? same date? And roster deaths with
no catalogue entry are listed for completeness. Writes D3_deaths.csv."""
import csv, re, collections
from pathlib import Path
import duckdb
D = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
EN = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)
RU = {m: i + 1 for i, m in enumerate('январ феврал март апрѣл ма іюн іюл август сентябр октябр ноябр декабр'.split())}
def parse(s):
    s = s or ''
    m = re.search(r'(?:d\.|†|died)\s*(\d{1,2})(?:\s*\(\d+\))?\s+([A-Za-z]{3})\w*\.?\s+(\d{4})', s)
    if m and m.group(2).lower()[:3] in EN: return f"{m.group(3)}-{EN[m.group(2).lower()[:3]]:02d}-{int(m.group(1)):02d}"
    m = re.search(r'†\s*(\d{1,2})(?:-го)?\s+([а-яѣі]+)\s+(\d{4})', s)
    if m:
        for k, v in RU.items():
            if m.group(2).startswith(k): return f"{m.group(3)}-{v:02d}-{int(m.group(1)):02d}"
    m = re.search(r'(?:d\.|†|died|умер)\D{0,12}(\d{4})', s)
    return m.group(1) if m else ''
ent = {}
for r in csv.DictReader(open('docs/jubilees_obituaries/jubilees_obituaries_all_entries.csv', encoding='utf-8')):
    ent.setdefault((r['season'], r['name_verbatim']), r)
links = list(csv.DictReader(open('docs/jubilees_obituaries/jubilees_obituaries_person_links.csv', encoding='utf-8')))
died = collections.defaultdict(list)
for pid, d, txt, eid, season in con.execute("""select cast(pl.person_id as varchar), cast(s.end_date_undate as varchar), s.end_date_text, pe.entry_id, sp.season
    from raw.person_entry_service s join raw.person_entry pe using(entry_id) join raw.source_pages sp using(page_id)
    join entities.person_link pl using(entry_id) where s.end_type='died'""").fetchall():
    died[pid].append((d, txt, eid, season))
lastseen = dict(con.execute("select cast(person_id as varchar), last_attested_season from research.person").fetchall())
name = dict(con.execute("select cast(person_id as varchar), display_name from research.person").fetchall())
out = []; seen_p = set()
for l in links:
    if l['link_status'] != 'linked' or l['kind'] not in ('obituary', 'death_mark', 'death_notice'): continue
    e = ent.get((l['season'], l['name_verbatim']), {})
    cd = parse(e.get('dates', '')) or parse(e.get('evidence_verbatim', ''))
    pid = l['person_id']; seen_p.add(pid)
    rd = sorted({x[0] for x in died.get(pid, []) if x[0]})
    if not rd: v = 'no died end stored'
    elif not cd: v = 'catalogue date not parsed'
    elif cd in rd or any(r[:len(cd)] == cd for r in rd): v = 'agree'
    elif any(r[:4] == cd[:4] for r in rd): v = 'same year, different day/month'
    else: v = 'different year'
    out.append((v, l['kind'], l['source_type'], l['season'], l['name_verbatim'], name.get(pid, '?'), cd, ';'.join(rd), lastseen.get(pid, ''), (e.get('dates') or '')[:120]))
for pid, xs in died.items():
    if pid not in seen_p:
        out.append(('roster death, not in catalogue links', '', 'roster', xs[0][3], '', name.get(pid, '?'), '', ';'.join(sorted({x[0] or '' for x in xs})), lastseen.get(pid, ''), ''))
out.sort(key=lambda r: (r[0], r[3]))
with open(D / 'D3_deaths.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(['verdict', 'kind', 'source', 'season', 'name_in_catalogue', 'person', 'catalogue_death', 'stored_died_dates', 'last_listed', 'catalogue_dates_field']); w.writerows(out)
print(collections.Counter(r[0] for r in out))
