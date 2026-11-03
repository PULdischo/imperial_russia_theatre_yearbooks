"""1905-06 Repertoire: extraction errors found by the season's ballet-review check and the blind read of the Маріинскій and
Большой columns (2026-11-02, docs/eval/scan_audit/1905-06_scan_reads.csv, 544 rows; every receipts figure already matched).
Each cell checked by Claude on ForUpload_1905-06_Repertoire.pdf (page index = pNNN). Reconciliation ledger 1905-06.
RG 2026-11-02: "Yes, apply all 15".

Маріинскій
 1-2. 5/6 Nov and 12/13 Nov 1905 (p012): Saturdays 5 and 12 Nov print a dash; Sunday 6 and 13 Nov are divided, УТРО «Демонъ
      оп.» 1996 р. 53 к. / «Евгеній Онѣгинъ, оп.» 1983 р. 30 к., ВЕЧЕРЪ the ballet bill. The extraction put each matinée on the
      Saturday. The rows keep their places (event ids unchanged) and take the right date/session; the two dark Saturdays are
      appended at the end of the array so no later row shifts.
 3.   12 Feb 1906 (p032) Гердтъ benefit: «3 и 5 карт. бал. Баядерка.» is printed as a work line above «Жавотта, бал.»; it was
      stored inside the annotation. Now a work (first, as printed); annotation keeps the benefit heading only.
 4-5. 3 Apr 1906 (p040) «1 д. бал. Донъ-Кихотъ.»; 15 Apr (p042) «1-е и 2-е д, бал. Тщетная предосторожность.»: act numbers
      restored to the titles (3 Apr's «1 д.» had gone to the annotation; 15 Apr's was lost).
 6.   4 Apr 1906 (p040) «4-е д. оп. Отелло.»: act number restored (it had gone to the annotation).
 7-8. 22 and 29 Sep 1905 (p004) «1, 2, 3 и 4 д. оп. Гугеноты»: acts restored from the annotation.
 9-10. 1 and 8 Sep 1905 (p000) «Самсонъ и Далида» -> «Далила»; 11. 10 Oct (p006) «Даліла» -> «Далила» (print: Далила).
 12.  28 Jan 1906 (p028) annotation «сестрах» -> «сестрахъ»; 13. 23 Mar (p038) «спектакль-гала» -> «спектакль-gala» (Latin in the
      print); 14. 8 Apr (p042) «попечения» -> «попеченія».
Большой
 15a. 26 Nov 1905 (p017): the charity concert cell prints no work; «Дочь фараона, бал.» had bled in from 27 Nov. Works removed.
 15b. 20 Sep 1905 (p003) «1, 2, 3 и 4 д. оп. Гугеноты.»: acts restored from the annotation.
 15c. 30 Apr 1906 (p047) «3 д. бал. Эсмеральда.»: act number restored.
(RG approved "15"; the Большой items are numbered 15a-c, so the script touches 17 cells.)

Act prefixes follow this season's stored convention («2-е д. Талисманъ» | бал.): the act words stay in the title, the genre in
the genre field.

uv run python docs/eval/reconciliation/fix_1905_06_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-11-02 (review check + blind column read, 1905-06 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1905-06_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
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


def one(ss, theater, date_text, session=None):
    hits = [S for S in ss if S["theater"].startswith(theater) and S["date_text"] == date_text
            and (session is None or S["session"] == session)]
    assert len(hits) == 1, (theater, date_text, hits)
    return hits[0]


MAR = "Ма"  # «Мариинскій»/«Маріинскій» both occur in this season's raw

# 1-2. Маріинскій matinées
p, d, f = load("p012"); ss = d["sessions"]
for i_m, i_e, d_old, d_new, w_m, r_m, w_e0, r_e in (
        (23, 24, "5 Суббота.", "6 Воскрес.", "Демонъ", "1996 р. 53 к.", "Пробужденіе Флоры", "2814 р. 45 к."),
        (30, 31, "12 Суббота.", "13 Воскрес.", "Евгеній Онѣгинъ", "1983 р. 30 к.", "Гарлемскій тюльпанъ", "2729 р. 95 к.")):
    M, E = ss[i_m], ss[i_e]
    assert M["theater"].startswith(MAR) and E["theater"].startswith(MAR)
    assert M["date_text"] == d_old and M["works"][0]["work_title"] == w_m and M["receipts_text"] == r_m, M
    assert E["date_text"] == d_new and E["works"][0]["work_title"] == w_e0 and E["receipts_text"] == r_e, E
    assert M["session"] == E["session"] == "unspecified"
    M.update(date_text=d_new, session="morning"); note(M, f"date «{d_old}» -> «{d_new}», session -> morning (УТРО)")
    E["session"] = "evening"; note(E, "session -> evening (ВЕЧЕРЪ)")
    assert not [S for S in ss if S["date_text"] == d_old and S["theater"].startswith(MAR)]
    ss.append(dark(M, d_old))
save(p, d, f); print("p012", len(ss), "sessions")

# 3. Маріинскій 12 Feb, Гердтъ benefit
p, d, f = load("p032"); S = one(d["sessions"], MAR, "12 Воскрес.", "evening")
head = "Бенефисъ солиста Его Величества П. А. Гердта за 45-ти лѣтнюю службу."
assert S["annotation"] == head + " 3 и 5 карт. бал. Баядерка." and [w["work_title"] for w in S["works"]] == ["Жавотта"], S
S["annotation"] = head
S["works"].insert(0, {"work_title": "3 и 5 карт. Баядерка", "genre": "бал."})
note(S, "«3 и 5 карт. бал. Баядерка.» moved from the annotation to a work (printed first, above «Жавотта»)")
save(p, d, f); print("p032", S["works"])

# 4, 6. Маріинскій 3 and 4 Apr
p, d, f = load("p040"); ss = d["sessions"]
S = one(ss, MAR, "3 Понед.")
assert S["annotation"].endswith(" 1 д.") and S["works"][0] == {"work_title": "Донъ-Кихотъ", "genre": "бал."}, S
S["annotation"] = S["annotation"][:-len(" 1 д.")]; S["works"][0]["work_title"] = "1 д. Донъ-Кихотъ"
note(S, "act «1 д.» moved from the annotation into the title («1 д. бал. Донъ-Кихотъ.»)")
S = one(ss, MAR, "4 Вторн.")
assert S["annotation"].endswith(" 4-е д.") and S["works"][1] == {"work_title": "Отелло", "genre": "оп."}, S
S["annotation"] = S["annotation"][:-len(" 4-е д.")]; S["works"][1]["work_title"] = "4-е д. Отелло"
note(S, "act «4-е д.» moved from the annotation into the title («4-е д. оп. Отелло.»)")
save(p, d, f); print("p040 done")

# 5, 14. Маріинскій 15 Apr and 8 Apr
p, d, f = load("p042"); ss = d["sessions"]
S = one(ss, MAR, "15 Суббота.")
assert S["works"][1] == {"work_title": "Тщетная предосторожность", "genre": "бал."}, S
S["works"][1]["work_title"] = "1-е и 2-е д, Тщетная предосторожность"
note(S, "acts restored as printed («1-е и 2-е д, бал. Тщетная предосторожность.», comma as printed)")
S = one(ss, MAR, "8 Суббота.")
assert "попечения" in S["annotation"], S
S["annotation"] = S["annotation"].replace("попечения", "попеченія"); note(S, "annotation «попечения» -> «попеченія»")
save(p, d, f); print("p042 done")

# 7-8. Маріинскій 22 and 29 Sep «Гугеноты»
p, d, f = load("p004"); ss = d["sessions"]
for dt in ("22 Четвергъ.", "29 Четвергъ."):
    S = one(ss, MAR, dt)
    assert S["annotation"] == "1, 2, 3 и 4 д." and S["works"] == [{"work_title": "Гугеноты", "genre": "оп."}], S
    S["annotation"] = None; S["works"][0]["work_title"] = "1, 2, 3 и 4 д. Гугеноты"
    note(S, "acts «1, 2, 3 и 4 д.» moved from the annotation into the title")
save(p, d, f); print("p004 done")

# 9-11. «Самсонъ и Далила»
for pg, dt, old in (("p000", "1 Четв.", "Самсонъ и Далида"), ("p000", "8 Четвергъ.", "Самсонъ и Далида"),
                    ("p006", "10 Понед.", "Самсонъ и Даліла")):
    p, d, f = load(pg); S = one(d["sessions"], MAR, dt)
    assert S["works"][0]["work_title"] == old, S
    S["works"][0]["work_title"] = "Самсонъ и Далила"; note(S, f"title «{old}» -> «Самсонъ и Далила» (print)")
    save(p, d, f); print(pg, dt, "Далила")

# 12-13. annotations
for pg, dt, old, new in (("p028", "28 Воскрес.", "о сестрах милосердія", "о сестрахъ милосердія"),
                         ("p038", "23 Четвергъ.", "спектакль-гала", "спектакль-gala")):
    p, d, f = load(pg); S = one(d["sessions"], MAR, dt)
    assert old in S["annotation"], S
    S["annotation"] = S["annotation"].replace(old, new); note(S, f"annotation «{old}» -> «{new}» (print)")
    save(p, d, f); print(pg, dt, new)

# 15a. Большой 26 Nov
p, d, f = load("p017"); S = one(d["sessions"], "Большой", "26 Суббота.")
assert S["works"] == [{"work_title": "Дочь фараона", "genre": "бал."}] and "музыкально-литературный" in S["annotation"], S
S["works"] = []; note(S, "work «Дочь фараона, бал.» removed: the cell prints no work (bled in from 27 Nov)")
save(p, d, f); print("p017 26 Nov works", S["works"])

# 15b. Большой 20 Sep «Гугеноты»
p, d, f = load("p003"); S = one(d["sessions"], "Большой", "20 Вторникъ.")
assert S["annotation"] == "1, 2, 3 и 4 д." and S["works"] == [{"work_title": "Гугеноты", "genre": "оп."}], S
S["annotation"] = None; S["works"][0]["work_title"] = "1, 2, 3 и 4 д. Гугеноты"
note(S, "acts «1, 2, 3 и 4 д.» moved from the annotation into the title")
save(p, d, f); print("p003 done")

# 15c. Большой 30 Apr
p, d, f = load("p047"); S = one(d["sessions"], "Большой", "30 Воскрес.")
assert S["works"][0] == {"work_title": "Эсмеральда", "genre": "бал."}, S
S["works"][0]["work_title"] = "3 д. Эсмеральда"; note(S, "act restored («3 д. бал. Эсмеральда.»)")
save(p, d, f); print("p047 done")

print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
