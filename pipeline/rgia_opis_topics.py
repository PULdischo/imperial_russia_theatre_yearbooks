"""Tag оп. 18's дела by topic, from RGIA's own authoritative titles.

Dates turned out to be a weak instrument for this опись: RGIA publishes them
for only 37% of дела, and scan-derived dates score 60.6% exact / 29% wrong
against RGIA's own (see rgia_dates_merge.py). Titles, by contrast, are
complete and authoritative for all 1142. So topic is the primary filter here
and date is a secondary hint -- not the other way round.

Tags are deliberately broad and overlapping: the cost of an extra candidate
is one glance, the cost of a missed дело is a hole in the research.

Usage:
    python pipeline/rgia_opis_topics.py
"""
from __future__ import annotations

import argparse, csv, re
from collections import Counter
from pathlib import Path

TOPICS: dict[str, str] = {
    "ежегодник":        r"ежегодник",
    "личный состав":    r"личн\w*\s+состав|списки?\s+(артист|служащ|хорист|портн|музыкант|танцов|фигурант|разборщ)|требовательн\w*\s+ведомост|на выдачу (жалованья|содержания)|послужн",
    "репертуар":        r"репертуар|ведомост\w*\s+поставленных|реестр\w*\s+пьес|поставленн\w*\s+пьес",
    "бенефис":          r"бенефис",
    "сборы/касса":      r"сбор\w*\s+(со|с)\s+спектакл|касс[аыу]|поспектакльн|абонемент|продаж\w*\s+билет",
    "цензура/ТЛК":      r"цензур|театральн\w*-?\s*литературн\w*\s+комитет|рассмотрени\w*\s+пьес|допуск\w*\s+к\s+представлен",
    "постановка":       r"постановк|монтировк|декорац|бутафор|костюм|реквизит",
    "училище":          r"училищ|воспитанник|стипенди",
    "здания":           r"здани|постройк|ремонт|перестройк|архитектор",
    "контракты":        r"контракт|ангажемент|условие с|договор",
    "труппы":           r"(русск\w*|французск\w*|немецк\w*|итальянск\w*|балетн\w*|оперн\w*|драматическ\w*)\s+труппы?",
}
PEOPLE = {
    "Всеволожский": r"всеволожск", "Теляковский": r"теляковск",
    "Погожев": r"погожев", "Гершельман": r"гершельман",
    "Дризен": r"дринзен|дризен", "Чайковский": r"чайковск",
    "Петипа": r"петипа", "Дягилев": r"дягилев",
    "Направник": r"направник", "Немирович-Данченко": r"немирович",
}
THEATRES = {
    "Александринский": r"александринск", "Мариинский": r"мариинск",
    "Михайловский": r"михайловск", "Эрмитажный": r"эрмитажн",
    "Большой": r"большого театра|большой театр", "Красносельский": r"красносельск",
}


def tag(title: str, table: dict[str, str]) -> list[str]:
    return [k for k, pat in table.items() if re.search(pat, title, re.I)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path,
                    default=Path("outputs/rgia_catalogue/opis18_dela_filled.csv"))
    ap.add_argument("--out", type=Path,
                    default=Path("outputs/rgia_catalogue/opis18_tagged.csv"))
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.src, encoding="utf-8")))
    for r in rows:
        t = r["title_ru"]
        r["topics"] = "; ".join(tag(t, TOPICS))
        r["people"] = "; ".join(tag(t, PEOPLE))
        r["theatres"] = "; ".join(tag(t, THEATRES))

    cols = list(rows[0].keys())
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    def report(name, table, field):
        c = Counter()
        for r in rows:
            for k in (r[field].split("; ") if r[field] else []): c[k] += 1
        print(f"\n{name}:")
        for k, n in c.most_common():
            excl = sum(1 for r in rows if k in (r[field].split("; ") if r[field] else [])
                       and r["in_research_range"] == "no")
            print(f"   {k:<18} {n:>4}   ({excl} ruled out by RGIA's own dates)")

    print(f"{len(rows)} дела tagged -> {args.out}")
    report("topics", TOPICS, "topics")
    report("people named in titles", PEOPLE, "people")
    report("theatres named in titles", THEATRES, "theatres")
    untagged = [r for r in rows if not r["topics"]]
    print(f"\nno topic matched: {len(untagged)} ({100*len(untagged)/len(rows):.0f}%)")


if __name__ == "__main__":
    main()
