import duckdb,json,shutil,os,uuid
B='outputs/full_run_pre_promote_backup_2026-10-02_relink131/'
os.makedirs(B,exist_ok=True)
shutil.copy2('outputs/full_run/imperial_theaters.duckdb',B+'imperial_theaters.duckdb')
print('backup done')
ch=json.load(open('/tmp/audit2/relink_changes.json'))
con=duckdb.connect('outputs/full_run/imperial_theaters.duckdb')
loser='118e53f0-43b3-4cb8-b015-192faed9d74e'; surv='10991ea4-100c-4a02-9f15-6a09a57e4e73'
for eid,(old,new) in ch.items():
    cur=str(con.execute("select person_id from entities.person_link where entry_id=?",[eid]).fetchone()[0])
    assert cur==old,(eid,cur,old)
    con.execute("update entities.person_link set person_id=?, match_method='manual_realign_131' where entry_id=?",[new,eid])
print('relinked',len(ch))
assert con.execute("select count(*) from entities.person_link where person_id=?",[loser]).fetchone()[0]==0
con.execute("update entities.person set superseded_by_person_id=? where person_id=?",[surv,loser])
con.execute("""insert into entities.person_merge_log values (?,?,?,?,?,?,?,?,?,?)""",
  [str(uuid.uuid4()),loser,surv,'Розовъ, Александръ Ѳедоровичъ','Розовъ, Александръ Ѳедоровичъ',1.0,'link_misalignment_repair_131','confirmed_manual','manual','stray person created by a shifted person_link block on administration_1894-95_p002; same name/patronymic/start date as the long-lived person'])
print('tombstoned stray Розовъ; merge log row added')
con.close()
