import duckdb,re,difflib,json
from collections import defaultdict,Counter
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
def norm(s):
    s=(s or '').lower().replace('ъ','').replace('ь','').replace('ѣ','е').replace('і','и').replace('ѳ','ф').replace('ё','е')
    s=re.sub(r'\d-?[йя]','',s); return re.sub(r'[^а-яa-z]','',s)
def sim(a,b): return difflib.SequenceMatcher(None,norm(a),norm(b)).ratio()
def match(ef,ep,pf,pp):
    if ef and pf and sim(ef,pf)<0.6: return False
    if ep and pp and sim(ep,pp)<0.6: return False
    return True
PAGES=['musicians_1891-92_MSK_p003','musicians_1894-95_MSK_p000','administration_1895-96_p001','administration_1894-95_p002']
GLOBAL={ # entry -> (person id prefix) chosen after reviewing candidates
 'musicians_1891-92_MSK_p003__e048':'093c796d','musicians_1894-95_MSK_p000__e028':'61b42a3b',
 'administration_1895-96_p001__e037':'1d378a89','administration_1894-95_p002__e018':'1bfb8436',
 'administration_1894-95_p002__e025':'72aaab0a','administration_1894-95_p002__e026':'3d658378'}
allp={str(r[0]):r for r in c.execute("select person_id,canonical_family_name,canonical_first_name from entities.person where superseded_by_person_id is null").fetchall()}
pref={k[:8]:k for k in allp}
nl={str(k):v for k,v in c.execute("select person_id,count(*) from entities.person_link group by 1").fetchall()}
final={}   # entry_id -> new person_id
cur_all={}
for page in PAGES:
    ents=c.execute("""select l.entry_id,e.family_name,e.first_name,e.patronymic,l.person_id,p.canonical_family_name,p.canonical_first_name,p.canonical_patronymic
       from entities.person_link l join raw.person_entry e using(entry_id) join entities.person p on p.person_id=l.person_id where e.page_id=? order by l.entry_id""",[page]).fetchall()
    pool={str(r[4]):(r[5],r[6],r[7]) for r in ents}
    onpage=Counter(str(r[4]) for r in ents)
    for r in ents:
        cur_all[r[0]]=str(r[4])
        eid=r[0]
        if eid in GLOBAL: final[eid]=pref[GLOBAL[eid]]; continue
        cands=[pid for pid,(pf,pn,pp) in pool.items() if sim(r[1],pf)>=0.8 and match(r[2],r[3],pn,pp)]
        cands.sort(key=lambda x:(-(nl.get(x,0)-onpage[x]),x!=str(r[4])))
        assert cands,(eid,'no candidate')
        final[eid]=cands[0]
changes={e:(cur_all[e],n) for e,n in final.items() if cur_all[e]!=n}
# sanity: no person linked twice on a page unless the entry names are equal-ish
bypage=defaultdict(list)
for e,n in final.items(): bypage[e.rsplit('__',1)[0]].append((n,e))
for pg,lst in bypage.items():
    cnt=Counter(n for n,_ in lst)
    for n,k in cnt.items():
        if k>1: print('!! person',n[:8],'linked',k,'times on',pg,[e.rsplit('__',1)[1] for nn,e in lst if nn==n])
print('entries total',len(final),'| relinks',len(changes))
json.dump(changes,open('/tmp/audit2/relink_changes.json','w'))
# persons that lose ALL their links by this change
before=Counter(); 
allq=c.execute("select entry_id,person_id from entities.person_link").fetchall()
cur_link={e:str(p) for e,p in allq}
after=dict(cur_link); after.update({e:n for e,(o,n) in changes.items()})
b=Counter(cur_link.values()); a=Counter(after.values())
lost=[p for p in b if a.get(p,0)==0]
print('persons losing all links:',[(p[:8],allp.get(p,('?','?','?'))[1:3]) for p in lost])
wd=[p for p in lost if c.execute("select count(*) from entities.person_wikidata_link where person_id=?",[p]).fetchone()[0]]
ml=[p for p in lost if c.execute("select count(*) from entities.person_merge_log where person_id_1=? or person_id_2=?",[p,p]).fetchone()[0]]
print('of those with wikidata link:',len(wd),'| in merge log:',len(ml))
# independent check: tenure-start consistency of every affected person before vs after
def starts(pid_map):
    d=defaultdict(set)
    rows=c.execute("select e.entry_id,s.start_date_text from raw.person_entry e join raw.person_entry_service s using(entry_id) where s.period_order=1").fetchall()
    for eid,st in rows:
        p=pid_map.get(eid)
        if p and st:
            m=re.search(r'(\d{1,2}\s+\S+\s+\d{4})',st)
            d[p].add(m.group(1) if m else st)
    return d
affected_b={cur_all[e] for e in changes}|{n for e,(o,n) in changes.items()}
sb,sa=starts(cur_link),starts(after)
inc=lambda s:sum(1 for p in affected_b if len(s.get(p,()))>1)
print('affected persons',len(affected_b),'| with >1 distinct first-period start date: before',inc(sb),'-> after',inc(sa))
bad_after=[(p[:8],allp.get(p,('?','?','?'))[1],sa[p]) for p in affected_b if len(sa.get(p,()))>1]
for x in bad_after[:12]: print('   still inconsistent:',x)
