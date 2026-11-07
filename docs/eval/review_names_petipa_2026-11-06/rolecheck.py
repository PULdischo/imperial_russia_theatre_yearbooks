import csv, re, duckdb, sys
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
# spiski roles per (season, first_name) for every Petipa entry
sp={}
for pid, fam, first, work, role in c.sql("""select pe.page_id, pe.family_name, pe.first_name, cr.label, cr.role_name
   from raw.person_entry pe join raw.person_entry_credit cr using(entry_id)
   where pe.family_name like 'Петипа%' and cr.credit_type='named_work'""").fetchall():
    season=re.search(r"_(\d{4}-\d{2})_", pid).group(1)
    sp.setdefault((season, first), []).append((work or '', role or ''))
def words(s):
    s=s.lower().replace('ѣ','е').replace('і','и').replace('ѳ','ф').replace('„','').replace('“','')
    return [re.sub(r"(ией|ою|ею|ами|ями|ой|ей|ыя|ия|ая|ии|ию|ы|и|а|я|у|ю|ъ|ь|е|о)$","",w) for w in re.findall(r"[a-zа-яё]{3,}", s)]
def same(r1, r2):
    a,b=words(r1),words(r2)
    return bool(a) and bool(b) and a[0]==b[0] and (len(a)<2 or len(b)<2 or a[1]==b[1])
rows=list(csv.DictReader(open(sys.argv[1],encoding='utf-8')))
out=[]
for x in rows:
    if x['label'][0] in 'H': continue
    b,a=x['before'],x['after']
    rb=re.search(r"([А-ЯЁA-Za-zа-яёѣі][^—;:()\d]{1,40}?)\s*[—–-]\s*(г-ж\w*\s*|Г-ж\w*\s*)?([А-ЯЁ]\.\s*)*$", b)
    ra=re.match(r"\s*\d?\s*(-я)?\s*\(([^)]{2,40})\)", a)
    role=(ra.group(2) if ra else (rb.group(1).strip() if rb else '')).strip(' ,.')
    if not role: continue
    hits=[]
    for (season, first), lst in sp.items():
        if season!=x['season']: continue
        for w,r in lst:
            if r and same(r, role): hits.append(f"{first}: {w} — {r}")
    out.append((x['label'][:30], x['proposed'], x['mention_id'], x['season'], role, '; '.join(sorted(set(hits))) or '-'))
w=csv.writer(open(sys.argv[2],'w',encoding='utf-8')); w.writerow(['label','proposed','mention_id','season','review_role','spiski_hits']); w.writerows(out)
from collections import Counter
agree=dis=none=0
for l,p,m,s,role,h in out:
    firsts={hh.split(':')[0] for hh in h.split('; ')} if h!='-' else set()
    want={'Марія М.':'Марія','Надежда М.':'Надежда','Любовь М.':'Любовь','Вѣра М.':'Вѣра'}.get(p)
    if h=='-': none+=1
    elif want and firsts=={want}: agree+=1
    elif want: dis+=1; print('DISAGREE', l, m, s, role, '|', h)
    else: print('HELPS?', l, m, s, role, '|', h)
print('roles found', len(out), '| agree', agree, '| disagree', dis, '| no spiski hit', none)
