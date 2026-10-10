"""Second pass after apply_fixes.py (issue #150): bring the credit ROWS (label / role_name) into line with the
corrected summary text, for the 23 rows apply_fixes' word-level updates could not reach (the row held a hyphenated
or garbled form of a word, or the entry's whole text was replaced, or its text had been empty), plus two words of
the p006 readings that only ONE reader saw and that look like worn type.

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/sync_rows.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/sync_rows.py --write

Every new row value must occur in its entry's (corrected) summary text; otherwise nothing is written.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402

RAW = HERE.parent.parent.parent / "outputs" / "full_run" / "raw"
E = "balletartists_"
#: (entry_id, field, old) -> new
ROW_MAP = {
    (E + "1894-95_SP_p005__e022", "role_name", "nota-piycъ"): "нотаріусъ",
    (E + "1895-96_MSK_p005__e018", "role_name", "nota-prius"): "нотаріусъ",
    (E + "1897-98_MSK_p005__e024", "role_name", "nota-priusъ"): "нотаріусъ",
    (E + "1906-07_SP_p009__e013", "role_name", "nota-piycъ"): "нотаріусъ",
    (E + "1896-97_SP_p005__e019", "label", "Младa"): "Млада",
    (E + "1896-97_SP_p006__e018", "label", "Младa"): "Млада",
    (E + "1897-98_SP_p007__e011", "label", "Младa"): "Млада",
    (E + "1898-99_SP_p007__e012", "label", "Младa"): "Млада",
    (E + "1897-98_MSK_p004__e018", "label", "Пéri"): "Пери",
    (E + "1897-98_MSK_p004__e019", "label", "Пéri"): "Пери",
    (E + "1905-06_SP_p007__e001", "label", "операхъ"): "оперѣ",
    (E + "1907-08_SP_p005__e006", "label", "операхъ"): "оперѣ",
    (E + "1906-07_MSK_p008__e004", "role_name", "оберъ-гофмаршаль"): "оберъ-гофмаршалъ",
    (E + "1906-07_MSK_p008__e004", "role_name", "Аммонa-Ra"): "Аммона-Ра",
    (E + "1908-09_SP_p006__e005", "role_name", "кшатій"): "кшатрій",
    (E + "1908-09_SP_p006__e007", "role_name", "Вазиль"): "Базиль",
    (E + "1908-09_SP_p006__e007", "role_name", "Жанъ-де Бріень"): "Жанъ-де Бріенъ",
    (E + "1908-09_SP_p006__e007", "role_name", "графъ Альберть"): "графъ Альбертъ",
    (E + "1908-09_SP_p006__e007", "role_name", "Шгесь"): "Шгесъ",
    (E + "1908-09_SP_p006__e009", "label", "Фея куколь"): "Фея куколъ",
    (E + "1908-09_SP_p006__e013", "label", "балетѣ"): "балетъ",
    (E + "1908-09_SP_p006__e016", "role_name", "кавалеръ изъ свиты де-Бріень"): "кавалеръ изъ свиты де-Бріенъ",
    (E + "1908-09_SP_p006__e017", "role_name", "Гансь"): "Гансъ",
    (E + "1908-09_SP_p006__e020", "label", "балетѣ"): "балетъ",
    # round 3: the row for «въ 4 дивертиссментахъ—4» had been labelled «драмѣ»
    (E + "1907-08_MSK_p006__e024", "label", "драмѣ"): "дивертиссментахъ",
}
#: Text edits: a single reader saw worn type; the intended letter is kept (project convention).
TEXT_MAP = {
    (E + "1908-09_SP_p006__e005", "кшатвій"): "кшатрій",
    (E + "1908-09_SP_p006__e016", "цридворный"): "придворный",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    by_page = {}
    for (eid, f, old), new in ROW_MAP.items():
        by_page.setdefault(eid.split("__e")[0], set()).add(eid)
    for (eid, old) in TEXT_MAP:
        by_page.setdefault(eid.split("__e")[0], set()).add(eid)
    changed, problems = 0, []
    norm = lambda s: re.sub(r"\s+", " ", (s or "").replace("-", "")).strip()
    for page, eids in sorted(by_page.items()):
        path = RAW / f"{page}.raw.json"
        doc = rp.loads(path.read_text(encoding="utf-8"))
        entries = doc.get("entries")
        for eid in sorted(eids):
            e = entries[int(eid.split("__e")[1]) - 1]
            text = e.get("credit_summary_text") or ""
            for (e2, old), new in TEXT_MAP.items():
                if e2 == eid and old in text:
                    text = text.replace(old, new)
                    e.set("credit_summary_text", text); changed += 1
            for (e2, f, old), new in ROW_MAP.items():
                if e2 != eid:
                    continue
                rows = [r for r in e.get("credits") or [] if r.get(f) == old]
                if len(rows) < 1:
                    if any(r.get(f) == new for r in e.get("credits") or []):
                        continue                      # already synced
                    problems.append((eid, f, old, "row not found and the new value is not there either")); continue
                if norm(new) not in norm(text):
                    problems.append((eid, f, old, f"new value {new!r} not in the summary text")); continue
                for r in rows:
                    r.set(f, new); changed += 1
        if args.write:
            path.write_text(rp.dumps(doc), encoding="utf-8")
    print(("WROTE " if args.write else "DRY RUN "), changed, "edits on", len(by_page), "pages")
    for p in problems:
        print("  PROBLEM", p)
    return 1 if (problems and args.write) else 0


if __name__ == "__main__":
    sys.exit(main())
