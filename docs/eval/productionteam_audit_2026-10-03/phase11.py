import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
PT='productionteam_'
try: E.replace_in(PT+'1891-92_p001','e015','tenure_note_text','труппы.','труппъ.',log)
except Exception as ex: fails.append(str(ex)[:150])
try:
    x=E.ent(PT+'1898-99_p002','e002'); assert x['service_periods'][0]['start_date_text']=='19. мая 1869 г.'
    E.set_period(PT+'1898-99_p002','e002',0,start='19 мая 1869 г.',log=log)
except Exception as ex: fails.append(str(ex)[:150])
print(len(log),'changes;',len(fails),'fails',fails)
