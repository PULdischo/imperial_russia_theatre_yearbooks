"""Safeguard for the general rules: is a review mention inside a quoted OLD cast? Looks back up to 3 blocks (same review, across page
breaks) for old-cast wording («При первомъ … представленіи», «первыми исполнителями», «въ первый разъ поставленъ», «первоначально» …)
with no current-performance wording after it (a dated performance «16-го апрѣля», «въ сотое представленіе», «въ обозрѣваемомъ сезонѣ»,
«при (его) возобновленіи», «нынѣ» …). Writes oldcast_mentions.csv for the G1/G2 candidates it catches."""
import duckdb, csv, re
G = 'docs/eval/review_names_general_rules_2026-11-07'
c = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
OLD = (r"(при\s+перв(омъ|ой|ыхъ)\s+(и\s+послѣдующихъ\s+)?(представлені|постановк)|первыми\s+исполнител|въ\s+первый\s+разъ\s+"
       r"(былъ\s+|была\s+|было\s+)?(поставлен|данъ|дана|исполнен)|первоначально|при\s+первоначальн|тогда\s+слѣдующ|въ\s+былое\s+время|"
       r"тогдашн\w*|первыхъ\s+исполнител|первыми\s+сюжетами|впервые[^.]{0,80}18[0-8]\d|въ\s+18[0-8]\d\s*(г\.|году|года))")
NOW = (r"((^|[.¶]\s*)\d+-?го\s+(января|февраля|марта|апрѣля|мая|іюня|іюля|августа|сентября|октября|ноября|декабря)|сотое\s+представлені|"
       r"обозрѣваем|при\s+(его\s+|ея\s+|настоящ\w+\s+|послѣдн\w+\s+|нынѣшн\w+\s+)?(его\s+)?(возобновлені|постановк)|предыдущ\w+\s+сезон|сезона\s+19|въ\s+этомъ\s+сезон|нынѣшн|нынѣ\b|теперь)")
blocks = c.sql("select block_id, page_id, block_index, coalesce(text, caption_text, '') from raw.review_block order by page_id, block_index").fetchall()
prevs, buf, cur = {}, [], None
for bid, pid, bi, t in blocks:
    review = pid.rsplit('_p', 1)[0]
    if review != cur: buf, cur = [], review
    prevs[bid] = ' ¶ '.join(buf[-3:])
    if t.strip(): buf.append(t)
def is_oldcast(bid, a, t):
    ctx = prevs.get(bid, '')[-1500:] + ' ¶ ' + t[:a + 20]
    m = list(re.finditer(OLD, ctx, re.I))
    return bool(m) and not re.search(NOW, ctx[m[-1].end():], re.I), (m[-1].group(0).replace('\n', ' ') if m else '')
if __name__ == '__main__':
    out = []
    for g in ['g1', 'g2']:
        rows = [r for r in csv.DictReader(open(f'{G}/{g}.csv')) if g == 'g2' or not r['flag']]
        info = {str(m): (b, a, t) for m, b, a, t in c.sql(f"""select m.mention_id, m.block_id, m.char_start, coalesce(b.text, b.caption_text, '')
            from research.review_mention m join raw.review_block b on b.block_id = m.block_id
            where m.mention_id in ({','.join(r['mention_id'] for r in rows)})""").fetchall()}
        n = 0
        for r in rows:
            ok, w = is_oldcast(*info[r['mention_id']])
            if ok: n += 1; out.append(dict(rule=g, mention_id=r['mention_id'], season=r['season'], block_id=info[r['mention_id']][0], wording=w))
        print(g, len(rows), '| inside a quoted old cast:', n)
    csv.DictWriter(open(f'{G}/oldcast_mentions.csv', 'w', encoding='utf-8'), fieldnames=['rule', 'mention_id', 'season', 'block_id', 'wording']).writeheader()
    w = csv.DictWriter(open(f'{G}/oldcast_mentions.csv', 'a', encoding='utf-8'), fieldnames=['rule', 'mention_id', 'season', 'block_id', 'wording']); w.writerows(out)
    print('17224 caught:', any(o['mention_id'] == '17224' for o in out), '| blocks:', len({o['block_id'] for o in out}))
