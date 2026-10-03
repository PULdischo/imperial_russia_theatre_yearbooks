import sys,json
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
REM={'1892-93_p002':(['e005','e008','e010','e011','e014','e017'],False),   # heading lines parsed as person rows; DB already skips them
     '1894-95_p001':(['e008','e012','e015'],True),'1891-92_p002':(['e004'],True),'1904-05_p002':(['e005'],True),
     '1905-06_p004':(['e002'],True),'1906-07_p004':(['e002'],True),'1907-08_p004':(['e002'],True)}
removed=[];plan={'remove':{},'add':[]}
for pg,(es,indb) in REM.items():
    d=E.load(PT+pg)['entries']
    idx=sorted([int(e[1:])-1 for e in es],reverse=True)
    for i in idx:
        x=d[i]; fam=(x.get('family_name') or '')
        assert (not fam) or fam in ('Александринскій театръ','Сизовъ','Оствайлъ') or fam.startswith('Съ 1 іюля 1895'),(pg,i+1,fam)
        removed.append(dict(page=PT+pg,entry='e%03d'%(i+1),row=x)); del d[i]
    if indb: plan['remove'][PT+pg]=[int(e[1:]) for e in es]
ADD=[('1901-02_p001','3f1ba0c7-779c-4e10-8643-001af4015d86',dict(institution='Императорскіе театры',heading_path='Машинисты-механики и ихъ помощники / Маріинскій театръ / Машинистъ-механикъ',list_number=None,family_name='Бергеръ',first_name='Николай',patronymic='Александровичъ',tenure_note_text='(съ 5 октября 1880 г.).',service_periods=[dict(start_date_text='5 октября 1880 г.',end_date_text=None,end_type=None)])),
     ('1901-02_p002','0995a2d1-df1e-48ac-a51b-a13bd6467af5',dict(institution='Парикмахеры:',heading_path='Парикмахеры: / Балетная труппа',list_number=None,family_name='Педдеръ',first_name='Георгій',patronymic='Ивановичъ',tenure_note_text='(съ 1 марта 1879 г.). Мужскіе и женскіе парики.',service_periods=[dict(start_date_text='1 марта 1879 г.',end_date_text=None,end_type=None)])),
     ('1897-98_p002','4edaf0e2-d2e3-47c9-96cd-117595a9dbf3',dict(institution='Главный гардеробъ',heading_path='Михайловскій театръ',list_number=None,family_name='Ковалевъ',first_name='Андрей',patronymic='Ѳедоровичъ',tenure_note_text='(съ 1 мая 1888 г.).',service_periods=[dict(start_date_text='1 мая 1888 г.',end_date_text=None,end_type=None)]))]
for pg,pid,row in ADD:
    d=E.load(PT+pg)['entries']; d.append(row); log.append((PT+pg,'e%03d'%len(d),'ADDED',row['family_name']))
    plan['add'].append(dict(entry_id=PT+pg+'__e%03d'%len(d),person_id=pid))
print(len(removed),'rows removed;',len(log),'added;',len(fails),'fails')
json.dump(plan,open('/tmp/audit8/relink_plan.json','w'),ensure_ascii=False,indent=1)
json.dump(removed,open('/tmp/audit8/removed_rows.json','w'),ensure_ascii=False,indent=1)
