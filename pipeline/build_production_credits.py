"""Split the ballet productions lists' free-text creator credits into rows.

    raw.production_entry.description_text
      e.g. "Балетъ въ 4 д. и 6 карт., соч. Сенъ-Жоржа и М. И. Петипа, музыка Ц. Пуни."
    -> analysis.production_entry_credit, one row per (name, role) mention:
         Сенъ-Жоржа   | соч.    | author
         М. И. Петипа | соч.    | author
         Ц. Пуни      | музыка  | music

Analysis tier: pure parsing of the verbatim text, no new facts. Every
printed form stays exactly as printed (genitive/instrumental case endings,
pre-reform orthography, the print's own slips); normalising a name to the
nominative and linking it to a person belong in the entities layer
(issue #133). `role_category` is a coarse label derived from the printed
role words, which are kept verbatim in `role_text`.

role_category:
  author          соч., or a name printed with no role word ("Балетъ Нюитера ...")
  libretto        либретто / программа / сюжетъ <person> / составлен(а|ъ) <person>
  music           музыка
  instrumentation инструментована
  staging         постановка / поставленъ / танцы (и постановка) / танцы соч.
  source          the author of the work a ballet is based on
                  ("сюжетъ заимствованъ изъ сказки Перро", "на сюжетъ романа Сервантеса")

NB "сказки Перро" (Charles Perrault, source) and "соч. Ж. Перро" (Jules Perrot,
author) print the same surname -- role_category is what keeps them apart.

A handful of strings the rules can't read correctly are fixed in OVERRIDES
(keyed by the exact description_text), each with its reason.

Additive and safe to re-run: CREATE OR REPLACE on this one table only.

Usage:
    python pipeline/build_production_credits.py \
        --db outputs/full_run/imperial_theaters.duckdb [--csv out.csv] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb

UP = "А-ЯЁІѲѢѴ"
LO = "а-яёіѳѣѵъь"
WORD = rf"[{UP}][{LO}]+(?:[-'’][{UP}{LO}][{LO}]+)?"

# Role triggers, longest first. Each: (regex, role_category).
TRIGGERS = [
    (r"[Лл]ибретто \(сюжетъ заимствованъ\)", "libretto"),
    (r"(?<=[а-яъ])—(?=[А-Я])", "libretto"),   # "по роману Виктора Гюго—А. А. Горскимъ": librettist after the dash
    (r"сюжетъ и музыка", "libretto+music"),
    (r"соч\. и музыка", "author+music"),
    (r"[Тт]анцы и постановка", "staging"),
    (r"[Тт]анцы соч\.", "staging"),
    (r"(?:[Сс]южетъ|[Сс]одержаніе) (?:заимствован[ъо]|ваимствованъ|взятъ) изъ"
     r" (?:русской )?(?:сказ(?:ки|окъ)|поэмы|рыцарской легенды)", "source"),
    (r"на сюжетъ романа", "source"),
    (r"(?:либретто )?составлен(?:о|наго) по(?: роману)?", "source"),
    (r"составлена по нѣмецкимъ народнымъ сказкамъ и повѣрьямъ", "libretto"),
    (r"составленъ", "libretto"),
    (r"[Лл]ибретто(?: составлено)?", "libretto"),
    (r"[Пп]рограмма(?: составлена)?", "libretto"),
    (r"[Сс]южетъ", "libretto"),
    (r"инструментована", "instrumentation"),
    (r"(?:вновь )?(?:[Пп]оставленъ|Посгавленъ)(?: балетмейстер(?:омъ|ами))?", "staging"),
    (r"[Пп]остановка", "staging"),
    (r"[Мм]узыка(?: соч\.)?", "music"),
    (r"соч\.?,?", "author"),
]
TRIGGER_RE = re.compile("|".join(f"(?P<t{i}>{p})" for i, (p, _) in enumerate(TRIGGERS)))

HONORIFIC = r"(?:барона|князя|г-на|гг\.|г\.|лорда|Лорда)"
INITIAL = rf"(?:[{UP}][{LO}]{{0,3}}\.|[{UP}](?= [{UP}]))"  # "М.", "Мод.", "Альб.", or bare "И" in "М. И Петипа"
# Not names: capitalised genre/structure words and words inside «...».
STOP = {"Балетъ", "Большой", "Сюжетъ", "Содержаніе", "Программа", "Музыка", "Танцы",
        "Поставленъ", "Посгавленъ", "Постановка", "Либретто", "Мимодрама", "Прологъ",
        "Волшебная", "Волшебный", "Фантастическій", "Комическій", "Характерный",
        "Пантомимный", "Миѳологическій", "Аллегорическій", "Анакреонтическій",
        "Хореографическая", "Деми-характерный", "Балетъ-феерія", "Балетъ-дивертиссементъ",
        "Балетъ-фантазія"}
NAME_RE = re.compile(
    rf"(?P<hon>{HONORIFIC} )?"
    rf"(?P<name>⁂|Г⁂|(?:{INITIAL} ?)*(?:{WORD})(?: (?:{WORD}))?|(?:{INITIAL} ?)+(?=[,и ]))"
    rf"(?P<suffix> \(отца\))?"
)
COLLECTIVE_RE = re.compile(r"(?:и )(?P<name>др\.|друг\.)|(?P<name2>разныхъ авторовъ)")

OVERRIDES: dict[str, list[tuple[str, str, str, str]]] = {
    # (name_printed, role_text, role_category, note) in printed order
    "Балетъ въ 5 д. и 10 карт., соч. К. В. и А. Н. Богданова, музыка Мюльендорфера и Шимана.": [
        ("К. В.", "соч.", "author", "initials only; may share the surname Богданова with the next name, or be a separate person (cf. 'программа К. В.' elsewhere)"),
        ("А. Н. Богданова", "соч.", "author", ""),
        ("Мюльендорфера", "музыка", "music", ""),
        ("Шимана", "музыка", "music", "")],
}


def strip_noise(text: str, stop_words: bool = True) -> str:
    """Blank out spans that never contain creator names, keeping offsets."""
    def blank(m):
        return " " * len(m.group(0))
    t = re.sub(r"^\([^)]*\)\.?", blank, text)          # leading subtitle / scope note
    t = re.sub(r"«[^»]*»", blank, t)                    # quoted titles
    t = re.sub(r"\((?:\d|1-е)[^)]*\)", blank, t)        # trailing scope note "(1-е д.)"
    for w in sorted(STOP, key=len, reverse=True) if stop_words else []:  # never names
        t = re.sub(rf"(?<![\w-]){re.escape(w)}(?![\w-])", blank, t)
    return t


def parse(desc: str) -> list[dict]:
    if desc in OVERRIDES:
        return [dict(name_printed=n, role_text=rt, role_category=rc, honorific_printed=None,
                     qualifier_printed=None, is_pseudonym="⁂" in n, is_collective=False, note=note or None)
                for n, rt, rc, note in OVERRIDES[desc]]
    # role words are found before blanking the stop words (several are capitalised:
    # "Сюжетъ", "Поставленъ"); names are found after, so "Балетъ Нюитера" isn't one name
    triggers = [(m.start(), m.end(), m.group(0), TRIGGERS[int(m.lastgroup[1:])][1])
                for m in TRIGGER_RE.finditer(strip_noise(desc, stop_words=False))]
    t = strip_noise(desc)
    hits = []  # (start, end, name, honorific, is_collective)
    for m in NAME_RE.finditer(t):
        if any(s <= m.start() < e for s, e, _, _ in triggers):
            continue  # inside a trigger phrase
        hits.append((m.start(), m.end(), m.group("name") + (m.group("suffix") or ""),
                     (m.group("hon") or "").strip() or None, False))
    for m in COLLECTIVE_RE.finditer(t):
        s = m.start("name") if m.group("name") else m.start("name2")
        hits.append((s, m.end(), m.group("name") or m.group("name2"), None, True))
    hits.sort()
    out = []
    prev_end = 0
    for s, e, nm, hon, coll in hits:
        before = [tr for tr in triggers if tr[1] <= s]
        if before:
            ts, te, rt, rc = before[-1]
            # qualifier: printed words between the trigger (or the previous name of the
            # same trigger) and this name, from the ORIGINAL text so «...» survives
            gap = desc[max(te, prev_end):s].strip()
            if gap != "и.":  # keep the printed initial "и." (below); otherwise drop a leading "и"/punctuation
                gap = re.sub(r"^[\s,.;]*(?:и\b)?[\s,.;]*", "", gap).strip()
            gap = re.sub(r"(?:,|\s—)$", "", gap).strip()
        else:
            rt, rc, gap = None, "author", ""
        if rt == "—":
            rt = "либретто составлено по роману … —"
        note = None
        if gap == "и.":  # "сюжетъ и. Асрейтера": printed lower-case initial (RG 2026-09-28: a slip for И.)
            nm, gap, note = "и. " + nm, "", "lower-case 'и.' printed as the initial; RG read it as a slip for И. (#101)"
        gap = gap.strip(" ,;") or None
        if gap and re.fullmatch(r"[).(]*", gap):
            gap = None
        for cat in rc.split("+"):
            out.append(dict(name_printed=nm, honorific_printed=hon, qualifier_printed=gap,
                            role_text=rt, role_category=cat, is_pseudonym="⁂" in nm,
                            is_collective=coll, note=note))
        prev_end = e
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    con = duckdb.connect(str(args.db), read_only=args.dry_run)
    entries = con.execute("""SELECT production_entry_id, description_text FROM raw.production_entry
                             ORDER BY production_entry_id""").fetchall()
    rows = []
    for pe_id, desc in entries:
        for i, r in enumerate(parse(desc or ""), 1):
            rows.append(dict(credit_id=f"{pe_id}__c{i:02d}", production_entry_id=pe_id, credit_order=i, **r))
    import pandas as pd
    df = pd.DataFrame(rows, columns=["credit_id", "production_entry_id", "credit_order", "name_printed",
                                     "honorific_printed", "qualifier_printed", "role_text", "role_category",
                                     "is_pseudonym", "is_collective", "note"])
    if args.csv:
        df.to_csv(args.csv, index=False)
    print(f"{len(entries)} entries -> {len(df)} credit rows; "
          f"{df.production_entry_id.nunique()} entries with >=1 credit")
    print(df.role_category.value_counts().to_string())
    if not args.dry_run:
        con.execute("CREATE SCHEMA IF NOT EXISTS analysis")
        con.register("credits_df", df)
        con.execute("""
            CREATE OR REPLACE TABLE analysis.production_entry_credit (
                credit_id VARCHAR PRIMARY KEY,
                production_entry_id VARCHAR NOT NULL,
                credit_order INTEGER NOT NULL,
                name_printed VARCHAR NOT NULL,
                honorific_printed VARCHAR,
                qualifier_printed VARCHAR,
                role_text VARCHAR,
                role_category VARCHAR NOT NULL,
                is_pseudonym BOOLEAN NOT NULL,
                is_collective BOOLEAN NOT NULL,
                note VARCHAR)""")
        con.execute("INSERT INTO analysis.production_entry_credit SELECT * FROM credits_df")
        print("wrote analysis.production_entry_credit")
    con.close()


if __name__ == "__main__":
    main()
