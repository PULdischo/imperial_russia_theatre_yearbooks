"""BalletArtists Moscow 1902-04: totals whose last digit is an italic 3/8 that the print does not distinguish (RG, 2026-10-31:
"yes make the corrections" -- store the reading the parts support, note the ambiguity). Read by Claude on the scans, zoomed
(docs/eval/copied_tallies_2026-10-30/sweep/digit_reads_2026-10-31.csv, group D).
  1903-04 MSK p005 no. 2 Бакинъ 2-й: «Всего—7[3/8] раза», parts 36+37=73 -> 73 (stored 78)
  1902-03 MSK p000 no. 8 Боткина: «Всего—[3/8]6 разъ», parts 26+10=36 -> 36 (stored 86)
  1903-04 MSK p008 no. 79 Шеншинъ: «Всего—5[3/8]», parts 28+25=53 -> already stored 53, unchanged.
Field edits only. usage: uv run python docs/eval/raw_fix_italic_3_8_totals_2026-10-31.py [--write]; then rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
pages = {}
for page, i, fam, old, new, n_old, n_new in [('1903-04_MSK_p005', 2, 'Бакинъ 2-й', 'Всего—78 раза', 'Всего—73 раза', 78, 73),
                                             ('1902-03_MSK_p000', 13, 'Боткина', 'Всего—86 разъ', 'Всего—36 разъ', 86, 36)]:
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][i - 1]
    assert e['family_name'] == fam and e['credit_summary_text'].count(old) == 1, (fam, e['credit_summary_text'])
    e['credit_summary_text'] = e['credit_summary_text'].replace(old, new)
    tot = [c for c in e['credits'] if c['label'] == 'Всего']; assert len(tot) == 1 and tot[0]['count'] == n_old; tot[0]['count'] = n_new
e = json.loads((RAW / 'balletartists_1903-04_MSK_p008.raw.json').read_text(encoding='utf-8'))['entries'][11]
assert e['family_name'] == 'Шеншинъ' and 'Всего—53' in e['credit_summary_text']
if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
