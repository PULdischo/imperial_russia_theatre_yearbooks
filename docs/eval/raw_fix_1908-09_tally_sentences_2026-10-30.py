"""1908-09 BalletArtists, the italic «Всего» tally sentence (RG, 2026-10-30: "yes go ahead" on fixing the «въ» misreads).

The 1908-09 lists set the tally in italic: «Всего—въ 6 балетахъ—19 разъ.» Italic ъ looks like «в», so extraction stored the
preposition as «всѣ» (68), «вв» (54+5), «88» (7) or dropped it (MSK p006, 14). Every tally sentence of all 16 pages
(MSK p001-p007, SP p000-p008; 168 entries) was read on the scans by four parallel readers
(scratchpad reads vse_reads_group1-4.tsv, summarised in known_issues.md); the data-changing findings were re-read by Claude.
Corrections, all to the printed text:
  P  the word after «Всего—» set to «въ» wherever the print has it; Бочаровъ 2-й (SP p005 no. 11) and Ларіонова (MSK p002 no. 42)
     print no «въ» and are left without it.
  H  «Все-то» / «Все-ю» -> «Все-го» (the word is hyphenated at a line break in print; 5 entries).
  E  singular «1 балетъ» / «1 балетахъ» -> «1 балетѣ», «1 оперъ» -> «1 оперѣ» (italic ѣ looks like «ть»; every singular read
     prints ѣ), in the sentence and in the matching category credit label.
  N  Григорьевъ (SP p005 no. 17): «—27 разъ» -> «—21 разъ» (Claude read 21; the ten roles sum to 21), sentence and credit count.
  X  Three entries with NO printed credit line carried a copy of a neighbour's tally (the carry-over at the top of a column, or
     the next entry's): Тренинская (MSK p003 no. 73, copy of no. 72's tail), Рыхлякова 2-я (SP p003 no. 81, copy of no. 80's
     tail), Александрова (SP p000 Артистки no. 1, copy of no. 4 Бакеркина). credit_summary_text -> null, credits -> [].
     Re-read by Claude on the scan. The owners (nos. 72, 80, 4) already hold their full tally.
  Print slips are stored as printed (genuine_print_typos.md): Фокинъ (SP p008 no. 73) «балетахь».
Field edits only; no entry added, removed or moved (person_link unaffected).
usage: uv run python docs/eval/raw_fix_1908-09_tally_sentences_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, re, sys
from collections import Counter
from pathlib import Path

RAW = Path('outputs/full_run/raw')
NO_VE = {('balletartists_1908-09_SP_p005', '11.'), ('balletartists_1908-09_MSK_p002', '42.')}
SPURIOUS = {('balletartists_1908-09_MSK_p003', '73.', 'Тренинская'), ('balletartists_1908-09_SP_p003', '81.', 'Рыхлякова 2-я'),
            ('balletartists_1908-09_SP_p000', '1.', 'Александрова')}
GRIGORIEV = ('balletartists_1908-09_SP_p005', '17.', 'Григорьевъ')
FOKIN = ('balletartists_1908-09_SP_p008', '73.', 'Фокинъ')
# Всего / Все-то / Все-ю, dash, optional garbled preposition, N, category, dash, count, разъ/раза
T = re.compile(r'(?P<vse>Все(?:го|-го|-то|-ю))(?P<d1>\s*[—–-]+\s*)(?P<prep>(?:въ|всѣ|вв|88)\s+)?(?P<n>\d+)(?P<sp>\s+)'
               r'(?P<cat>[^\W\d_]+)(?P<d2>\s*[—–-]+\s*)(?P<cnt>\d+)(?P<raz>\s+раз[ъа])')
EXPECTED = Counter({'P': 145, 'H': 5, 'E': 45, 'N': 1, 'X': 3, 'F': 1})

done, log = Counter(), []
for f in sorted(RAW.glob('balletartists_1908-09_*.raw.json')):
    pid = f.name[:-len('.raw.json')]
    d = json.loads(f.read_text(encoding='utf-8')); changed = False
    for e in d['entries']:
        key = (pid, e.get('list_number'))
        if (pid, e.get('list_number'), e.get('family_name')) in SPURIOUS:
            assert e.get('credit_summary_text'), key
            log.append(f'X {pid} {key[1]} {e["family_name"]}: «{e["credit_summary_text"]}» -> null')
            e['credit_summary_text'] = None; e['credits'] = []; done['X'] += 1; changed = True
            continue
        t = e.get('credit_summary_text') or ''
        m = T.search(t)
        if not m:
            continue
        g = m.groupdict(); old = m.group(0)
        if g['vse'] in ('Все-то', 'Все-ю'):
            g['vse'] = 'Все-го'; done['H'] += 1
        if key in NO_VE:
            assert not g['prep'], key
        elif g['prep'] != 'въ ' and not (g['prep'] or '').startswith('въ'):
            g['prep'] = 'въ '; done['P'] += 1
        cat_old = g['cat']
        if g['n'] == '1' and g['cat'] in ('балетъ', 'балетахъ'):
            g['cat'] = 'балетѣ'; done['E'] += 1
        elif g['n'] == '1' and g['cat'] == 'оперъ':
            g['cat'] = 'оперѣ'; done['E'] += 1
        if (pid, key[1], e.get('family_name')) == GRIGORIEV:
            assert g['cnt'] == '27'; g['cnt'] = '21'; done['N'] += 1
        if (pid, key[1], e.get('family_name')) == FOKIN:
            assert g['cat'] == 'балетахъ'; g['cat'] = 'балетахь'; done['F'] += 1
        new = g['vse'] + g['d1'] + (g['prep'] or '') + g['n'] + g['sp'] + g['cat'] + g['d2'] + g['cnt'] + g['raz']
        if new == old:
            continue
        e['credit_summary_text'] = t[:m.start()] + new + t[m.end():]
        for c in e.get('credits') or []:
            if c.get('credit_type') != 'category_totals':
                continue
            if c.get('label') == cat_old and g['cat'] != cat_old and (pid, key[1], e.get('family_name')) != FOKIN:
                c['label'] = g['cat']
            if (pid, key[1], e.get('family_name')) == GRIGORIEV and c.get('count') == 27:
                c['count'] = 21
        log.append(f'{pid} {key[1]} {e.get("family_name")}: «{old}» -> «{new}»'); changed = True
    if changed and '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n'.join(log))
print(dict(done), 'expected', dict(EXPECTED))
assert done == EXPECTED, (done, EXPECTED)
print('WRITTEN' if '--write' in sys.argv else 'dry run')
