import sys,re
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
for pg,es in (('1905-06_p001',(4,5,6)),('1894-95_p003',(7,8))):
    for n in es:
        x=E.ent(PT+pg,'e%03d'%n); old=x['heading_path']
        m=re.fullmatch(r'(.*/ Отдѣлъ бутафорскій) / ([^/]+ театръ) / Бутафоры',old)
        if not m: fails.append((pg,n,old)); continue
        x['heading_path']=f'{m.group(1)} / Бутафоры / {m.group(2)}'; log.append((PT+pg,'e%03d'%n,'heading_path',old,x['heading_path']))
print(len(log),'changes;',len(fails),'fails',fails)
