"""Flag unusual spellings of RECURRING names for a scan check.

RG's idea, 2026-09-26: "anytime we get a version that is a little unusual,
we could check it against the scan. Frequently occurring names like Легатъ
or Преображенская will have one spelling that occurs more than others."

Why this reaches something nothing else does: these are spellings every
extraction pass AGREED on, so the run-disagreement signal is blind to them
by construction. `Пѣтипа` appears once against 169 `Петипа`; no pass ever
dissented.

**It is a worklist, never an auto-fix**, for two reasons, both measured:

  * `Тихомировъ` x28 vs `Тихоміровъ` x4 -- and the print really does carry
    BOTH. Minority does not mean wrong. See
    [[pre-reform-orthography-is-unstable]].
  * `Легать` x34 vs `Легатъ` x32 -- RG ruled `Легатъ`, so here the MAJORITY
    spelling is the erroneous one. The model's systematic ъ->ь slip is
    frequent enough to outvote the truth. Frequency is informative at high
    ratios and actively misleading near 1:1, which is why --min-ratio
    defaults to 5 and the ratio is always printed.

Usage:
    uv run python pipeline/name_variants.py --raw-dir outputs/reviews/pilot_1 \
        --out outputs/reviews/name_variants.csv [--min-ratio 5] [--min-total 5]
"""
from __future__ import annotations
import argparse, csv, collections, glob, io, os, re

TOKEN = re.compile(r'[А-ЯЁѢІѲѴ][а-яёѣіѳѵъь-]{3,}')
SPAN = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
TAG = re.compile(r'</?[a-z][^>]*>')
# Fold ONLY the axes that are genuinely unstable in this orthography.
FOLD = (('ъ', ''), ('ь', ''), ('і', 'и'), ('ѣ', 'е'),
        ('ѳ', 'ф'), ('ѵ', 'и'), ('ё', 'е'))


def page_text(path: str) -> str:
    s = io.open(path, encoding='utf-8').read()
    return TAG.sub('', " ".join(SPAN.findall(s)).replace('\\n', ' '))


def fold(w: str) -> str:
    w = w.lower()
    for a, b in FOLD:
        w = w.replace(a, b)
    return w


def find_variants(raw_dir: str, min_total: int, min_ratio: float):
    counts = collections.Counter()
    where = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(raw_dir, '*.raw.json'))):
        pid = os.path.basename(f).replace('.raw.json', '')
        for m in TOKEN.finditer(page_text(f)):
            counts[m.group()] += 1
            where[m.group()].add(pid)

    groups = collections.defaultdict(collections.Counter)
    for w, n in counts.items():
        groups[fold(w)][w] += n

    rows = []
    for _, var in groups.items():
        if len(var) < 2 or sum(var.values()) < min_total:
            continue
        top, topn = var.most_common(1)[0]
        for w, n in var.items():
            if w == top:
                continue
            ratio = topn / n
            if ratio < min_ratio:
                continue
            rows.append({'variant': w, 'variant_count': n,
                         'dominant': top, 'dominant_count': topn,
                         'ratio': round(ratio, 1),
                         'pages': ";".join(sorted(where[w]))})
    rows.sort(key=lambda r: (-r['dominant_count'], -r['ratio']))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-ratio', type=float, default=5.0,
                    help='below ~2 the signal inverts; see module docstring')
    ap.add_argument('--min-total', type=int, default=5)
    a = ap.parse_args()
    rows = find_variants(a.raw_dir, a.min_total, a.min_ratio)
    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ['variant', 'variant_count', 'dominant',
                            'dominant_count', 'ratio', 'pages'])
        w.writeheader(); w.writerows(rows)
    print(f'{len(rows)} spellings, {sum(r["variant_count"] for r in rows)} '
          f'instances to check -> {a.out}')
    for r in rows[:20]:
        print(f'  {r["variant"]:20s} x{r["variant_count"]:<3d} vs '
              f'{r["dominant"]:20s} x{r["dominant_count"]:<4d} ({r["ratio"]}x)')


if __name__ == '__main__':
    main()
