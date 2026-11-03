"""B8 (person field audit 2026-11-02): service-end kinds and dates per RG's rulings A1/A2/A8, plus scan-read corrections.
Input B8_final.csv (entry_id, period_order, action, value, now, basis, source). Actions on raw service_periods[period_order-1]:
  set_type       end_type = value (blank -> null)
  remove_end     end_date_text = end_type = null (arrivals, secondments, concurrent posts, graduates' arrival)
  set_date_text  end_date_text = value (scan-read correction; the parser re-derives the date)
  merge_periods  join this period with the next: keep this start, take the next period's end; drop the next period
  add_period     entry has no service period: add one with no dates and end_type = value (only when period_order is 1)
Pass another CSV of the same shape as the first argument (e.g. B9_undated_transfers.csv, 2026-11-02).
Field edits on service periods only: no entries added/removed/reordered (person_link unaffected).
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_b8_ends.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, sys, collections
from pathlib import Path

RAW = Path('outputs/full_run/raw'); D = Path(__file__).parent
src = next((a for a in sys.argv[1:] if a.endswith('.csv')), 'B8_final.csv')
rows = list(csv.DictReader(open(D / src, encoding='utf-8')))
by_page = collections.defaultdict(list)
for r in rows:
    page, idx = r['entry_id'].rsplit('__e', 1)
    by_page[page].append((int(idx), r))
n = collections.Counter(); problems = []
for page, items in sorted(by_page.items()):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    # merges last so period indexes stay valid for the other edits on the same entry
    for idx, r in sorted(items, key=lambda x: x[1]['action'] == 'merge_periods'):
        e = d['entries'][idx - 1]
        sp = e.get('service_periods') or []
        po = int(r['period_order']) - 1
        if r['action'] == 'add_period':
            if sp or po != 0:
                problems.append((r['entry_id'], r['period_order'], 'entry already has a period')); continue
            e['service_periods'] = [{'start_date_text': None, 'end_date_text': None, 'end_type': r['value']}]
            n['add_period'] += 1; continue
        if po >= len(sp):
            problems.append((r['entry_id'], r['period_order'], 'no such period')); continue
        p = sp[po]
        a = r['action']
        if a == 'set_type':
            if r['source'] == 'rules' and (p.get('end_type') or '') != r['now']:
                problems.append((r['entry_id'], r['period_order'], f"type now {p.get('end_type')!r}, expected {r['now']!r}")); continue
            p['end_type'] = r['value'] or None
        elif a == 'remove_end':
            p['end_date_text'] = None; p['end_type'] = None
        elif a == 'set_date_text':
            p['end_date_text'] = r['value']
        elif a == 'merge_periods':
            nxt = sp[po + 1]
            p['end_date_text'] = nxt.get('end_date_text'); p['end_type'] = nxt.get('end_type')
            del sp[po + 1]
        n[a] += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(dict(n), 'on', len(by_page), 'pages', '| WRITTEN' if '--write' in sys.argv else '| dry run')
print(len(problems), 'problems'); [print(' ', p) for p in problems[:30]]
