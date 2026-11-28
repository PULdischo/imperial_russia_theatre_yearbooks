"""Historical-cast audit (RG 2026-11-27: make sure historical casts don't get mixed into the contemporary ones).
Flags review blocks NOT in docs/eval/review_historical_passages.csv that hold linked person mentions (or performer
links) and show signs of an earlier time, looking back across blocks of the same review (the 2026-11-03 sweep only
looked inside the block, so a cast whose year sits in the paragraph before was missed: 1895-96 SP «Конекъ», 1864).
Signals (any): S1 old-cast wording with no current-performance wording after it (oldcast_check.py, lookback 3 blocks);
S2 a year before the season (18NN or 18NN г.) in this block or the 2 blocks before it, same review; S3 a quoted
journal or chronicler («(18NN, №», «хроникеръ», «писалъ», «отзывъ о первомъ представленіи»); S4 the block directly
follows a listed historical block. Reads a COPY of production (path argument). Writes candidates.csv."""
import csv, re, sys, collections, duckdb
db = sys.argv[1]; OUT = 'docs/eval/historical_cast_audit_2026-11-27/candidates.csv'
c = duckdb.connect(db, read_only=True)
sys.path.insert(0, 'docs/eval/review_names_general_rules_rerun_2026-11-27')
import oldcast_check as oc  # uses its own read-only connection to production for block order only -- re-done below instead
OLD, NOW = oc.OLD, oc.NOW
hist = {r['block_id']: r['scope'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv', encoding='utf-8'))}
blocks = c.sql("select block_id, page_id, block_index, block_type, coalesce(text, caption_text, '') from raw.review_block order by page_id, block_index").fetchall()
links = collections.defaultdict(list)
for b, s, pid, name in c.sql("""select m.block_id, m.surface, m.person_id::varchar, p.display_name from research.review_mention m
        join research.person p using(person_id) where m.mention_type='person'""").fetchall():
    links[b].append(f'{s}→{name}')
review_of = lambda pid: pid.rsplit('_p', 1)[0]
byrev = collections.defaultdict(list)
for row in blocks: byrev[review_of(row[1])].append(row)
CITE = r"(\(18[0-9]\d\s*,?\s*№|хроникер|хроникёр|писалъ|писала|отзывъ\s+о\s+первомъ|первое\s+представлені|Русская\s+Сцена|Русской\s+Сцен|Сѣверная\s+пчела|Театральн\w+\s+и\s+музыкальн)"
out = []
for rev, rows in byrev.items():
    season = re.search(r'(\d{4})-\d\d', rev); start = int(season.group(1)) if season else 1900
    texts = [r[4] for r in rows]
    for i, (bid, pid, bi, bt, t) in enumerate(rows):
        if bid in hist or not links.get(bid): continue
        if bt == 'figure': continue          # plate captions show the current production
        prev3 = ' ¶ '.join(x for x in texts[max(0, i - 3):i] if x.strip())
        sig = []
        ctx = prev3[-1500:] + ' ¶ ' + t
        m = list(re.finditer(OLD, ctx, re.I))
        if m and not re.search(NOW, ctx[m[-1].end():], re.I): sig.append('S1 ' + m[-1].group(0).replace('\n', ' '))
        yrs = [int(y) for y in re.findall(r'\b(18\d\d)\b', ' '.join(texts[max(0, i - 2):i + 1])) if int(y) < start - 1]
        if yrs: sig.append('S2 ' + ','.join(map(str, sorted(set(yrs)))))
        cm = re.search(CITE, ' '.join(texts[max(0, i - 2):i + 1]), re.I)
        if cm: sig.append('S3 ' + cm.group(0).replace('\n', ' '))
        if i and rows[i - 1][0] in hist: sig.append('S4 follows ' + rows[i - 1][0][-10:])
        if not sig: continue
        out.append(dict(block_id=bid, season=rev.split('_')[1], review=rev, signals=' | '.join(sig), n_linked=len(links[bid]),
                        linked='; '.join(links[bid])[:400], text=t.replace('\n', ' ')[:300]))
w = csv.DictWriter(open(OUT, 'w', encoding='utf-8', newline=''), fieldnames=list(out[0]), lineterminator='\n'); w.writeheader(); w.writerows(out)
print('candidate blocks:', len(out), '| linked mentions in them:', sum(o['n_linked'] for o in out))
cnt = collections.Counter(tuple(sorted({s[:2] for s in o['signals'].split(' | ')})) for o in out)
for k, v in cnt.most_common(): print('  ', '+'.join(k), v)
