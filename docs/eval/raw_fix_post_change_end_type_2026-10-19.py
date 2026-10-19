"""Service periods closed by an appointment, transfer or release, stored as end_type 'left service' (RG, 2026-10-19).
Found by the M9 scan checks (docs/eval/person_audit_2026-10-19/, group 1): notes such as «Назначенъ бухгалтеромъ 1 сентября
1904 г.», «Съ 1 сентября 1895 г. назначенъ чиновникомъ особыхъ порученій при Конторѣ», «Переведена въ Московскую балетную
труппу», «Освобожденъ отъ обязанностей балетмейстера 1 марта 1905 г., съ оставленіемъ артистомъ» close a POST, not the person's
service. RG: treat them as post changes, with the end type the parser already uses for transfers ('other', as for
«Переведенъ къ Московскимъ театрамъ»).

Rule (the entry's tenure note + credit line, lower-cased): contains назначен / освобожден / переведен / утвержден / произведен,
and contains none of оставил / остав. / уволен / вышел / выбыл / отчислен / умер / скончал / † / «по <digit>» (a printed period).
Only service periods with end_type 'left service' are touched; the end date text is kept. Field edit only: no entries added,
removed or reordered, so entities.person_link is unaffected.

usage: uv run python docs/eval/raw_fix_post_change_end_type_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, re, sys, collections
from pathlib import Path
import duckdb

RAW = Path('outputs/full_run/raw')
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
rows = con.execute(r"""
    select pe.entry_id, pe.page_id, s.period_order, s.end_date_text
    from raw.person_entry_service s join raw.person_entry pe using(entry_id)
    where s.end_type = 'left service'
      and lower(coalesce(pe.tenure_note_text,'') || ' ' || coalesce(pe.credit_summary_text,''))
          similar to '.*(назначен|освобожден|переведен|утвержден|произведен).*'
      and lower(coalesce(pe.tenure_note_text,'') || ' ' || coalesce(pe.credit_summary_text,''))
          not similar to '.*(оставил|остав\.|уволен|вышел|выбыл|отчислен|умер|скончал|†|по \d).*'
    order by 1""").fetchall()
con.close()
assert len(rows) == 28, len(rows)

by_page = collections.defaultdict(list)
for eid, page, order, edt in rows:
    by_page[page].append((int(eid.rsplit('__e', 1)[1]), int(order), edt, eid))

changed = 0
for page, items in sorted(by_page.items()):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for idx, order, edt, eid in items:
        e = d['entries'][idx - 1]          # entry_id numbers are 1-based (flatten_roster_page)
        sp = e['service_periods'][order - 1]
        assert sp.get('end_type') == 'left service' and (sp.get('end_date_text') or None) == (edt or None), (eid, sp, edt)
        print(f"{eid:40} {e.get('family_name')!s:22} {sp.get('end_date_text')!s:22} left service -> other")
        sp['end_type'] = 'other'
        changed += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{changed} service periods on {len(by_page)} pages', '| WRITTEN' if '--write' in sys.argv else '| dry run')
