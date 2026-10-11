"""Stored-data detector for the two signatures that marked the date-shift cascades found by the false-split sizing
(issue #151 follow-up 13). Reads outputs/full_run/raw/repertoire_*.raw.json; writes shift_candidates.csv next to itself.

    uv run python docs/eval/title_check_2026-10-10/detect_shift_candidates.py

  DUP    two consecutive sessions of the SAME theater on a page with the same receipts figure (to the kopeck, not «— к.»)
         and the same list of works: one of them is a duplicate of the other's cell (1899-00 p012 Михайловскій 14/15 Nov).
  BANNER a session stored as morning/evening that has no works and only an annotation (1899-00 p018 Александринскій 18 Dec:
         a banner-only cell given two slots, which pushed the column after it one slot off).
Both are candidates for a scan check, not findings. Seasons whose receipts are not printed (1890-91, 1891-92) cannot
trip DUP at all (1891-92 pair012 18 Среда was found by the sample, not by this).
"""
import csv, glob, json, os, re, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(os.path.dirname(__file__), 'shift_candidates.csv')


def theater(s):
    t = (s.get('theater') or '').lower()
    for k, v in (('мар', 'MAR'), ('александр', 'ALX'), ('михайл', 'MIH'), ('больш', 'BOL'), ('мал', 'MAL'), ('нов', 'NOV')):
        if k in t:
            return v
    return t[:6]


rows = []
for p in sorted(glob.glob(os.path.join(ROOT, 'outputs/full_run/raw/repertoire_*.raw.json'))):
    pid = os.path.basename(p).replace('.raw.json', '')
    S = json.load(open(p, encoding='utf-8')).get('sessions') or []
    by = collections.defaultdict(list)
    for i, s in enumerate(S, 1):
        by[theater(s)].append((i, s))
    for t, L in by.items():
        for (i, a), (j, b) in zip(L, L[1:]):
            ra = (a.get('receipts_text') or '').strip(); rb = (b.get('receipts_text') or '').strip()
            wa = [(w.get('work_title') or '').lower() for w in a.get('works') or []]
            wb = [(w.get('work_title') or '').lower() for w in b.get('works') or []]
            if ra and ra == rb and wa and wa == wb and not re.search(r'—\s*к', ra):
                rows.append(('DUP', pid, t, f's{i:03d}/s{j:03d}', f"{a.get('date_text')} | {b.get('date_text')}", ra))
    for i, s in enumerate(S, 1):
        if s.get('session') in ('morning', 'evening') and not (s.get('works') or []) and (s.get('annotation') or '').strip():
            rows.append(('BANNER', pid, theater(s), f's{i:03d}', f"{s.get('date_text')} {s.get('session')}", (s.get('annotation') or '')[:60]))
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['kind', 'page_id', 'theater', 'sessions', 'dates', 'detail']); w.writerows(rows)
print(len(rows), 'candidates ->', OUT)
