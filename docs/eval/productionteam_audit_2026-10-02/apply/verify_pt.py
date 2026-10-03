import duckdb,csv,collections,sys
csv.field_size_limit(10**9)
B='outputs/full_run_pre_promote_backup_2026-10-02_pt_stage1/'
old=duckdb.connect(B+'imperial_theaters.duckdb',read_only=True); new=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
q=lambda c,s:c.execute(s).fetchall()
print('receipts same:',q(old,'select sum(receipts_total_kopecks) from research.event')==q(new,'select sum(receipts_total_kopecks) from research.event'))
print('entries old/new:',q(old,'select count(*) from raw.person_entry')[0][0],q(new,'select count(*) from raw.person_entry')[0][0])
to={str(r[0]):str(r[1]) for r in q(old,'select person_id,superseded_by_person_id from entities.person where superseded_by_person_id is not null')}
tn={str(r[0]):str(r[1]) for r in q(new,'select person_id,superseded_by_person_id from entities.person where superseded_by_person_id is not null')}
print('tombstones old/new:',len(to),len(tn),'| old all kept:',all(tn.get(k)==v for k,v in to.items()))
print('live old/new',q(old,'select count(*) from entities.person where superseded_by_person_id is null')[0][0],q(new,'select count(*) from entities.person where superseded_by_person_id is null')[0][0])
print('orphan links:',q(new,'select count(*) from entities.person_link pl left join entities.person p on pl.person_id=p.person_id where p.person_id is null')[0][0])
print('links to tombstoned persons:',q(new,'select count(*) from entities.person_link l join entities.person p using(person_id) where p.superseded_by_person_id is not null')[0][0])
print('entries without link:',q(new,'select count(*) from raw.person_entry e left join entities.person_link l using(entry_id) where l.entry_id is null')[0][0])
i=0
for k,v in tn.items():
    if k not in to:
        i+=1; a=q(new,f"select display_name,first_attested_season,last_attested_season from entities.person where person_id='{k}'")[0]; b=q(new,f"select display_name,first_attested_season,last_attested_season from entities.person where person_id='{v}'")[0]
        print(' NEW tombstone',i,a,'=>',b)
print('flags',sum(1 for _ in open('outputs/full_run/quality_flags.csv'))-1)
