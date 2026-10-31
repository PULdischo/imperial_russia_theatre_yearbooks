import re
CAT = re.compile(r'(?:^|[;.]\s*|\s)[Вв]ъ\s+(?:\d+\s+)?([^\s—;.()]+)\s*(?:—\s*)?(\d+)')
TOT = re.compile(r'Всего\s*(?:—\s*)?(?:въ\s+\d+\s+\S+\s*—\s*)?(\d+)')
WORK = re.compile(r'(?:^|[;:.]\s*|(?<=\))\s*,\s*)([^;:.(),]+?)\s*\(([^()]*)\)')
def strip_parens(t): return re.sub(r'\([^()]*\)', '', t)
def credits(t):
    out = []
    head = t.split('Въ томъ числѣ:')[0]
    for lab, n in CAT.findall(strip_parens(head)):
        out.append({'credit_type': 'category_totals', 'label': lab, 'count': int(n)})
    m = TOT.search(strip_parens(t))
    if m: out.append({'credit_type': 'category_totals', 'label': 'Всего', 'count': int(m.group(1))})
    for work, roles in WORK.findall(t):
        work = work.strip()
        for r in re.split(r'(?<=\d)\s*,\s*', roles):
            mm = re.match(r'\s*(.+?)\s*—\s*(\d+)\s*$', r)
            if not mm: raise ValueError(('role', work, r, t))
            out.append({'credit_type': 'named_work', 'label': work, 'role_name': mm.group(1), 'count': int(mm.group(2))})
    return out
if __name__ == '__main__':
    import json
    for t in ['Въ 14 балетахъ—22; въ 3 операхъ—13. Всего—35 разъ. Въ томъ числѣ: Гарлемскій тюльпанъ (бабочка—2); Спящая красавица (фея-крошка—1, фея-Кандидъ—1, красная шапочка—3).',
              'Индія (Тассира—4); Кипрская статуя (Галатея—3). Всего—10 разъ.', 'Въ балетахъ—45; въ операхъ—56; въ драмѣ—1. Всего—102 раза.',
              'Волшебная флейта (маркизъ—1); Коппелія (Коппеліусъ—2). Всего—въ 3 балетахъ—4 раза.']:
        print(json.dumps(credits(t), ensure_ascii=False))
