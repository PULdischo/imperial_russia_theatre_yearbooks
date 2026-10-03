import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
def setk(pg,e,key,old,new):
    x=E.ent(PT+pg,e); cur=x.get(key)
    if (cur or None)!=(old or None): fails.append((pg,e,key,cur,old)); return
    x[key]=new; log.append((PT+pg,e,key,cur,new))
# blind-sample fixes
setk('1902-03_p003','e021','first_name','Казимира','Казиміра')
setk('1909-10_p001','e007','tenure_note_text','съ 25 октября 1897 г.','сь 25 октября 1897 г.')
setk('1893-94_p002','e024','patronymic','Никіфоровичъ','Никифоровичъ')
for n,old in ((3,'И. д.'),(4,'И. д.'),(5,'И. обв.'),(6,'И. д.'),(7,'И. д.'),(8,'И. д.'),(9,'И. д.')): setk('1901-02_p003','e%03d'%n,'list_number',old,None)
setk('1900-01_p002','e007','list_number',None,'1.')
setk('1906-07_p002','e012','tenure_note_text','(съ 1 октября 1882 г.). Оставила службу 1 августа 1907 г.','(съ 1 октября 1882 г.). Оставилъ службу 1 августа 1907 г.')
for pg,e,old in (('1902-03_p002','e009','Отдѣлъ мужскихъ костюмовъ'),('1903-04_p002','e008','Отдѣлъ мужскихъ костюмовъ'),('1903-04_p002','e009','Отдѣлъ головныхъ уборовъ, обуви и бѣлья'),('1904-05_p004','e002','Костюмерша'),('1904-05_p004','e003','Художникъ-консультантъ')): setk(pg,e,'rank_or_title',old,None)
# missing row: Педдеръ, Балетная труппа, 1898-99 p002 (appended at END of the page array -> e025)
d=E.load(PT+'1898-99_p002')['entries']
assert len(d)==24 and not any(x['family_name']=='Педдеръ' and 'Балетная' in x['heading_path'] for x in d)
new={"institution":"Списокъ личнаго состава служащихъ по монтировочной части.","heading_path":"С.-ПЕТЕРБУРГЪ / Отдѣлъ гардеробный / Парикмахеры / Балетная труппа","family_name":"Педдеръ","first_name":"Георгій","patronymic":"Ивановичъ","rank_or_title":"Мужскіе и женскіе парики.","tenure_note_text":"(съ 1 марта 1879 г.).","service_periods":[{"start_date_text":"1 марта 1879 г.","end_date_text":None,"end_type":None}]}
d.append(new); log.append((PT+'1898-99_p002','e025','ROW ADDED',None,new['heading_path']))
print(len(log),'changes;',len(fails),'fails',fails)
