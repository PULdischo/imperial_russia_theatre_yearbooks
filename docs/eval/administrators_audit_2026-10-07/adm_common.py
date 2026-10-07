"""Shared helper: map the database entry number of a page to its raw array index, replicating parse_and_validate's row handling BEFORE numbering:
(1) _repair_roster: a row with a blank family_name is dropped unless heading_path holds a recoverable 'Surname, First Patronymic[, rest]' (then the name is recovered, heading_path := rest);
(2) _repair_fragment_person_entries: rows whose family_name is 'Оставилъ службу' or '†' are folded into the previous kept row and dropped."""
import re
NAME_IN_HEADING_RE = re.compile(r"^((?:(?:Графъ|Графиня|Князь|Княгиня|Баронъ|Баронесса)\s+)?[А-ЯЁІѢѲѴ][а-яёіѣѳѵ\-]+(?:\s+\d+-(?:й|я|е))?),\s+([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+)(?:\s+([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+))?(?:,\s*(.+))?$")
FRAG = {'Оставилъ службу', '†'}
def kept(entries):
    out = []; k = 0
    for ri, e in enumerate(entries):
        fam = (e.get('family_name') or '').strip()
        if not fam:
            if not NAME_IN_HEADING_RE.match((e.get('heading_path') or '').strip()): continue
            fam = 'recovered'
        if fam in FRAG: continue
        k += 1; out.append((k, ri))
    return out
