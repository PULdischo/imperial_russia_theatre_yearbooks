import json,glob,shutil,os
B='outputs/full_run_pre_promote_backup_2026-10-02_nameaudit/raw/'
MAP={'Виолончель':'Віолончель','Біолончель':'Віолончель','Вальдгорнь':'Вальдгорнъ','Вальдгорнт':'Вальдгорнъ','сріпка':'срипка'}
SPEC={('1899-00_MSK_p000',10):('Вальторнъ','Вальдгорнъ'),('1900-01_MSK_p001',7):('Вальторнъ','Вальдгорнъ')}
log=[]
for f in sorted(glob.glob('outputs/full_run/raw/musicians_*.raw.json')):
    pg=f.split('/')[-1][10:-9]; d=json.load(open(f)); ch=False
    for i,e in enumerate(d['entries']):
        for k in ('tenure_note_text','rank_or_title'):
            v=e.get(k) or ''; nv=v
            for o,n in MAP.items(): nv=nv.replace(o,n)
            if (pg,i+1) in SPEC and k=='tenure_note_text': nv=nv.replace(*SPEC[(pg,i+1)])
            if nv!=v: e[k]=nv; ch=True; log.append((pg,i+1,k,v,nv))
    if ch:
        if not os.path.exists(B+os.path.basename(f)): shutil.copy(f,B)
        json.dump(d,open(f,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
print(len(log)); [print(l) for l in log]
json.dump(log,open('/tmp/audit6/residual_log.json','w'),ensure_ascii=False,indent=1)
