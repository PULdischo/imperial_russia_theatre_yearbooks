"""Рябцовъ, Владиміръ Александровичъ, BalletArtists Moscow 1901-02 no. 56 (balletartists_1901-02_MSK_p007, printed p. 118):
the one non-additive performance tally that had not been read on the scan (corpus-wide tally check, 2026-10-30). Read by Claude
on the full-resolution PDF image (pdf/Spiski_BalletArtists/ForUpload_1901-02_Spisok_BalletArtistsMoscow.pdf, page 8), zoomed:
the print has «въ 20 операхъ — 9», so 29 + 9 + 9 = 47 adds up and the stored «—3» was an extraction misread. Two more misreads
in the same entry: «Копекъ-горбунокъ» (print Конекъ-) and «дивертисементахъ» (print дивертиссементахъ). RG approved the fix
2026-10-30. The printed «20 операхъ» (twenty operas, nine performances) is left as printed: a probable print slip, not
confirmed (genuine_print_typos.md). Field edit only, applied to every string of the ONE entry; no entry added, removed or moved.
usage: uv run python docs/eval/raw_fix_ryabtsov_tally_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
PAGE, INDEX, FAMILY = 'balletartists_1901-02_MSK_p007', 9, 'Рябцовъ'
PAIRS = [('операхъ—3;', 'операхъ — 9;'), ('Копекъ-горбунокъ', 'Конекъ-горбунокъ'), ('дивертисементахъ', 'дивертиссементахъ')]


def fix(obj, old, new):
    n = 0
    for k, v in list(obj.items() if isinstance(obj, dict) else enumerate(obj)):
        if isinstance(v, str) and old in v:
            n += v.count(old); obj[k] = v.replace(old, new)
        elif isinstance(v, (dict, list)):
            n += fix(v, old, new)
    return n


f = RAW / f'{PAGE}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][INDEX - 1]
assert e['family_name'] == FAMILY and e['list_number'] == '56.', (e['family_name'], e['list_number'])
for old, new in PAIRS:
    n = fix(e, old, new); assert n >= 1, old
    print(f'{PAGE} no.{INDEX} {FAMILY}: «{old}» -> «{new}» x{n}')
opera = [c for c in e['credits'] if c['credit_type'] == 'category_totals' and c['label'] == 'операхъ']
assert len(opera) == 1 and opera[0]['count'] == 3, opera
opera[0]['count'] = 9
print(f'{PAGE} no.{INDEX} {FAMILY}: credits операхъ count 3 -> 9')
if '--write' in sys.argv:
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('WRITTEN' if '--write' in sys.argv else 'dry run')
