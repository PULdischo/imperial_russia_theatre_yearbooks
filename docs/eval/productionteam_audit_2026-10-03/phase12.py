import sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
log=[];fails=[]
try: E.set_field('productionteam_1909-10_p002','e001','tenure_note_text','(съ 1 сентября 1889 г.). Мужскіе па- Мужскіе па-.','(съ 1 сентября 1889 г.). Мужскіе па-',log)
except Exception as ex: fails.append(str(ex)[:150])
print(len(log),'changes;',len(fails),'fails',fails)
