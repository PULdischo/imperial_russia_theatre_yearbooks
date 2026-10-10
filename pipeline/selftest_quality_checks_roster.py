"""Self-test for the two Roster checks in quality_checks.py (issue #149, 2026-10-10):
`duplicate_person_on_page` and the credit-sum checks. Synthetic rows only, no database or scans,
so it runs anywhere:

    uv run python pipeline/selftest_quality_checks_roster.py

Exits non-zero if any case fails. The cases are the real shapes behind the rules: the four genuine
bugs of issue #124 (a continuation note split into its own row), the legitimate double listings that
made up 179 of its 183 flags, Исаева printed twice, the #23 credit-count repair, and the 1908-09
"Всего—въ N балетахъ—M" format. (The 4 real #124 bugs were also re-checked on their pre-fix raw JSON,
from outputs/full_run_pre_promote_backup_2026-09-30_roster1908-10, which is gitignored.)
"""
from __future__ import annotations

import sys

import quality_checks as q


def row(**k):
    d = dict(page_id="p", entry_id="p__e", family_name="Иванов", first_name="И", patronymic="И",
             heading_path="A / B", list_number="1.", rank_or_title="", service_class="", instrument="",
             subject_taught="", tenure_note_text="", credit_summary_text="")
    d.update(k)
    return d


def credit(label, count, typ="category_totals", production=None):
    return {"credit_type": typ, "label": label, "category_credit_count": str(count),
            "category_production_count": "" if production is None else str(production)}


def main() -> int:
    failures = []

    def expect(label, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, wanted {want!r}")

    # --- duplicate_person_on_page
    dup = lambda a, b: bool(q.find_duplicate_persons([a, b]))
    expect("identical double extraction", dup(row(entry_id="e1"), row(entry_id="e2")), True)
    expect("same person printed twice, other list numbers (Исаева)",
           dup(row(entry_id="e1", list_number="31."), row(entry_id="e2", list_number="38.")), True)
    expect("continuation note split off (note text as list_number, post text in rank_or_title; Нелидовъ)",
           dup(row(entry_id="e1", rank_or_title="колл. рег."),
               row(entry_id="e2", list_number="Съ 1 сентября 1895 г.", rank_or_title="помощникомъ завѣдывающаго")), True)
    expect("continuation note split off (death note as list_number; Бесслеръ)",
           dup(row(entry_id="e1", list_number="9."), row(entry_id="e2", list_number="† 7 марта 1895 г.")), True)
    expect("unnumbered rows, same heading, only the note differs (conservative)",
           dup(row(entry_id="e1", list_number="", tenure_note_text="a"),
               row(entry_id="e2", list_number="", tenure_note_text="b")), True)
    expect("one person, two subjects (Горскій)",
           dup(row(entry_id="e1", subject_taught="Танцы."), row(entry_id="e2", subject_taught="Мимика и пластика.")), False)
    expect("two different headings", dup(row(entry_id="e1"), row(entry_id="e2", heading_path="A / C")), False)
    expect("two numbered entries, different notes (Педдеръ)",
           dup(row(entry_id="e1", list_number="2.", tenure_note_text="Мужскіе парики"),
               row(entry_id="e2", list_number="4.", tenure_note_text="Женскіе парики")), False)
    expect("different pages are never duplicates",
           dup(row(entry_id="e1"), row(entry_id="e2", page_id="other")), False)

    # --- credit repair (#23): "Въ 7 балетахъ—21" stored with 7 where 21 belongs
    r = credit("балетахъ", 7, production=7)
    expect("repair 7 -> 21", q.repaired_credit_count(r, "Въ 7 балетахъ—21; въ 1 оперѣ—1. Всего—22 раза."), "21")
    expect("no repair when stored value is already X",
           q.repaired_credit_count(credit("балетахъ", 21), "Въ 7 балетахъ—21. Всего—21 разъ."), "21")
    expect("no repair when N == X (final period captured)",
           q.repaired_credit_count(credit("драмѣ", 1), "Въ 1 драмѣ—1. Всего—1 разъ."), "1")
    expect("non-category rows untouched",
           q.repaired_credit_count(credit("Дочь фараона", 2, typ="named_work"), "Въ 2 балетахъ—5."), "2")

    # --- total sentence that carries its own category (1908-09): must be skipped by the check
    for txt in ("Всего—всѣ 5 балетахъ—15 разъ.", "Всего—вв 5 балетахъ—15 разъ.", "Всего—5 балетахъ—15 разъ.",
                "Все-ю—вв 1 балетъ—2 раза."):
        expect(f"carries category: {txt}", bool(q._TOTAL_CARRIES_CATEGORY_RE.search(txt)), True)
    for txt in ("Въ 9 балетахъ—31. Всего—36 разъ.", "Въ балетахъ—38; въ операхъ—22. Всего—60 разъ.",
                "Всего—36 разъ. Въ томъ числѣ: Катарина (тюремщикъ—2)."):
        expect(f"does not carry category: {txt}", bool(q._TOTAL_CARRIES_CATEGORY_RE.search(txt)), False)

    # --- classification
    flag, detail = q.classify_credit_mismatch("Въ балетахъ—88; въ операхъ—22. Всего—60 разъ.", 110, 60, [88, 22])
    expect("digit misread candidate (Бюхнеръ 38 read as 88)", flag, "credit_digit_misread_candidate")
    expect("... and names the fix", "part1 88->38" in detail, True)
    flag, _ = q.classify_credit_mismatch("Въ балетахъ—88; въ операхъ—22. Всего—60 разъ.", 110, 60, [110])
    expect("not additive, no look-alike fix", flag, "credit_summary_not_additive")
    flag, _ = q.classify_credit_mismatch("Въ 6 балетахъ—18; въ 1 оперѣ—1; въ дивертисементахъ—3. Всего—22 раза.", 18, 6, [18])
    expect("printed text adds but rows do not", flag, "credit_sum_mismatch")
    flag, _ = q.classify_credit_mismatch("Все—10—64 раза.", 59, 64, [46, 13])
    expect("unparseable text stays actionable", flag, "credit_sum_mismatch")
    # the real 1899-00 entry: «дивертиcсементѣ» has a Latin c; its part must still count (36+15+2+1 = 54, printed 56)
    flag, _ = q.classify_credit_mismatch(
        "Въ 8 балетахъ—36; въ 11 операхъ—15; въ 1 драмѣ—2; въ 1 дивертиcсементѣ—1. Всего—56 разъ.", 54, 56, [36, 15, 2, 1])
    expect("Latin look-alike inside a word does not hide a part",
           flag in ("credit_summary_not_additive", "credit_digit_misread_candidate"), True)

    for f in failures:
        print("FAIL", f)
    print(f"{'FAILED' if failures else 'all cases pass'} ({len(failures)} failure(s))")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
