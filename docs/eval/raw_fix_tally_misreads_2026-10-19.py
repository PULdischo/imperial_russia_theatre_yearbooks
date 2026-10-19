"""Misreads in seven BalletArtists performance tallies (RG, 2026-10-19: "fix what the scans confirm"). Each line read by Claude
on the full-resolution PDF image, zoomed, after a read-only agent flagged them (the «перемоніймейстеръ» pass). Replacements are
applied to every string of the ONE entry (credit line, credits' label / role name). Field edit only.
Not changed: 1892-93 «Калькабрино» (print «Каль-|кабрино»; the agent's «бабрино» was its own misread); 1904-05 MSK Брыкинъ's
damaged «цер·мовій-».
usage: uv run python docs/eval/raw_fix_tally_misreads_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
FIXES = [
    # page, entry no. (1-based), surname, [(stored, printed)]
    ('balletartists_1892-93_SP_p005', 12, 'Булгаковъ',
     [('коммиссарь', 'коммиссаръ'), ('кунецъ', 'купецъ'), ('оруженосяцъ', 'оруженосецъ'), ('альгвази-ловъ', 'альгвазиловъ')]),
    ('balletartists_1898-99_MSK_p008', 14, 'Чудиновъ',
     [('тью-хранитель', 'тѣлохранитель'), ('Копеллія', 'Коппелія'), ('Корсарь', 'Корсаръ'), ('швейцарь', 'швейцаръ')]),
    ('balletartists_1899-00_SP_p009', 15, 'Солянниковъ 2-й',
     [('Шелякуничъ', 'Щелкунчикъ'), ('дакей', 'лакей'), ('Корсарь', 'Корсаръ'), ('Лебеди-ное', 'Лебединое')]),
    ('balletartists_1900-01_MSK_p006', 4, 'Брыкинъ 2-й',
     [('сарадинскій', 'сарацинскій'), ('куколь', 'куколъ')]),
    ('balletartists_1901-02_MSK_p005', 5, 'Брыкинъ 2-й',
     [('дивертисементахъ', 'дивертиссементахъ'), ('Корсарь', 'Корсаръ'), ('корсарь', 'корсаръ')]),
    ('balletartists_1903-04_SP_p008', 20, 'Прѣсняковъ 1-й',
     [('оруженоносецъ', 'оруженосецъ'), ('пыгать', 'цыганъ')]),
    ('balletartists_1904-05_SP_p009', 6, 'Прѣсняковъ 1-й',
     [('Копекъ-Горбунокъ', 'Конекъ-Горбунокъ')]),
]


def fix(obj, old, new):
    n = 0
    for k, v in list(obj.items() if isinstance(obj, dict) else enumerate(obj)):
        if isinstance(v, str) and old in v:
            n += v.count(old); obj[k] = v.replace(old, new)
        elif isinstance(v, (dict, list)):
            n += fix(v, old, new)
    return n


total = 0
for page, i, fam, pairs in FIXES:
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    e = d['entries'][i - 1]
    assert e['family_name'] == fam, (page, e['family_name'])
    for old, new in pairs:
        n = fix(e, old, new); assert n >= 1, (page, old)
        print(f'{page} no.{i} {fam}: «{old}» -> «{new}» x{n}'); total += n
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{total} replacements', '| WRITTEN' if '--write' in sys.argv else '| dry run')
