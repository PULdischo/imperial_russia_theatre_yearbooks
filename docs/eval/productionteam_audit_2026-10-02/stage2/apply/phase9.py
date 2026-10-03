import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
try: E.set_field(PT+'1897-98_p002','e025','family','Ѳоктистовъ','Ѳеоктистовъ',log)
except Exception as ex: fails.append(str(ex)[:150])
try: E.set_field(PT+'1894-95_p001','e018','first','Евлокія','Евдокія',log)
except Exception as ex: fails.append(str(ex)[:150])
for n,t in ((16,'Маріинскій'),(17,'Александринскій'),(18,'Михайловскій')):
    x=E.ent(PT+'1903-04_p001','e%03d'%n); old=x['heading_path']; exp='С.-ПЕТЕРБУРГЪ / Отдѣлъ бутафорскій / %s театръ / Бутафоры'%t
    if old!=exp: fails.append((n,old)); continue
    x['heading_path']='С.-ПЕТЕРБУРГЪ / Отдѣлъ бутафорскій / Бутафоры / %s театръ'%t; log.append((PT+'1903-04_p001','e%03d'%n,'heading_path',old,x['heading_path']))
print(len(log),'changes;',len(fails),'fails',fails)
