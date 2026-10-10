"""Add the four confirmed gaps (issue #151 follow-up 8; RG: "yes, add the four known gaps", 2026-10-10).
Each cell read blind on the scan by two readers where a second reading existed (gap_70.csv, gap_70b.csv; cells_33/C088/C098 earlier).
  G1 repertoire_1902-03_p018 (printed p. 20), 28 Суббота, Александринскій: the stored session is the ВЕЧЕРЪ half (banner + «Побѣда», no receipts
     printed); the missing УТРО half «Воспитатель Флаксманъ, ком. | Великая тайна.» with receipts 409 р. 86 к. is added.
  G2 repertoire_1893-94_pair010 (printed p. 10), 21 Воскрес., Александринскій: stored = ВЕЧЕРЪ (receipts 1658 р. 40 к.); added УТРО
     «Мертвыя души (2-я часть), сц.», receipts 484 р. 60 к.
  G3 repertoire_1898-99_p028 (printed p. 30), 21 Воскрес. февраля 1899, Александринскій: stored = УТРО (Женитьба + Въ чужомъ пиру похмѣлье,
     631 р. 09 к.); added ВЕЧЕРЪ «Сердце не камень, ком. | Мечта, др. сц.», receipts 1653 р. 70 к.
  G4 repertoire_1904-05_p011 (printed p. 101): the whole Moscow row printed «23 Пятница.» (a misprint for 5 Nov; between «4 Четв.» and
     «6 Суббота.») was absent: Большой «Гугеноты, оп.» 1489 р. 85 к.; Малый «Упразднители, ком.» 673 р. 63 к.; Новый «Потокъ, др. | Изъ-за
     мышенка, ком.» 218 р. 45 к. The printed day text is kept verbatim; the date is corrected by _MANUAL_DATE_OVERRIDES (validate_performance_dates.py).
New sessions are appended at the END of each page's sessions array so no existing event id shifts (#131-style rule).
uv run python docs/eval/title_check_2026-10-10/apply_gap_sessions.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw"
SRC = "issue #151 follow-up 8: added from the scan (read blind, 2026-10-10)"
def new(date_text, month, year, session, theater, receipts, works, ann=None):
    return {"date_text": date_text, "month_text": month, "year_text": year, "session": session, "theater": theater, "is_dark": False,
            "receipts_text": receipts, "annotation": ann, "works": [{"work_title": t, "genre": g} for t, g in works], "_source": SRC}
PLAN = [
    # (page, index (1-based) of the existing session, expected stored title, label to give it, new session)
    ("repertoire_1902-03_p018", 26, "Побѣда", "evening",
     new("28 Суббота.", None, None, "morning", "Александринскій театръ.", "409 р. 86 к.", [("Воспитатель Флаксманъ", "ком."), ("Великая тайна", None)])),
    ("repertoire_1893-94_pair010", 40, "Собака садовника", "evening",
     new("21 Воскрес.", None, None, "morning", "Александринскій.", "484 р. 60 к.", [("Мертвыя души (2-я часть)", "сц.")])),
    ("repertoire_1898-99_p028", 15, "Женитьба", "morning",
     new("21 Воскрес.", "февраля.", "1899 г.", "evening", "Александринскій театръ", "1653 р. 70 к.", [("Сердце не камень", "ком."), ("Мечта", "др. сц.")])),
]
G4 = ("repertoire_1904-05_p011", [
    new("23 Пятница.", None, None, "unspecified", "Большой театръ.", "1489 р. 85 к.", [("Гугеноты", "оп.")]),
    new("23 Пятница.", None, None, "unspecified", "Малый театръ.", "673 р. 63 к.", [("Упразднители", "ком.")]),
    new("23 Пятница.", None, None, "unspecified", "Новый театръ.", "218 р. 45 к.", [("Потокъ", "др."), ("Изъ-за мышенка", "ком.")]),
])
def load(page):
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    return p, d, fmt
w = "--write" in sys.argv
for page, idx, title, label, ns in PLAN:
    p, d, f = load(page); S = d["sessions"]; cur = S[idx - 1]
    assert cur["works"][0]["work_title"] == title and cur["session"] == "unspecified", (page, cur)
    cur["session"] = label; S.append(ns)
    print(f"{page}: s{idx} -> {label}; appended s{len(S)} ({ns['session']}, {ns['receipts_text']}, {[x['work_title'] for x in ns['works']]})")
    if w: p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
p, d, f = load(G4[0]); S = d["sessions"]
assert not any((s["date_text"] or "").startswith("23") for s in S)
for ns in G4[1]:
    S.append(ns); print(f"{G4[0]}: appended s{len(S)} {ns['theater']} {ns['receipts_text']} {[x['work_title'] for x in ns['works']]}")
if w: p.write_text(json.dumps(d, indent=f[0], ensure_ascii=f[1]) + f[2], encoding="utf-8")
print("WROTE" if w else "DRY RUN")
