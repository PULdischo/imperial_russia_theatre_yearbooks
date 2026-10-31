"""BalletArtists: performance tallies printed but never transcribed (RG, 2026-10-31: "yes, start the transcription").
The sweep (docs/eval/copied_tallies_2026-10-30/sweep/) found three pages whose entries had no tally fields at all -- 1891-92 MSK
p005, 1895-96 SP p008, 1905-06 SP p006 -- and two single entries (1892-93 MSK p002 no. 47 Кольева, printed «Копьева»; 1906-07 MSK
p005 no. 20 Евлановъ). Each was transcribed blind by two readers (docs/eval/copied_tallies_2026-10-30/transcription/read_*.tsv):
98 of 100 readings agreed outright; the 2 letter differences read by Claude on the scan («Дочь фараопа», «герцогь», both misprints,
stored as printed). Final text: transcription/final_tallies.tsv. Credit rows built by transcription/tally_parse.py (one row per
category total and per role, as the extraction does). Рыжевъ (1891-92), Пишо and Степановъ (1895-96) print no tally.
Adds credit_summary_text and credits to these 80 entries; no entry added, removed or moved; service notes untouched.
usage: uv run python docs/eval/raw_fix_transcribe_missing_tallies_2026-10-31.py [--write]; then rebuild_after_raw_edit.sh"""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'copied_tallies_2026-10-30' / 'transcription'))
from tally_parse import credits

RAW = Path('outputs/full_run/raw')
rows = list(csv.DictReader(open(Path(__file__).parent / 'copied_tallies_2026-10-30/transcription/final_tallies.tsv'), delimiter='\t'))
assert len(rows) == 80
pages, odd = {}, []
for r in rows:
    pid, i = r['entry_id'].rsplit('__e', 1)
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][int(i) - 1]
    assert not e.get('credit_summary_text') and not e.get('credits'), r['entry_id']
    t = r['tally'] or None
    e['credit_summary_text'] = t
    e['credits'] = credits(t) if t else []
    if t:
        c = e['credits']; tot = [x['count'] for x in c if x['label'] == 'Всего']
        parts = [x['count'] for x in c if x['credit_type'] == 'category_totals' and x['label'] != 'Всего']
        if not tot or (parts and sum(parts) != tot[0]): odd.append((r['entry_id'], parts, tot, t[:90]))
print('not additive or no total:', len(odd))
for o in odd: print(' ', o)
if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(rows), 'entries,', len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
