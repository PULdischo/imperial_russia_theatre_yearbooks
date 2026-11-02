"""B1 (person field audit 2026-11-01): restore printed leaving / death / transfer-out lines that the transcription dropped
or stored without an end date. Input: B1_final.csv (RG-approved rows only) with columns
entry_id, printed_line, end_date_text, end_type (left service | died | other), action (add_line | parse_only).
- add_line: the line is missing from the data. Append it verbatim to tenure_note_text and close the LAST service period.
- parse_only: the line is already stored (tenure note or tally text). If it sits in credit_summary_text, move it to
  tenure_note_text (the tally field keeps only the tally); close the last service period.
Field edits only (no entries added, removed or reordered), so entities.person_link stays aligned (issue #131).
Rulings applied: A2 (arrivals / secondments are never ends; not in the input), A3 (partial dates keep printed text).
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_b1_ends.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, sys, collections
from pathlib import Path

RAW = Path('outputs/full_run/raw')
D = Path(__file__).parent
INP = sys.argv[sys.argv.index('--input') + 1] if '--input' in sys.argv else D / 'B1_final.csv'
rows = list(csv.DictReader(open(INP, encoding='utf-8')))
by_page = collections.defaultdict(list)
for r in rows:
    page, idx = r['entry_id'].rsplit('__e', 1)
    by_page[page].append((int(idx), r))
n = collections.Counter()
for page, items in sorted(by_page.items()):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for idx, r in items:
        e = d['entries'][idx - 1]                      # entry ids are 1-based
        line = r['printed_line'].strip()
        sp = e.setdefault('service_periods', []) or e['service_periods']
        if not sp:
            sp.append({'start_date_text': None, 'end_date_text': None, 'end_type': None})
        last = sp[-1]
        assert not last.get('end_date_text') or r['action'] == 'parse_only', (r['entry_id'], last)
        if r['action'] == 'add_line':
            assert line not in (e.get('tenure_note_text') or '') + (e.get('credit_summary_text') or ''), (r['entry_id'], 'line already stored')
            e['tenure_note_text'] = ((e.get('tenure_note_text') or '').rstrip() + ' ' + line).strip()
        else:
            cs = e.get('credit_summary_text') or ''
            if line and line in cs:
                e['credit_summary_text'] = cs.replace(line, '').strip() or None
                e['tenure_note_text'] = ((e.get('tenure_note_text') or '').rstrip() + ' ' + line).strip()
                n['moved_from_tally'] += 1
        last['end_date_text'] = r['end_date_text'] or None
        last['end_type'] = r['end_type']
        n[r['action']] += 1
        print(f"{r['entry_id']:42} {e.get('family_name')!s:22} {r['action']:10} {r['end_type']:12} {r['end_date_text']}")
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(dict(n), f'on {len(by_page)} pages', '| WRITTEN' if '--write' in sys.argv else '| dry run')
