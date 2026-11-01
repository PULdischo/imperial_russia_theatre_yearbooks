"""Leaving / transfer / death audit worklists (RG 2026-11-01: "we never really audited leaving dates, moving dates, and death notices").
D1: every stored service end (end date or end type) -> read on the scan: date, kind, and that it belongs to this person.
D2: a person's listing just before a GAP in the same list (absent next season, back later) with no end stored -> dropped note?
Writes d1_worklist.csv, d2_worklist.csv and slices/d1_sliceN.csv, d2_sliceN.csv grouped by page."""
import csv, collections
from pathlib import Path
import duckdb
D = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
H = ['item', 'list', 'season', 'city', 'page_id', 'entry_id', 'list_no', 'stored_name', 'stored_tenure_note', 'stored_credit_summary', 'stored_end']
d1 = con.execute("""
select pe.entity_type, sp.season, coalesce(sp.city,''), pe.page_id, pe.entry_id, pe.list_number, pe.family_name, pe.first_name, pe.patronymic,
       pe.tenure_note_text, pe.credit_summary_text,
       string_agg(coalesce(s.end_date_text,'?')||' -> '||coalesce(cast(s.end_date_undate as varchar),'?')||' ['||coalesce(s.end_type,'no type')||']', ' ; ' order by s.period_order)
from raw.person_entry pe join raw.source_pages sp using(page_id) join raw.person_entry_service s using(entry_id)
where s.end_date_text is not null or s.end_date_undate is not null or s.end_type is not null
group by all order by pe.page_id, pe.entry_id""").fetchall()
d2 = con.execute("""
with a as (select pl.person_id, sp.season, coalesce(sp.city,'') city, pe.entity_type et, pe.entry_id from raw.person_entry pe
           join raw.source_pages sp using(page_id) join entities.person_link pl using(entry_id) where pe.entity_type<>'Graduates'),
s as (select distinct season from raw.source_pages where season is not null),
o as (select season, row_number() over (order by season) k from s),
b as (select a.*, o.k from a join o using(season)),
g as (select b.* from b where not exists (select 1 from b b2 where b2.person_id=b.person_id and b2.city=b.city and b2.et=b.et and b2.k=b.k+1)
                        and exists (select 1 from b b3 where b3.person_id=b.person_id and b3.city=b.city and b3.et=b.et and b3.k>b.k+1))
select pe.entity_type, sp.season, coalesce(sp.city,''), pe.page_id, pe.entry_id, pe.list_number, pe.family_name, pe.first_name, pe.patronymic,
       pe.tenure_note_text, pe.credit_summary_text, ''
from g join raw.person_entry pe using(entry_id) join raw.source_pages sp using(page_id)
where not exists (select 1 from raw.person_entry_service s where s.entry_id=g.entry_id and s.end_date_undate is not null)
order by pe.page_id, pe.entry_id""").fetchall()
def dump(name, rows, n):
    out = [[i + 1, et, s, c, p, e, ln or '', f'{f} | {fi or ""} | {pa or ""}', nt or '', cs or '', end] for i, (et, s, c, p, e, ln, f, fi, pa, nt, cs, end) in enumerate(rows)]
    with open(D / f'{name}_worklist.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(H); w.writerows(out)
    pages = collections.OrderedDict()
    for r in out: pages.setdefault(r[4], []).append(r)
    sl = [[] for _ in range(n)]; acc = 0; i = 0
    for p, rr in pages.items():
        sl[min(i, n - 1)] += rr; acc += len(rr)
        if acc >= len(out) / n * (i + 1): i += 1
    for k, x in enumerate(sl, 1):
        with open(D / f'slices/{name}_slice{k}.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh); w.writerow(H); w.writerows(x)
    print(name, len(out), 'rows', len(pages), 'pages', collections.Counter(r[1] for r in out), [len(x) for x in sl])
dump('d1', d1, 6)
dump('d2', d2, 2)
