"""Three date-shift cascades found by the false-split sizing (issue #151 follow-up 13). Each was read on the scan by me at full
resolution (2026-10-11); the stored column was one slot off its dates after a spurious extra half-slot.

    uv run python docs/eval/title_check_2026-10-10/fix_shift_cascades.py            # dry run
    uv run python docs/eval/title_check_2026-10-10/fix_shift_cascades.py --write

  repertoire_1899-00_p012, Михайловскій, 14-21 Nov 1899. s015 «15 Понед.» is a duplicate of the 14th's evening cell (same works,
      1268 р. 10 к.) and is deleted. s016-s020 carried the previous day's cell under the next day's label (Забава/Фрицинька
      605 р. is printed on 15 Понед.); s021 «21 morning» is the 20 Суббота cell (Bénéfice de M-r Brouette, 2026 р. 50 к.); s022
      is the 21st (600 р. 50 к.), one undivided cell. Labels are corrected to the row each cell is printed on.
  repertoire_1899-00_p018, Александринскій, 18-29 Dec 1899. The 18 Суббота cell prints only the banner «Спектакль въ память
      Вольфганга Гёте.» (no works, no figure) and was given two slots; from s019 every cell sat one slot early. The 14 sessions
      s018-s031 are relabelled to the 14 print sub-cells (18; 19 утро/вечеръ; 20; 21; 22; 26-29 each утро/вечеръ).
  repertoire_1891-92_pair012, Александринскій, 18 Среда (Dec 1891). The cell prints «Плоды просвѣщенія» only. s042 «18 evening»
      [Рабочая слободка, Ворона въ павлиньихъ перьяхъ] duplicates 19 Четвергъ's cell (s048) and is deleted; s043 is `unspecified`.
Later session ids shift down by one on p012 and pair012 (one deletion each); p018 keeps its ids.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[3] / "outputs" / "full_run" / "raw"
NOTE = "date/slot label corrected from the scan 2026-10-11 (date-shift cascade, issue #151 follow-up 13)"
WRITE = "--write" in sys.argv


def load(page):
    p = RAW / f"{page}.raw.json"
    t = p.read_text(encoding="utf-8")
    d = json.loads(t)
    fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    fmt = (ind, ea, tr)
    assert fmt, f"{page} does not round-trip"
    return p, d, fmt


def label(S, i):
    return S[i - 1]["date_text"]


def expect(S, i, date_text, receipts, first_title, theater):
    s = S[i - 1]
    got = (s["date_text"], s["receipts_text"], (s["works"][0]["work_title"] if s.get("works") else None), s["theater"])
    want = (date_text, receipts, first_title, theater)
    assert got == want, f"s{i:03d}: {got} != {want}"


def save(p, d, fmt):
    if WRITE:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")


def relabel(S, i, date_text, session):
    s = S[i - 1]
    s["date_text"], s["session"] = date_text, session
    s["_fix_note"] = NOTE


def p012():
    p, d, fmt = load("repertoire_1899-00_p012")
    S = d["sessions"]
    M = "Михайловскій театръ."
    # before-state: Михайловскій s014..s024, each against what the scan prints
    expect(S, 14, "14 Воскрес.", "1268 р. 10 к.", "Le Train de plaisir", M)
    expect(S, 15, "15 Понед.", "1268 р. 10 к.", "Le Train de plaisir", M)          # duplicate
    expect(S, 16, "16 Вторникъ.", "605 р. — к.", "Забава", M)                       # printed on 15
    expect(S, 17, "17 Среда.", "1453 р. 82¹/₂ к.", "Fromont jeune et Risler aîné", M)  # 16
    expect(S, 18, "18 Четвергъ.", "450 р. 50 к.", "Гибель Содома", M)               # 17
    expect(S, 19, "19 Пятница", "1272 р. 95 к.", "Fromont jeune et Risler aîné", M)  # 18
    expect(S, 20, "20 Суббота.", "358 р. 50 к.", "Бой бабочекъ", M)                 # 19
    expect(S, 21, "21 Воскрес.", "2026 р. 50 к.", "L'Ami Fritz", M)                 # 20
    expect(S, 22, "21 Воскрес.", "600 р. 50 к.", "L'Ami Fritz", M)                  # 21
    assert S[20]["session"] == "morning" and S[21]["session"] == "evening"
    rows = {15: label(S, 3), 16: label(S, 4), 17: label(S, 5), 18: label(S, 6), 19: label(S, 7), 20: label(S, 8), 21: label(S, 9)}
    assert rows == {15: "15 Понед.", 16: "16 Вторникъ.", 17: "17 Среда.", 18: "18 Четвергъ.", 19: "19 Пятница", 20: "20 Суббота.", 21: "21 Воскрес."}, rows
    # relabel (original indices), then delete the duplicate
    relabel(S, 16, rows[15], "unspecified")
    relabel(S, 17, rows[16], "unspecified")
    relabel(S, 18, rows[17], "unspecified")
    relabel(S, 19, rows[18], "unspecified")
    relabel(S, 20, rows[19], "unspecified")
    relabel(S, 21, rows[20], "unspecified")
    relabel(S, 22, rows[21], "unspecified")
    del S[14]
    print("p012: 1 session deleted, 7 relabelled ->", len(S), "sessions")
    save(p, d, fmt)


def p018():
    p, d, fmt = load("repertoire_1899-00_p018")
    S = d["sessions"]
    A = "Александринскій театръ."
    expect(S, 18, "18 Суббота.", None, None, A)
    expect(S, 19, "18 Суббота.", "318 р. 04 к.", "Недоросль", A)
    expect(S, 20, "19 Воскрес.", "1475 р. — к.", "Свѣтить, да не грѣть", A)
    expect(S, 21, "19 Воскрес.", "1645 р. 55 к.", "Накипь", A)
    expect(S, 22, "20 Понед.", "1368 р. 67 к.", "Идіотъ", A)
    expect(S, 23, "21 Вторн.", "1068 р. 82 к.", "Выгодное предпріятіе", A)
    expect(S, 24, "22 Среда.", "605 р. 37 к.", "Биронъ", A)
    expect(S, 25, "26 Воскрес.", "1651 р. 52 к.", "Борцы", A)
    expect(S, 26, "26 Воскрес.", "798 р. 49 к.", "Идіотъ", A)
    expect(S, 27, "27 Понед.", "1650 р. 20 к.", "Вторая молодость", A)
    expect(S, 28, "27 Понед.", "436 р. 46 к.", "Горе отъ ума", A)
    expect(S, 29, "28 Вторн.", "1636 р. 36 к.", "Закатъ", A)
    expect(S, 30, "28 Вторн.", "579 р. 02 к.", "Вторая молодость", A)
    expect(S, 31, "29 Среда.", "1653 р. 90 к.", "Накипь", A)
    L = {d_: label(S, i) for d_, i in (("18", 3), ("19", 4), ("20", 6), ("21", 7), ("22", 8), ("26", 9), ("27", 11), ("28", 13), ("29", 15))}
    assert L == {"18": "18 Суббота.", "19": "19 Воскрес.", "20": "20 Понед.", "21": "21 Вторн.", "22": "22 Среда.",
                 "26": "26 Воскрес.", "27": "27 Понед.", "28": "28 Вторн.", "29": "29 Среда."}, L
    plan = [(18, L["18"], "unspecified"), (19, L["19"], "morning"), (20, L["19"], "evening"), (21, L["20"], "unspecified"),
            (22, L["21"], "unspecified"), (23, L["22"], "unspecified"), (24, L["26"], "morning"), (25, L["26"], "evening"),
            (26, L["27"], "morning"), (27, L["27"], "evening"), (28, L["28"], "morning"), (29, L["28"], "evening"),
            (30, L["29"], "morning"), (31, L["29"], "evening")]
    for i, dt, ses in plan:
        relabel(S, i, dt, ses)
    print("p018: 14 relabelled ->", len(S), "sessions")
    save(p, d, fmt)


def pair012():
    p, d, fmt = load("repertoire_1891-92_pair012")
    S = d["sessions"]
    A = "Александринскій."
    assert S[41]["date_text"] == "18 Среда." and S[41]["session"] == "evening" and S[41]["theater"] == A
    assert [w["work_title"] for w in S[41]["works"]] == ["Рабочая слободка", "Ворона въ павлиньихъ перьяхъ"]
    assert S[47]["date_text"] == "19 Четвергъ" and [w["work_title"] for w in S[47]["works"]] == ["Рабочая слободка", "Ворона въ павлиньихъ перьяхъ"]
    assert S[42]["date_text"] == "18 Среда." and S[42]["session"] == "morning" and [w["work_title"] for w in S[42]["works"]] == ["Плоды просвѣщенія"]
    S[42]["session"] = "unspecified"
    S[42]["_fix_note"] = NOTE
    del S[41]
    print("pair012: 1 session deleted, 1 relabelled ->", len(S), "sessions")
    save(p, d, fmt)


if __name__ == "__main__":
    p012(); p018(); pair012()
    print("WROTE" if WRITE else "DRY RUN (nothing written)")
