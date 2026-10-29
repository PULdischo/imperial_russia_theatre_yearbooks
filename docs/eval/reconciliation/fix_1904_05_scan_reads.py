"""1904-05 Repertoire: extraction errors found by the blind read of all six theater columns (2026-10-28,
docs/eval/scan_audit/1904-05_scan_reads.csv) and checked by Claude on ForUpload_1904-05_Repertoire.pdf (page index = pNNN).
Reconciliation ledger 1904-05.

1. Малый, 1 Oct 1904 (p005, idx 20): stored as a dark placeholder («manual_uncertain_dark_placeholder»); the print has
   «Сенъ-Марсъ, тр.» 651 р. 56 к.
2. Большой, 2 Feb 1905 (p029): the Шаляпинъ charity cell prints no receipts; «3028 р. 21 к.» was copied up from 3 Feb.
3. Новый, 30-31 Oct 1904 (p011, idx 21-22): 30 Oct is a dash; 31 Oct is divided, УТРО «Первая ласточка» 294 р. 55 к.,
   ВЕЧЕРЪ «Марта» 828 р. 32 к. The extraction put the matinee on 30 Oct. Same on 6-7 Nov (idx 27-28: УТРО «Снѣгурочка»
   403 р. 96 к., ВЕЧЕРЪ «Риголетто» 830 р. 90 к.). The two rows keep their places (event ids unchanged) and take the right
   date/session; the two dark days are appended at the end of the array so no later row shifts.
4. Новый, 25-27 Feb 1905 evenings (p033, idx 33, 35, 37): stored «403 р. 01 к.» (the matinees' figure, copied); print
   1183 р. 94 к., 1187 р. 12 к., 1041 р. 57 к.
5. Михайловскій, 24 Apr 1905 (p042, idx 22): «480 р. 50 к.» -> «430 р. 50 к.» (flat-topped 3, open on the left; the 8 of
   «809» on the same line is closed and round).
6. Большой, 19 Apr 1905 evening (p041, idx 8): the banner «Спектакли въ пользу Иверской Общины Краснаго Креста.» spans the
   Большой and Малый cells of the whole day; it was attached to the Большой morning and the Малый evening only.

uv run python docs/eval/reconciliation/fix_1904_05_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-28 (blind column read, 1904-05 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1904-05_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: {msg}"


def save(p, d, fmt):
    if "--write" in sys.argv:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")


def dark(template, date_text):
    return {"date_text": date_text, "month_text": None, "year_text": None, "session": "unspecified",
            "theater": template["theater"], "is_dark": True, "receipts_text": None, "annotation": None, "works": [],
            "_fix_note": f"{TAG}: dash in the print; added at the end of the array (no row shift)"}


# 1. Малый 1 Oct 1904
p, d, f = load("p005"); S = d["sessions"][20]
assert S["date_text"] == "1 Пятница" and S["theater"].startswith("Малый") and S["is_dark"] and not S["works"], S
assert S.get("_repair_tier") == "manual_uncertain_dark_placeholder", S
S.update(is_dark=False, receipts_text="651 р. 56 к.", works=[{"work_title": "Сенъ-Марсъ", "genre": "тр."}])
note(S, "dark placeholder -> «Сенъ-Марсъ, тр.» 651 р. 56 к.")
save(p, d, f); print("p005", S["date_text"], S["works"], S["receipts_text"])

# 2. Большой 2 Feb 1905
p, d, f = load("p029")
hits = [S for S in d["sessions"] if S["date_text"] == "2 Среда." and S["theater"].startswith("Большой")]
assert len(hits) == 1; S = hits[0]
assert S["receipts_text"] == "3028 р. 21 к." and "Шаляпин" in (S["annotation"] or ""), S
S["receipts_text"] = None
note(S, "receipts «3028 р. 21 к.» -> none (no figure printed; copied from 3 Feb)")
save(p, d, f); print("p029", S["date_text"], S["theater"], S["receipts_text"])

# 3. Новый 30/31 Oct and 6/7 Nov 1904
p, d, f = load("p011"); ss = d["sessions"]
for i_m, i_e, d_old, d_new, w_m, r_m, w_e, r_e, dark_text in (
        (21, 22, "30 Суббота.", "31 Воскрес.", "Первая ласточка", "294 р. 55 к.", "Марта", "828 р. 32 к.", "30 Суббота."),
        (27, 28, "6 Суббота.", "7 Воскрес.", "Снѣгурочка, весенняя сказка", "403 р. 96 к.", "Риголетто", "830 р. 90 к.",
         "6 Суббота.")):
    M, E = ss[i_m], ss[i_e]
    assert M["theater"].startswith("Новый") and E["theater"].startswith("Новый")
    assert M["date_text"] == d_old and M["works"][0]["work_title"] == w_m and M["receipts_text"] == r_m, M
    assert E["date_text"] == d_new and E["works"][0]["work_title"] == w_e and E["receipts_text"] == r_e, E
    assert M["session"] == E["session"] == "unspecified"
    M.update(date_text=d_new, session="morning"); note(M, f"date «{d_old}» -> «{d_new}», session -> morning (УТРО)")
    E["session"] = "evening"; note(E, "session -> evening (ВЕЧЕРЪ)")
    assert not [S for S in ss if S["date_text"] == dark_text and S["theater"].startswith("Новый")]
    ss.append(dark(M, dark_text))
save(p, d, f); print("p011", len(ss), "sessions")

# 4. Новый 25-27 Feb 1905 evenings
p, d, f = load("p033"); ss = d["sessions"]
for i, dt, title, new in ((33, "25 Пятница.", "Соломенная шляпка", "1183 р. 94 к."),
                          (35, "26 Суббота.", "Въ сельцѣ Отрадномъ", "1187 р. 12 к."),
                          (37, "27 Воскрес.", "Фра-Діаволо", "1041 р. 57 к.")):
    S = ss[i]
    assert S["date_text"] == dt and S["session"] == "evening" and S["theater"].startswith("Новый"), S
    assert S["works"][0]["work_title"] == title and S["receipts_text"] == "403 р. 01 к.", S
    S["receipts_text"] = new; note(S, f"receipts «403 р. 01 к.» -> «{new}» (matinee figure copied in extraction)")
save(p, d, f); print("p033 done")

# 5. Михайловскій 24 Apr 1905
p, d, f = load("p042"); S = d["sessions"][22]
assert S["date_text"] == "24 Воскрес." and S["theater"].startswith("Михайлов") and S["receipts_text"] == "480 р. 50 к.", S
S["receipts_text"] = "430 р. 50 к."; note(S, "receipts «480 р. 50 к.» -> «430 р. 50 к.» (3 read as 8)")
save(p, d, f); print("p042", S["receipts_text"])

# 6. Большой 19 Apr 1905 evening banner
p, d, f = load("p041"); A, B = d["sessions"][7], d["sessions"][8]
banner = "Спектакли въ пользу Иверской Общины Краснаго Креста."
assert A["annotation"] == banner and A["session"] == "morning" and A["theater"].startswith("Большой"), A
assert B["date_text"] == "19 Вторн." and B["session"] == "evening" and B["theater"].startswith("Большой"), B
assert B["annotation"] is None and B["works"][0]["work_title"] == "Травіата", B
B["annotation"] = banner; note(B, "banner spans the whole day's Большой and Малый cells; attached to the evening too")
save(p, d, f); print("p041", B["annotation"])

print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
