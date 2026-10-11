"""Stage B of the column-structure read (issue #151 follow-up 15): printed half-performances that the stored data lacks.

    uv run python docs/eval/title_check_2026-10-10/align/apply_dropped_halves.py            # dry run
    uv run python docs/eval/title_check_2026-10-10/align/apply_dropped_halves.py --write

Every inserted session has at least two agreeing blind reads of the printed cell (align/reports_detail; the high-resolution
re-reads detail_26..28 for the cells that had one), and the figures and titles below are those readings. Where the stored
session already held the other half, it gets the slot (morning/evening) the print gives it. Before-states are asserted.
Two cases are not a plain "missing half":
  1899-00 p014 АЛЕК 27/28: 28's morning «Шутники» 445 р. 10 к. had been given to 27's «Женитьба Бѣлугина» (printed with no figure)
  1900-01 p010 АЛЕК 5: the stored session had the jubilee repeat's figure (274 р. 34 к.) with «Накипь»; «Накипь» is the evening, 1632 р. 96 к.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[4] / "outputs" / "full_run" / "raw"
WRITE = "--write" in sys.argv
NOTE = "half-performance read from the scan 2026-10-11 (column-structure read, issue #151 follow-up 15, Stage B)"
P = "repertoire_"


def W(title, genre):
    return {"work_title": title, "genre": genre}


# kind: 'after_evening' = stored s is the morning half, a new evening session follows it
#       'before_morning' = stored s is the evening half, a new morning session precedes it
#       'custom' handled by name
PLAN = [
    ("1899-00_p014", "custom_p014_1899"),
    ("1899-00_p024", ("after_evening", 34, "508 р. 65 к.", "Недоросль", [W("Накипь", "ком.")], "1650 р. 89 к.")),
    ("1900-01_p016", ("after_evening", 30, "627 р. — к.", "Andromaque", [W("Madame Lili", "com."), W("Le verre d'eau", "com.")], "534 р. 50 к.")),
    ("1900-01_p018", ("after_evening", 34, "613 р. — к.", "Комикъ", [W("Les brebis de Panurge", "com."), W("La mégère apprivoisée", "com.")], "302 р. 50 к.")),
    ("1901-02_p020", ("after_evening", 15, "1621 р. 83 к.", "Сонъ", [W("Комета", "эпизодъ")], "2018 р. 98 к.")),
    ("1901-02_p021", ("after_evening", 15, "636 р. 31 к.", "Лѣсъ", [W("Нефтяной фонтанъ", "ком.")], "1531 р. 83 к.")),
    ("1903-04_p006", ("after_evening", 33, "789 р. 55 к.", "Венеціанскій", [W("Пустоцвѣтъ", "ком.")], "1716 р. 64 к.")),
    ("1903-04_p018", ("after_evening", 24, "930 р. 14 к.", "Снѣгурочка", [W("Плоды просвѣщенія", "ком.")], "1806 р. 32 к.")),
    ("1898-99_p019", ("after_evening", 26, "389 р. 46 к.", "Севильскій", [W("Риголетто", "оп.")], "1414 р. 39 к.")),
    ("1893-94_pair018", ("after_evening", 7, "273 р. 88 к.", "Плоды", [W("Общество поощренія скуки", "ком.")], None)),
    ("1900-01_p027", ("before_morning", 35, "1146 р. 36 к.", "Каширская", [W("Снѣгурочка", "весенняя сказка")], "715 р. 70 к.")),
    ("1900-01_p022", "custom_p022"),
    ("1900-01_p017", "custom_p017"),
    ("1900-01_p008", "custom_p008"),
    ("1900-01_p010", "custom_p010"),
    ("1898-99_p014", "custom_p014_1898"),
    ("1897-98_pair022", "custom_pair022"),
]


def load(page):
    path = RAW / f"{P}{page}.raw.json"
    t = path.read_text(encoding="utf-8")
    d = json.loads(t)
    fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, f"{page} does not round-trip"
    return path, d, fmt


def first(s):
    ws = s.get("works") or []
    return ws[0]["work_title"] if ws else ""


def expect(S, i, receipts, title_prefix, what):
    x = S[i - 1]
    assert x.get("receipts_text") == receipts, f"{what} s{i:03d}: receipts {x.get('receipts_text')!r} != {receipts!r}"
    if title_prefix is not None:
        assert first(x).startswith(title_prefix), f"{what} s{i:03d}: title {first(x)!r} !~ {title_prefix!r}"


def new_like(base, session, works, receipts, annotation=None, date_text=None):
    n = copy.deepcopy(base)
    n["session"] = session
    n["works"] = works
    n["receipts_text"] = receipts
    n["annotation"] = annotation
    n["is_dark"] = False
    if date_text:
        n["date_text"] = date_text
    n["_source"] = None
    n["_fix_note"] = NOTE
    return n


def main():
    n_new = 0
    for page, spec in PLAN:
        path, d, fmt = load(page)
        S = d["sessions"]
        orig = list(S)
        ins_before, ins_after = {}, {}
        if isinstance(spec, tuple):
            kind, s_hint, rc, tp, works, fig = spec
            hits = [i for i, y in enumerate(orig, 1) if y.get("receipts_text") == rc and first(y).startswith(tp)]
            assert len(hits) == 1, f"{page}: {len(hits)} sessions with {rc!r} / {tp!r}"
            s = hits[0]            # located by figure + first title (earlier fixes may have moved the session number)
            expect(orig, s, rc, tp, page)
            x = orig[s - 1]
            if kind == "after_evening":
                x["session"] = "morning"
                x["_fix_note"] = NOTE
                ins_after[s] = new_like(x, "evening", works, fig, None)
            else:
                x["session"] = "evening"
                x["_fix_note"] = NOTE
                ins_before[s] = new_like(x, "morning", works, fig, None)
        elif spec == "custom_p014_1899":
            expect(orig, 16, "445 р. 10 к.", "Женитьба", page)          # 27 Суббота: the figure belongs to 28's morning
            expect(orig, 17, "1483 р. 25 к.", "Биронъ", page)
            orig[15]["receipts_text"] = None
            orig[15]["_fix_note"] = NOTE
            orig[16]["session"] = "evening"
            orig[16]["_fix_note"] = NOTE
            ins_before[17] = new_like(orig[16], "morning", [W("Шутники", "ком.")], "445 р. 10 к.", None)
        elif spec == "custom_p022":
            expect(orig, 3, "1643 р. 92 к.", "Царь", page)               # 14 Воскрес.: morning Царь Борисъ (no figure), evening Выгодное предпріятіе
            x = orig[2]
            x["session"] = "morning"
            x["receipts_text"] = None
            x["_fix_note"] = NOTE
            ins_after[3] = new_like(x, "evening", [W("Выгодное предпріятіе", "ком.")], "1643 р. 92 к.", None)
        elif spec == "custom_p017":
            expect(orig, 1, "1166 р. 13 к.", "Ромео", page)              # 6: morning Ромео и Джульетта (no figure), evening Кинъ 1166 р. 13 к.
            x = orig[0]
            x["session"] = "morning"
            x["receipts_text"] = None
            x["_fix_note"] = NOTE
            ins_after[1] = new_like(x, "evening", [W("Кинъ", "ком.")], "1166 р. 13 к.", None)
        elif spec == "custom_p008":
            expect(orig, 31, "666 р. 63 к.", "Les deux", page)            # 29: morning = the Siamese court troupe (no works, no figure)
            x = orig[30]
            assert x.get("annotation") == "Представленіе Сіамской Придворной труппы."
            ann = x["annotation"]
            x["annotation"] = None
            x["session"] = "evening"
            x["_fix_note"] = NOTE
            ins_before[31] = new_like(x, "morning", [], None, ann)
        elif spec == "custom_p010":
            expect(orig, 15, "274 р. 34 к.", "Накипь", page)             # 5 Nov: morning = jubilee repeat 274 р. 34 к.; evening Накипь 1632 р. 96 к.
            x = orig[14]
            ann = x["annotation"]
            assert ann == "Повтореніе юбилейнаго спектакля въ память П. С. Мочалова."
            x["annotation"] = None
            x["receipts_text"] = "1632 р. 96 к."
            x["session"] = "evening"
            x["_fix_note"] = NOTE
            ins_before[15] = new_like(x, "morning", [], "274 р. 34 к.", ann)
        elif spec == "custom_p014_1898":
            expect(orig, 15, "853 р. 30 к.", "Джентльмэнъ", page)        # 29: morning Джентльмэнъ; evening = what was stored under 30
            expect(orig, 18, "1438 р. 71 к.", "Наталья", page)
            assert orig[17]["date_text"].startswith("30 ")
            orig[14]["session"] = "morning"
            orig[14]["_fix_note"] = NOTE
            orig[17]["date_text"] = orig[14]["date_text"]
            orig[17]["session"] = "evening"
            orig[17]["_fix_note"] = NOTE
            ins_after[18] = new_like(orig[17], "unspecified", [W("Борцы", "ком.")], "1647 р. — к.", None, date_text="30 Понед.")
        elif spec == "custom_pair022":
            x17, x19 = orig[16], orig[18]
            assert (x17.get("annotation") or "").startswith("Vorstellung zu wohl") and first(x17).startswith("Tristan")
            assert x19.get("receipts_text") == "5785 р. 10 к." and first(x19).startswith("A basso")
            ann = ("Vorstellung zu wohlthätigen Zwecken.\n2-ter Akt (1-es Bild) aus der Oper Fidelio.\n"
                   "Vorspiel und Charfreitagszauber aus der Oper Parsifal.\nScenen aus der Op. Die lustigen Weiber von Windsor.\nConcert-Abtheilung.")
            x17["annotation"] = None
            x17["_fix_note"] = NOTE
            x19["session"] = "evening"
            x19["_fix_note"] = NOTE
            ins_before[19] = new_like(x19, "morning", [], None, ann)
        else:
            raise SystemExit(f"unknown spec {spec}")
        out = []
        for i, x in enumerate(orig, 1):
            if i in ins_before:
                out.append(ins_before[i]); n_new += 1
            out.append(x)
            if i in ins_after:
                out.append(ins_after[i]); n_new += 1
        d["sessions"] = out
        print(f"{page}: sessions {len(orig)} -> {len(out)}")
        if WRITE:
            path.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
    print(f"{n_new} sessions inserted;", "WROTE" if WRITE else "DRY RUN (nothing written)")


if __name__ == "__main__":
    main()
