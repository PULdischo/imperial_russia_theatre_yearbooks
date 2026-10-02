import duckdb,json,csv,sys
csv.field_size_limit(10**9)
B='outputs/full_run_pre_promote_backup_2026-10-02_nameaudit/'
old=duckdb.connect(B+'imperial_theaters.duckdb',read_only=True)
new=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
q=lambda c,s:c.execute(s).fetchall()
print('receipts same:',q(old,'select sum(receipts_total_kopecks) from research.event')==q(new,'select sum(receipts_total_kopecks) from research.event'))
print('entries old/new:',q(old,'select count(*) from raw.person_entry')[0][0],q(new,'select count(*) from raw.person_entry')[0][0])
to={str(r[0]):str(r[1]) for r in q(old,'select person_id,superseded_by_person_id from entities.person where superseded_by_person_id is not null')}
tn={str(r[0]):str(r[1]) for r in q(new,'select person_id,superseded_by_person_id from entities.person where superseded_by_person_id is not null')}
print('tombstones old/new:',len(to),len(tn),'| old all kept:',all(tn.get(k)==v for k,v in to.items()))
for k,v in tn.items():
    if k not in to: print('  NEW tombstone',q(new,f"select display_name,first_attested_season,last_attested_season from entities.person where person_id='{k}'"),'->',q(new,f"select display_name,first_attested_season,last_attested_season from entities.person where person_id='{v}'"))
print('live old/new',q(old,'select count(*) from entities.person where superseded_by_person_id is null')[0][0],q(new,'select count(*) from entities.person where superseded_by_person_id is null')[0][0])
print('orphans:',q(new,'select count(*) from entities.person_link pl left join entities.person p on pl.person_id=p.person_id where p.person_id is null')[0][0])
ol={k:str(v) for k,v in q(old,'select entry_id,person_id from entities.person_link')}; nl={k:str(v) for k,v in q(new,'select entry_id,person_id from entities.person_link')}
changed={k for k in nl if ol.get(k)!=nl[k]}
print('links changed:',len(changed),sorted(changed)[:8])
# parsed diff
def load(p):
    return {r['entry_id']:r for r in csv.DictReader(open(p,encoding='utf-8'))}
a=load(B+'parsed/person_entry.csv'); b=load('outputs/full_run/parsed/person_entry.csv')
ch=0;cols={}
import collections
cc=collections.Counter()
for k in b:
    if k in a:
        for c in b[k]:
            if a[k][c]!=b[k][c]: cc[c]+=1
print('parsed column diffs:',dict(cc),'| entries only in one:',len(set(a)^set(b)))
print('flags',sum(1 for _ in open('outputs/full_run/quality_flags.csv'))-1)
