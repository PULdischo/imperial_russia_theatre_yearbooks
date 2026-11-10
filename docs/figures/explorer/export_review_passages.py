"""Export, for every ballet in the Ballet Explorer, the Season Review passages that speak about it, by season and city.

A passage is "direct" when the database links it to the ballet or one of its excerpts: a work mention (entities.review_mention), a cast
statement (research.review_assertion), a creator or craft credit (research.review_credit) or a dance number (research.review_dance).
Text is research.review_passage (the corrected transcription), reflowed for reading.
English is the machine translation in outputs/reviews/translations.csv (made 2026-10-06 for reading; may predate later text corrections).

usage: uv run python docs/figures/explorer/export_review_passages.py  ->  docs/figures/explorer/reviews.json"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'outputs/full_run/imperial_theaters.duckdb'
con = duckdb.connect(str(DB), read_only=True)
q = lambda s, *a: con.execute(s, a).fetchall()


def reflow(t):
    t = re.sub(r'([^\s-])-\n\s*(?=[А-ЯЁѲІѢA-Z])', r'\1-', t or '')   # a real hyphen before a capital («Донъ-\nКихотъ»)
    t = re.sub(r'([^\s-])-\n\s*', r'\1', t)                          # a word broken at the line end
    return re.sub(r'\s*\n\s*', ' ', t).strip()


# the ballets on the page and their excerpt works
ballets = q("""SELECT w.work_id::VARCHAR FROM research.work w WHERE w.art_form = 'ballet' AND w.excerpt_of_work_id IS NULL""")
canon = dict(q("SELECT work_id::VARCHAR, canonical_title FROM research.work"))
parent = {wid: wid for wid, in ballets}
for x, p in q("SELECT work_id::VARCHAR, excerpt_of_work_id::VARCHAR FROM research.work WHERE excerpt_of_work_id IS NOT NULL"):
    if p in parent:
        parent[x] = p

direct = defaultdict(set)           # ballet -> block ids
surfaces = defaultdict(set)         # ballet -> printed forms to highlight
for b, wid, surf in q("""SELECT block_id, entity_id::VARCHAR, surface FROM entities.review_mention
                         WHERE mention_type = 'work' AND entity_id IS NOT NULL"""):
    if wid in parent:
        direct[parent[wid]].add(b); surfaces[parent[wid]].add(reflow(surf))
for tbl in ('review_assertion', 'review_credit', 'review_dance'):
    for b, wid in q(f"SELECT block_id, work_id::VARCHAR FROM research.{tbl} WHERE work_id IS NOT NULL"):
        if wid in parent:
            direct[parent[wid]].add(b)

# all passages in reading order, grouped by review section (one city's ballet / opera / general review of a season)
rows = q("""SELECT b.block_id, b.page_id, b.block_index, b.block_type, b.text, b.caption_text, p.season, p.city, p.genre, p.printed_folio
            FROM research.review_passage b JOIN research.review_page p USING (page_id) ORDER BY b.page_id, b.block_index""")
info, order, pos = {}, defaultdict(list), {}
for bid, pid, idx, typ, text, cap, season, city, genre, folio in rows:
    sect = re.sub(r'_p\d+$', '', pid)
    info[bid] = dict(season=season, city=city, genre=genre, folio=folio, type=typ,
                     ru=reflow(cap if typ == 'figure' and cap else text))
    pos[bid] = (sect, len(order[sect])); order[sect].append(bid)

csv.field_size_limit(10 ** 9)
tr_path = ROOT / 'outputs/reviews/translations.csv'
english = {r['block_id']: r['english'] for r in csv.DictReader(open(tr_path, encoding='utf-8'))} if tr_path.exists() else {}

def title_like(surf, wid):
    """keep only printed forms of the title itself (not scene names or credit phrases linked to the work)"""
    t = canon.get(wid, '').lower().replace('ъ', '')
    s0 = surf.lower().replace('ъ', '').replace('ѣ', 'е')
    stem = t.replace('ѣ', 'е')[:5]
    return len(surf) <= 45 and '—' not in surf and stem and stem in s0


passages, out = {}, {}
for wid, blocks in direct.items():
    keep = {}
    for b in blocks:
        if b not in pos:
            continue
        sect, i = pos[b]
        keep[b] = True          # linked passages only (RG 2026-11-10: the neighbouring "context" passages were dropped)
    by = defaultdict(list)
    for b, is_direct in keep.items():
        d = info[b]
        if not d['ru']:
            continue
        passages.setdefault(b, dict(folio=d['folio'], genre=d['genre'], ru=d['ru'], en=english.get(b, '')))
        by[f"{d['season']}|{d['city']}"].append((pos[b], [b, 1 if is_direct else 0]))
    hl = {x for x in surfaces[wid] if title_like(x, wid)} | {canon.get(wid, '')}
    out[wid] = dict(hl=sorted(hl - {''}, key=len, reverse=True),
                    seasons={k: [p for _, p in sorted(v, key=lambda t: t[0])] for k, v in by.items()})

path = Path(__file__).with_name('reviews.json')
path.write_text(json.dumps(dict(ballets=out, passages=passages), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
n = len(passages)
print(len(out), 'ballets with review passages;', n, 'distinct passages;', len(english), 'translations;',
      path.stat().st_size // 1024, 'KB')
