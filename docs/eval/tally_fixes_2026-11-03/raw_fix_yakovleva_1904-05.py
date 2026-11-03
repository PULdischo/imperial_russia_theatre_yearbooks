"""Яковлева 1-я, 1904-05 SP p.21 no. 130 (balletartists_1904-05_SP_p005, entry 19): seven misreads in the tally line, read on the scan
by Claude 2026-11-03, approved by RG ("Yes, correct all 7"; docs/research_layer_review_2026-11-03.md). Counts all match the print.
Changes the tally text and the matching items; every old value is asserted, and a second run is a no-op that says so.

usage: uv run python docs/eval/tally_fixes_2026-11-03/raw_fix_yakovleva_1904-05.py --raw-dir <dir> [--write]"""
import argparse, json
from pathlib import Path

PAGE, IDX, FAMILY = 'balletartists_1904-05_SP_p005', 19, 'Яковлева 1-я'
TEXT = [('Копсъ-Горбунокъ', 'Конекъ-Горбунокъ'), ('Нахита', 'Пахита'), ('Корсарь (перпитянка', 'Корсаръ (негритянка'),
        ('Фея куколь', 'Фея куколъ'), ('Граніелла', 'Граціелла'), ('Голубая георгиня', 'Голубая георгина')]
ITEMS = [  # (old label, old part) -> (new label, new part)
    (('Копсъ-Горбунокъ', 'деревенская баба'), ('Конекъ-Горбунокъ', 'деревенская баба')),
    (('Нахита', 'графиня'), ('Пахита', 'графиня')),
    (('Корсарь', 'перпитянка'), ('Корсаръ', 'негритянка')),
    (('Фея куколь', 'жена купца'), ('Фея куколъ', 'жена купца')),
    (('Граніелла', 'Маріанна'), ('Граціелла', 'Маріанна')),
    (('Голубая георгиня', 'Сусанна'), ('Голубая георгина', 'Сусанна')),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True, type=Path)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    f = a.raw_dir / f'{PAGE}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    e = d['entries'][IDX - 1]
    assert e['family_name'] == FAMILY, e['family_name']
    t = e['credit_summary_text']
    if all(new in t for _, new in TEXT) and not any(old in t for old, _ in TEXT):
        print('already applied; nothing to do'); return
    for old, new in TEXT:
        assert t.count(old) == 1, (old, t)
        t = t.replace(old, new)
    e['credit_summary_text'] = t
    for (ol, orole), (nl, nrole) in ITEMS:
        hits = [c for c in e['credits'] if c.get('label') == ol and c.get('role_name') == orole]
        assert len(hits) == 1, (ol, orole, hits)
        hits[0]['label'], hits[0]['role_name'] = nl, nrole
    print('text:', t)
    for c in e['credits']:
        print('  ', c)
    if a.write:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WRITTEN' if a.write else 'dry run')


if __name__ == '__main__':
    main()
