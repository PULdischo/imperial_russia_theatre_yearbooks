import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
for n in (15,16,17,18):
    x=E.ent('productionteam_1900-01_p003','e%03d'%n); old=x['heading_path']
    if old!='МОСКВА / Большой театръ / Помощники-машиниста': fails.append((n,old)); continue
    x['heading_path']='МОСКВА / Отдѣлъ декораціонный / Большой театръ / Помощники-машиниста'; log.append(('productionteam_1900-01_p003','e%03d'%n,'heading_path',old,x['heading_path']))
print(len(log),'changes;',len(fails),'fails',fails)
