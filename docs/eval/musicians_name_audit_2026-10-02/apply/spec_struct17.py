S=[]
def A(pg,e,**kw): S.append(('musicians_'+pg,e,kw))
for e,fam in (('e005','Вальтеръ 2-й'),('e044','Тарнке 1-й'),('e045','Тарнке 2-й')):
    A('1890-91_SP_p003',e,family_name=(fam.split()[0],fam),first_name=(fam.split()[1],None),patronymic=('см. оперный оркестръ',None),tenure_note_text=('','(см. оперный оркестръ)'))
A('1899-00_MSK_p002','e024',family_name=('Ромашковъ','Ромашковъ 1-й'),first_name=('1-й','Капитонъ'),patronymic=('Капитонъ Андреевичъ','Андреевичъ'))
A('1899-00_MSK_p002','e025',family_name=('Ромашковъ','Ромашковъ 2-й'),first_name=('2-й','Павелъ'),patronymic=('Павелъ Ѳёдоровичъ','Ѳедоровичъ'))
A('1899-00_MSK_p002','e026',family_name=('Ромашковъ','Ромашковъ 3-й'),first_name=('3-й','Григорій'),patronymic=('Григорій Ѳёдоровичъ','Ѳедоровичъ'))
A('1899-00_MSK_p003','e018',family_name=('Шмидтъ','Шмидтъ 1-й'),first_name=('І-й','Францъ'),patronymic=('Францъ',None))
A('1899-00_MSK_p003','e019',family_name=('Шмидтъ','Шмидтъ 2-й'),first_name=('2-й','Фридрихъ'),patronymic=('Фридрихъ',None))
A('1899-00_MSK_p003','e025',family_name=('Эйхенвальдъ','Эйхенвальдъ 1-я'),first_name=('1-я','Ида'),patronymic=('Ида',None))
A('1899-00_MSK_p003','e026',family_name=('Эйхенвальдъ','Эйхенвальдъ 2-я'),first_name=('2-я','Надежда'),patronymic=('Надежда','Александровна'))
