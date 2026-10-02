import sys,json,shutil,os
sys.path.insert(0,'/tmp/audit6'); import engine
WRITE='--write' in sys.argv
ST='Солистъ Двора Его Императорскаго Величества'; SK='Солистка Двора Его Императорскаго Величества'; SB='Солистъ балета.'
rows=[('1890-91_SP_p002','e036',ST),('1891-92_SP_p002','e045',ST),('1892-93_SP_p002','e032',ST),('1893-94_SP_p000','e012',ST),
('1890-91_SP_p002','e012',ST),('1891-92_SP_p002','e021',ST),('1892-93_SP_p002','e008',ST),('1897-98_SP_p002','e033',ST),('1898-99_SP_p003','e033',ST),
('1900-01_SP_p003','e038',ST),('1902-03_SP_p003','e029',ST),('1903-04_SP_p003','e017',ST),
('1897-98_SP_p002','e036',SK),('1898-99_SP_p003','e036',SK),('1902-03_SP_p003','e031',SK),('1903-04_SP_p003','e019',SK),('1904-05_SP_p003','e024',SK),
('1909-10_MSK_p002','e026',SB)]
log=[]
for pg,e,t in rows:
    x=engine.resolve('musicians_'+pg,e)
    assert not (x.get('rank_or_title') or '').strip(),(pg,e,x.get('rank_or_title'))
    ten=x['tenure_note_text']; core=t.rstrip('.')
    cand=' '+t+'.' if not t.endswith('.') else ' '+t
    assert cand in ten,(pg,e,ten)
    x['rank_or_title']=t; x['tenure_note_text']=ten.replace(cand,'',1)
    log.append(('musicians_'+pg,e,'rank_or_title+tenure',ten,x['tenure_note_text'],t))
for e,n in (('e001','1.'),('e002','2.'),('e003','1.'),('e004','2.')):
    engine.apply_ops('musicians_1905-06_MSK_p001',e,{'list_number':(None,n)},log)
# duplicated phrase
x=engine.resolve('musicians_1891-92_SP_p004','e035'); d='Піанистъ при драматическихъ спектакляхъ при драматическихъ спектакляхъ.'
assert d in x['tenure_note_text'],x['tenure_note_text']
old=x['tenure_note_text']; x['tenure_note_text']=old.replace(d,'Піанистъ при драматическихъ спектакляхъ.'); log.append(('musicians_1891-92_SP_p004','e035','tenure_note_text',old,x['tenure_note_text']))
print(len(log),'edits'); [print(l[0][10:],l[1],l[3][:80],'=>',str(l[4])[:80]) for l in log if l[2]!='list_number']
if WRITE:
    B='outputs/full_run_pre_promote_backup_2026-10-02_titles/raw/'; os.makedirs(B,exist_ok=True)
    for p in engine._cache: shutil.copy(engine.R+p+'.raw.json',B)
    shutil.copy('outputs/full_run/imperial_theaters.duckdb',B+'../'); shutil.copytree('outputs/full_run/parsed',B+'../parsed',dirs_exist_ok=True)
    engine.write_all(); json.dump(log,open('/tmp/audit6/titles_log.json','w'),ensure_ascii=False,indent=1); print('WRITTEN')
