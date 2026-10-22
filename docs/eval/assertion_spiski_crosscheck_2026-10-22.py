# Cross-check of research.review_assertion against the BalletArtists spiski role credits (2026-10-22, RG asked).
# Usage: uv run python -I docs/eval/assertion_spiski_crosscheck_2026-10-22.py <out.csv>   (run from the repo root)
# Role match = every 4-letter word stem of one side is in the other (folds ѣ/і/ѳ/ъ/ь/й), so declined forms match.
import duckdb, re, collections, csv, sys
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
def norm(s):
    s=(s or '').lower().replace('ѣ','е').replace('і','и').replace('ѳ','ф').replace('ё','е').replace('ъ','').replace('ь','').replace('й','и')
    return [w[:4] for w in re.findall(r'[а-яa-z]+',s) if len(w)>1]
def rmatch(a,b):
    a,b=norm(a),norm(b)
    if not a or not b: return False
    sa,sb=set(a),set(b)
    return sa<=sb or sb<=sa
cred=collections.defaultdict(list)  # person -> [(season,city,work,role)]
for pid,season,city,work,role in c.execute("""
  select pl.person_id, s.season, s.city, pc.label, pc.role_name from raw.person_entry_credit pc
  join raw.person_entry pe using(entry_id) join raw.source_pages s on s.page_id=pe.page_id
  join entities.person_link pl on pl.entry_id=pe.entry_id
  where pc.credit_type='named_work' and pc.role_name is not null""").fetchall():
    cred[str(pid)].append((season,city,work,role))
cred_seasons={r[0] for v in cred.values() for r in v}
rows=c.execute("""select assertion_id, season, city, role_surface, performer_surface, performer_person_id, link_method, work_surface, w.canonical_title
  from research.review_assertion a left join research.work w using(work_id)""").fetchall()
B=collections.Counter(); ex=collections.defaultdict(list); bym=collections.defaultdict(collections.Counter)
for aid,season,city,role,psurf,pid,lm,wsurf,wtitle in rows:
    if pid is None: b='0 no performer linked'
    else:
        cs=cred.get(str(pid),[])
        same=[x for x in cs if x[0]==season]
        if any(rmatch(role,x[3]) for x in same): b='A role in spiski, same season'
        elif any(rmatch(role,x[3]) for x in cs): b='B role in spiski, other season'
        elif same: b='C person has spiski roles that season, not this one'
        elif season not in cred_seasons: b='E season has no role credits in spiski'
        elif cs: b='D person has spiski roles, none this season'
        else: b='F person has no spiski role credits at all'
    B[b]+=1; bym[lm][b]+=1; ex[b].append((season,city,role,psurf,wtitle or wsurf, lm))
for k in sorted(B): print(B[k],k)
print()
for lm in bym: print(lm, sorted(bym[lm].items()))
print('role-credit seasons:', sorted(cred_seasons))
import random; random.seed(1)
for k in ['C person has spiski roles that season, not this one','D person has no spiski roles, none this season','F person has no spiski role credits at all','B role in spiski, other season']:
    print('==',k); [print('  ',e) for e in random.sample(ex[k],min(8,len(ex[k])))]
with open(sys.argv[1],'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['bucket','season','city','role','performer','work','link_method'])
    for k in sorted(ex):
        for e in ex[k]: w.writerow([k,*e])
