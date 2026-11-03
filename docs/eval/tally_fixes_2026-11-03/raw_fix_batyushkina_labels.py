"""«ком. Батюшкина дочка—въ бал. Своенравная жена (part—N)»: one item label for every entry that prints it (RG 2026-11-03, "Yes, full
label"; docs/research_layer_review_2026-11-03.md). 28 BalletArtists entries, SP 1893-94 and 1894-95, all print the same line; the
stored item had four shapes (full phrase, ballet only, comedy only, ballet inside the part). Only the item `label` (and the part
where the ballet sat inside it) changes; the tally text stays as printed, except two part names scan-checked by Claude 2026-11-03:
«коранщикъ» -> «корзинщикъ» (Кшесинскій 2-й 1894-95 p.53 no.30) and «поварь» -> «поваръ» (Сергѣевъ 1894-95 p.54 no.57).
Every old value is asserted; a second run changes nothing and says so.

usage: uv run python docs/eval/tally_fixes_2026-11-03/raw_fix_batyushkina_labels.py --raw-dir <dir> [--write]"""
import argparse, json
from pathlib import Path

LABEL = 'ком. Батюшкина дочка—въ бал. Своенравная жена'
OLD_LABELS = {'Своенравная жена', 'Батюшкина дочка', 'ком. Батюшкина дочка', 'ком. Батюшкина дочка — въ бал. Своенравная жена'}
PART_FIXES = {  # entry_id: (old part, new part), also replaced in the tally text
    'balletartists_1894-95_SP_p006__e015': ('коранщикъ', 'корзинщикъ'),
    'balletartists_1894-95_SP_p007__e018': ('поварь', 'поваръ'),
}
TEXT_FIXES = {  # entry_id: (old, new) in the tally text; read on the scan by RG 2026-11-03 (smudged page)
    'balletartists_1893-94_SP_p008__e008': ('въ бал: Своенравная', 'въ бал. Своенравная'),   # Ширяевъ p.65 no.71: "it's a period"
}
EXPECTED_ENTRIES = 28


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True, type=Path)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    seen, changed = 0, 0
    for f in sorted(a.raw_dir.glob('balletartists_189*_SP_p*.raw.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        dirty = False
        for i, e in enumerate(d['entries'], 1):
            if 'Батюшкина дочка' not in (e.get('credit_summary_text') or ''):
                continue
            seen += 1
            eid = f'{f.name[:-len(".raw.json")]}__e{i:03d}'
            hits = [c for c in e.get('credits') or []
                    if c.get('credit_type') == 'named_work' and (c.get('label') in OLD_LABELS or c.get('label') == LABEL)]
            assert len(hits) == 1, (eid, hits)
            c = hits[0]
            before = dict(c)
            if c['label'] != LABEL:
                c['label'] = LABEL
            role = c.get('role_name') or ''
            if role.startswith('Своенравная жена ('):          # Куличевская 1894-95: «Своенравная жена (графиня)»
                c['role_name'] = role[len('Своенравная жена ('):].rstrip(')')
            if eid in PART_FIXES:
                old, new = PART_FIXES[eid]
                if c['role_name'] == old:
                    c['role_name'] = new
                    t = e['credit_summary_text']
                    assert t.count(f'({old}') == 1, (eid, t)
                    e['credit_summary_text'] = t.replace(f'({old}', f'({new}')
                else:
                    assert c['role_name'] == new, (eid, c)
            assert c['role_name'] and isinstance(c['count'], int), (eid, c)
            if eid in TEXT_FIXES:
                old, new = TEXT_FIXES[eid]
                t = e['credit_summary_text']
                if old in t:
                    assert t.count(old) == 1, (eid, t)
                    e['credit_summary_text'] = t.replace(old, new); dirty = True
                    print(eid, e['family_name'], '| text:', old, '->', new)
                else:
                    assert new in t, (eid, t)
            if c != before:
                changed += 1; dirty = True
                print(eid, e['family_name'], '|', before.get('label'), '<', before.get('role_name'), '> ->', c['label'], '<', c['role_name'], '>', c['count'])
        if dirty and a.write:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    assert seen == EXPECTED_ENTRIES, seen
    print(f'{seen} entries print the line; {changed} changed', '| WRITTEN' if a.write else '| dry run')


if __name__ == '__main__':
    main()
