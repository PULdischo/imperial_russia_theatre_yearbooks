"""Stage A fixes from the column-structure read (issue #151 follow-up 15). Nothing here adds content that is not already stored:
only labels, session slots, theaters, and the split/merge of sessions are corrected. Every operation names the stored session it
expects (date label, receipts figure, first title) and the script stops if the page no longer matches.

    uv run python docs/eval/title_check_2026-10-10/align/apply_structure_fixes.py            # dry run
    uv run python docs/eval/title_check_2026-10-10/align/apply_structure_fixes.py --write

Evidence: align/reports (structure read, every cell of the page), align/reports_detail (cell-level reads; every figure below
was read on the scan), align/detail_verdicts.csv. Operations (all indices are the 1-based session numbers `sNNN` of the page):

  RELABEL   session s gets the date label of session `like` and a session slot (morning/evening/unspecified)
  DELETE    session s is a duplicate / empty slot for a cell that is printed once
  THEATER   session s is moved to the theater of session `like` (the French troupe's cell had been filed under Александринскій)
  MERGE     stored morning+evening of one undivided printed cell become one `unspecified` session (works of both, the figure)
  SPLIT     one stored session that holds the works of two printed halves becomes morning + evening (figure stays on the half
            it is printed under; a morning figure that was missing is added only where two readers agreed)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
NOTE = "slot/label corrected from the scan 2026-10-11 (column-structure read, issue #151 follow-up 15)"
P = "repertoire_"


def fix(page, ops):
    return (P + page, ops)


# (op, s, kw) ; `exp` = (date_text prefix, receipts_text or None, first work title prefix or None)
PLAN = [
    # ---- morning half stored on the preceding (dash) row: the dash-row session becomes the next day's morning
    fix("1894-95_pair008", [("RELABEL", 53, dict(like=56, session="morning", exp=("21", "334 р. 20 к.", "Ворогъ"))),
                            ("RELABEL", 56, dict(like=56, session="evening", exp=("22", "3353 р. 80 к.", None)))]),
    fix("1899-00_p026", [("RELABEL", 9, dict(like=10, session="morning", exp=("12", "789 р. 24 к.", "Борцы"))),
                         ("RELABEL", 10, dict(like=10, session="evening", exp=("13", "1652 р. — к.", "Девятый"))) ]),
    fix("1900-01_p006", [("RELABEL", 5, dict(like=6, session="morning", exp=("14", "2210 р 45 к.", "Фаустъ"))),
                         ("RELABEL", 6, dict(like=6, session="evening", exp=("15", "2876 р. 70 к.", "Щелкунчикъ")))]),
    fix("1903-04_p017", [("RELABEL", 21, dict(like=22, session="morning", exp=("13", "386 р. 26 к.", "Ревизоръ"))),
                         ("RELABEL", 22, dict(like=22, session="evening", exp=("14", "2213 р. — к.", "Сельская честь")))]),
    fix("1903-04_p022", [("RELABEL", 6, dict(like=7, session="morning", exp=("17", "1987 р. 03 к.", "Аида"))),
                         ("RELABEL", 7, dict(like=7, session="evening", exp=("18", "2839 р. 45 к.", "Лебединое")))]),
    fix("1904-05_p010", [("RELABEL", 26, dict(like=27, session="morning", exp=("30", "1870 р. 53 к.", "Пиковая"))),
                         ("RELABEL", 27, dict(like=27, session="evening", exp=("31", "2886 р. 45 к.", "Конекъ"))),
                         ("RELABEL", 33, dict(like=34, session="morning", exp=("6", "1930 р. 53 к.", "Дубровскій"))),
                         ("RELABEL", 34, dict(like=34, session="evening", exp=("7", "2892 р. 20 к.", "Спящая")))]),
    fix("1905-06_p013", [("RELABEL", 24, dict(like=25, session="morning", exp=("5", "256 р. 14 к.", "Женитьба"))),
                         ("RELABEL", 25, dict(like=25, session="evening", exp=("6", "678 р. 60 к.", "Искатели")))]),
    fix("1905-06_p029", [("RELABEL", 30, dict(like=31, session="morning", exp=("1", "— р. — к.", "Чужое"))),
                         ("RELABEL", 31, dict(like=31, session="evening", exp=("2", "1199 р. 33 к.", "Корридорная")))]),
    fix("1909-10_p020", [("RELABEL", 2, dict(like=3, session="morning", exp=("28", "665 р. 66 к.", "Вертеръ"))),
                         ("RELABEL", 3, dict(like=3, session="evening", exp=("29", "2841 р. 91 к.", "Коппелія")))]),
    fix("1903-04_p025", [("RELABEL", 33, dict(like=34, session="morning", exp=("1", "363 р. 96 к.", "Женитьба"))),
                         ("RELABEL", 34, dict(like=34, session="evening", exp=("2", "1170 р. 79 к.", "Пустоцвѣтъ")))]),
    fix("1900-01_p020", [("RELABEL", 18, dict(like=18, session="morning", exp=("31", "563 р. 26 к.", "Коварство"))),
                         ("RELABEL", 19, dict(like=18, session="evening", exp=("1", "1652 р. 65 к.", "Волки"))),
                         ("RELABEL", 20, dict(like=20, session="unspecified", exp=("1", "1646 р. 99 к.", "Дикарка")))]),
    # ---- a column that sits one slot early (the shift ends where a split absorbs it)
    fix("1907-08_p025", [("RELABEL", 15, dict(like=16, session="unspecified", exp=("5", "1318 р. 20 к.", "Ревизоръ"))),
                         ("RELABEL", 16, dict(like=17, session="unspecified", exp=("6", "546 р. 50 к.", "Въ старомъ"))),
                         ("RELABEL", 17, dict(like=18, session="unspecified", exp=("7", "699 р. 08 к.", "Джентльменъ"))),
                         ("RELABEL", 18, dict(like=19, session="unspecified", exp=("8", "854 р. 19 к.", "Доходное"))),
                         ("RELABEL", 19, dict(like=20, session="unspecified", exp=("9", "854 р. 16 к.", "Дѣльцы"))),
                         ("RELABEL", 20, dict(like=21, session="unspecified", exp=("10", "635 р. — к.", "Плоды"))),
                         ("RELABEL", 21, dict(like=22, session="unspecified", exp=("11", "714 р. 70 к.", "Доходное"))),
                         ("RELABEL", 22, dict(like=23, session="morning", exp=("12", "294 р. 49 к.", "Хрущевскіе"))),
                         ("RELABEL", 23, dict(like=23, session="evening", exp=("13", "1254 р. 35 к.", "Молодежь")))]),
    fix("1902-03_p018", [("RELABEL", 19, dict(like=20, session="morning", exp=("21", "164 р. 94 к.", "Таланты"))),
                         ("RELABEL", 20, dict(like=20, session="evening", exp=("22", "1352 р. 62 к.", "Воспитатель"))),
                         ("RELABEL", 21, dict(like=22, session="morning", exp=("22", "1015 р. 64 к.", "Дмитрій"))),
                         ("RELABEL", 22, dict(like=22, session="evening", exp=("26", "1974 р. 55 к.", "Миссъ"))),
                         ("RELABEL", 23, dict(like=24, session="morning", exp=("26", "476 р. 91 к.", "Зарница"))),
                         ("RELABEL", 24, dict(like=24, session="evening", exp=("27", "1336 р. 22 к.", "Снѣгурочка"))),
                         ("DELETE", 25, dict(exp=("27", "409 р. 86 к.", "Воспитатель")))]),   # duplicate of s047 (28 morning)
    fix("1905-06_p021", [("DELETE", 32, dict(exp=("26", None, None))),
                         ("RELABEL", 33, dict(like=32, session="unspecified", exp=("27", "442 р. 76 к.", "На всякаго"))),
                         ("RELABEL", 34, dict(like=34, session="unspecified", exp=("27", "723 р. 53 к.", "Буря")))]),
    # ---- exact duplicates of a neighbouring cell
    fix("1893-94_pair006", [("DELETE", 25, dict(exp=("16", "1023 р. 71 к.", "Сорванецъ")))]),
    fix("1893-94_pair010", [("DELETE", 36, dict(exp=("20", "484 р. 60 к.", "Мертвые")))]),
    fix("1897-98_pair010", [("DELETE", 28, dict(exp=("22", "3530 р. 40 к.", "Фра-Дьяволо")))]),
    # ---- French troupe's cell filed under Александринскій on its dash row; the Михайловскій cell was left empty
    fix("1892-93_pair012", [("THEATER", 79, dict(like=80, exp=("19", "879 р. 70 к.", "Celles"))),
                            ("DELETE", 80, dict(exp=("19", None, None))),
                            ("MERGE", 103, dict(drop=104, exp=("26", "1705 р. 50 к.", "Monsieur"), exp_drop=("26", None, None)))]),
    fix("1892-93_pair014", [("THEATER", 29, dict(like=30, exp=("9", "2077 р. 50 к.", "Bénéfice"))),
                            ("DELETE", 30, dict(exp=("9", None, None))),
                            ("THEATER", 65, dict(like=66, exp=("16", "1874 р. 50 к.", "Bénéfice"))),
                            ("DELETE", 66, dict(exp=("16", None, None)))]),
    # ---- one undivided printed cell stored as a morning + evening pair
    fix("1890-91_pair020", [("MERGE", 74, dict(drop=75, exp=("17", None, "Горе"), exp_drop=("17", None, "Святки")))]),
    fix("1891-92_pair016", [("MERGE_KEEP_SECOND", 98, dict(drop=97, exp=("9", None, "L'Article"), exp_drop=("9", None, None)))]),
    fix("1903-04_p017_b", [("MERGE_KEEP_SECOND", 3, dict(drop=2, exp=("7", "874 р. 11 к.", "Лѣсъ"), exp_drop=("7", None, None)))]),
    fix("1904-05_p022", [("MERGE", 32, dict(drop=33, exp=("9", "381 р. 40 к.", "L'acquitté"), exp_drop=("9", None, None)))]),
    # ---- printed halves stored as one session (works of both, the evening's figure): split into morning + evening
    fix("1900-01_p012", [("SPLIT", 28, dict(morning=["Плоды"], exp=("14", "1214 р. 02½ к.", "Плоды")))]),
    fix("1900-01_p016", [("SPLIT", 26, dict(morning=["Le Misanthrope"], exp=("6", "1022 р. 63 к.", "Le Misanthrope"))),
                         ("SPLIT", 14, dict(morning=["Биронъ"], exp=("6", "1607 р. 17 к.", "Биронъ")))]),
    fix("1900-01_p017", [("SPLIT", 23, dict(morning=["Другъ"], exp=("6", "938 р. 08 к.", "Другъ"))),
                         ("SPLIT", 12, dict(morning=["Жизнь"], exp=("6", "2493 р. 08 к.", "Жизнь")))]),
    fix("1900-01_p026", [("SPLIT", 30, dict(morning=["Le barbier"], morning_receipts="625 р. 50 к.", morning_annotation="Спектакль для учащейся молодежи.",
                                           exp=("4", "648 р. 85 к.", "Le barbier"))),
                         ("SPLIT", 33, dict(morning=["Le barbier"], exp=("7", "1451 р. 88 к.", "Le barbier")))]),
    fix("1902-03_p014", [("SPLIT", 36, dict(morning=["Les femmes"], exp=("6", "1271 р. 13 к.", "Les femmes")))]),
    fix("1902-03_p015", [("SPLIT", 22, dict(morning=["Виндзорскія"], exp=("6", "1174 р. 04 к.", "Виндзорскія")))]),
    fix("1903-04_p013", [("SPLIT", 12, dict(morning=["Бѣдность"], exp=("14", "776 р. 83 к.", "Сильные"))),
                         ("SPLIT", 22, dict(morning=["Трубадуръ"], exp=("14", "357 р. 27 к.", "Трубадуръ")))]),
]


def load(page):
    path = RAW / f"{page.replace('_b', '')}.raw.json"
    text = path.read_text(encoding="utf-8")
    d = json.loads(text)
    fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == text:
                    fmt = (ind, ea, tr)
    assert fmt, f"{page} does not round-trip"
    return path, d, fmt


def check(S, s, exp, what):
    x = S[s - 1]
    date_ok = (x.get("date_text") or "").strip().startswith(exp[0] + " ") or (x.get("date_text") or "").strip().split(" ")[0] == exp[0]
    assert date_ok, f"{what} s{s:03d}: date_text {x.get('date_text')!r} != {exp[0]}"
    if exp[1] is not None:
        assert x.get("receipts_text") == exp[1], f"{what} s{s:03d}: receipts {x.get('receipts_text')!r} != {exp[1]!r}"
    elif exp[1] is None and exp[2] is None:
        assert not x.get("works") and not x.get("receipts_text"), f"{what} s{s:03d} is not empty: {x.get('works')} {x.get('receipts_text')}"
    if exp[2]:
        t = (x.get("works") or [{}])[0].get("work_title") or ""
        assert t.startswith(exp[2]), f"{what} s{s:03d}: first title {t!r} !~ {exp[2]!r}"


def main():
    n_ops = n_pages = 0
    for page, ops in PLAN:
        path, d, fmt = load(page)
        S = d["sessions"]
        orig = list(S)                                  # original objects by position
        labels = {i + 1: (x.get("date_text"), x.get("theater")) for i, x in enumerate(orig)}
        dele, inserts = set(), {}
        for op, s, kw in ops:
            check(orig, s, kw["exp"], f"{page}:{op}")
            x = orig[s - 1]
            if op == "RELABEL":
                x["date_text"] = labels[kw["like"]][0]
                x["session"] = kw["session"]
                x["_fix_note"] = NOTE
            elif op == "DELETE":
                dele.add(s)
            elif op == "THEATER":
                x["theater"] = labels[kw["like"]][1]
                x["_fix_note"] = NOTE
            elif op in ("MERGE", "MERGE_KEEP_SECOND"):
                j = kw["drop"]
                check(orig, j, kw["exp_drop"], f"{page}:{op}:drop")
                y = orig[j - 1]
                if op == "MERGE":
                    ws = (x.get("works") or []) + (y.get("works") or [])
                    x["works"] = ws
                    x["receipts_text"] = x.get("receipts_text") or y.get("receipts_text")
                x["session"] = "unspecified"
                x["_fix_note"] = NOTE
                dele.add(j)
            elif op == "SPLIT":
                titles = [w.get("work_title") or "" for w in x.get("works") or []]
                mset = [w for w in x["works"] if any((w.get("work_title") or "").startswith(m) for m in kw["morning"])]
                eset = [w for w in x["works"] if w not in mset]
                assert mset and eset and len(mset) == len(kw["morning"]), f"{page} s{s:03d}: titles {titles} vs morning {kw['morning']}"
                m = copy.deepcopy(x)
                m["works"] = mset
                m["session"] = "morning"
                m["receipts_text"] = kw.get("morning_receipts")
                m["annotation"] = kw.get("morning_annotation")
                m["_fix_note"] = NOTE
                x["works"] = eset
                x["session"] = "evening"
                x["_fix_note"] = NOTE
                inserts[s] = m
            n_ops += 1
        out = []
        for i, x in enumerate(orig, 1):
            if i in dele:
                continue
            if i in inserts:
                out.append(inserts[i])
            out.append(x)
        d["sessions"] = out
        n_pages += 1
        print(f"{page}: {len(ops)} ops, sessions {len(S) if False else len(orig)} -> {len(out)}")
        if WRITE:
            path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
    print(f"{n_ops} operations on {n_pages} pages;", "WROTE" if WRITE else "DRY RUN (nothing written)")


if __name__ == "__main__":
    main()
