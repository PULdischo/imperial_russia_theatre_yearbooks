"""R9: a person's LAST listing in a list (city + list type), before 1910-11, with no end date stored.
Did the print give a leaving / death / transfer / appointment line that the transcription dropped?
Writes r9_worklist.csv (one row per entry) and slices/r9_sliceN.csv grouped by page."""
import csv, collections
from pathlib import Path
import duckdb
D = Path(__file__).parent
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
rows = con.execute("""
with a as (select pl.person_id, sp.season, coalesce(sp.city,'') city, pe.entity_type et, pe.entry_id, pe.page_id, pe.list_number,
                  pe.family_name, pe.first_name, pe.patronymic, pe.tenure_note_text n, pe.credit_summary_text c, sp.source_page_index
           from raw.person_entry pe join raw.source_pages sp using(page_id) join entities.person_link pl using(entry_id) where pe.entity_type<>'Graduates'),
last as (select person_id, city, et, max(season) ls from a group by all)
select a.et, a.season, a.city, a.page_id, a.entry_id, a.list_number, a.family_name, a.first_name, a.patronymic, a.n, a.c,
       regexp_matches(coalesce(a.n,'')||coalesce(a.c,''),'(Оставил|†|Умер|ереведен|азначен|Уволен)') has_text
from a join last l on l.person_id=a.person_id and l.city=a.city and l.et=a.et and l.ls=a.season
where a.season<'1910-11' and not exists (select 1 from raw.person_entry_service s where s.entry_id=a.entry_id and s.end_date_undate is not null)
order by case a.et when 'BalletArtists' then 0 else 1 end, a.page_id, a.entry_id""").fetchall()
H = ['item', 'list', 'season', 'city', 'page_id', 'entry_id', 'list_no', 'stored_name', 'stored_tenure_note', 'stored_credit_summary', 'leaving_text_already_stored']
out = [[i + 1, et, s, c, p, e, ln or '', f'{f} | {fi or ""} | {pa or ""}', n or '', cs or '', 'yes' if ht else 'no'] for i, (et, s, c, p, e, ln, f, fi, pa, n, cs, ht) in enumerate(rows)]
with open(D / 'r9_worklist.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow(H); w.writerows(out)
ballet = [r for r in out if r[1] == 'BalletArtists']; rest = [r for r in out if r[1] != 'BalletArtists']
def split(rs, n):
    pages = collections.OrderedDict()
    for r in rs: pages.setdefault(r[4], []).append(r)
    sl = [[] for _ in range(n)]; tot = len(rs); acc = 0; i = 0
    for p, rr in pages.items():
        sl[min(i, n - 1)] += rr; acc += len(rr)
        if acc >= tot / n * (i + 1): i += 1
    return sl
for k, sl in enumerate(split(ballet, 2) + split(rest, 3), 1):
    with open(D / f'slices/r9_slice{k}.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(H); w.writerows(sl)
    print('r9 slice', k, len(sl), 'items', len({r[4] for r in sl}), 'pages')
print(len(out), collections.Counter(r[1] for r in out))
