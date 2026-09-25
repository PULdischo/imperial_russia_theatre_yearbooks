"""Pre-1918 orthographic rules, for choosing between competing readings.

RG, 2026-09-26: "I think we can leave the raw layer whatever it is, then use
grammar and logic to make sure the proper letter appears in the research
layer."

So nothing here edits a transcription. These functions ADJUDICATE between
variants that the extraction passes disagree about, and say which rule
decided it. Two uses:

  1. Triage. Where three passes disagree on ъ/ь or a pre-reform letter, the
     rule usually settles it without a human. On the 200-page pilot this
     took the hard/soft-sign queue from 25 cases to 1.
  2. Later, a normalised field in the research layer, derived from raw the
     way analysis.role_normalized is derived in the tabular pipeline.

THE DISCIPLINE THAT MAKES THIS SAFE. A rule says what the language requires,
not what the compositor set. This corpus demonstrably prints things the
language does not require -- "Пребраженская" for "Преображенская" on a page
that also prints it correctly four lines up. So a rule may NEVER override
what a pass actually read:

  * rule agrees with a reading a pass produced  -> settled, low risk
  * rule contradicts every reading              -> FLAG. Either every pass
    misread, or the page really prints something irregular, and only the
    scan distinguishes those. On the pilot this fired once, on "они
    слышать", where the scan confirmed the rule and both passes were wrong.

Never use these to "fix" a reading no one disputed. That is exactly the
normalising habit the prompt now forbids the model.
"""
from __future__ import annotations

import re

VOWELS = "аеёиоуыэюяіѣѵ"
# ъ before a vowel is a separator, and in pre-reform orthography it appears
# there ONLY after a prefix. Elsewhere the separator is ь.
PREFIXES = ("об", "объ", "от", "под", "пред", "раз", "роз", "с", "в", "из",
            "без", "воз", "над", "меж", "сверх", "двух", "трех", "четырех")

# Words that genuinely end in a soft sign. Not exhaustive -- it does not need
# to be, because an unknown word simply goes unjudged rather than guessed.
SOFT_FINAL = {
    # 3rd-declension feminines
    "жизнь", "смерть", "часть", "власть", "роль", "рѣчь", "ночь", "дочь",
    "мать", "вещь", "любовь", "радость", "милость", "область", "печать",
    "связь", "пѣснь", "степь", "тѣнь", "цѣль", "честь", "новость",
    # masculines that really do take ь
    "царь", "князь", "конь", "день", "огонь", "корабль", "рубль", "путь",
    "зритель", "учитель", "писатель", "родитель", "деятель", "житель",
}
# Soft-sign noun classes narrow enough to be safe. Two attempts were wrong:
#   * bare "нь"/"ль"/"рь" -- far too broad; flipped "Аслинъ" and "театралъ".
#   * "арь"/"ярь" -- январь and словарь take ь, but пожаръ and самоваръ do
#     not, so the ending alone cannot decide. (An earlier bug hid this: the
#     test ran on the STEM, so "пожар" never met "арь" and the wrong rule
#     looked right.)
# Anything not covered here is left to SOFT_FINAL, or goes unjudged.
SOFT_SUFFIXES = ("тель", "ырь", "знь", "сть", "чь", "щь")


def _strip(w: str) -> str:
    return w.strip(" .,;:!?()[]«»„“”—–-").strip()


def judge_hard_soft(variants: list[str]) -> tuple[str | None, str]:
    """Pick between readings differing only in ъ/ь. Returns (choice, reason).

    choice is None when no rule applies, or when the rule's answer is not
    among the variants offered -- that second case is a FLAG, not a failure.
    """
    forms = [_strip(v) for v in variants]
    if len({f.replace("ъ", "").replace("ь", "") for f in forms}) != 1:
        return None, "not a pure ъ/ь difference"

    for f in forms:
        # ---- ъ before a vowel: only after a prefix -----------------------
        m = re.search(r"ъ([%s])" % VOWELS, f, re.I)
        if m:
            stem = f[:m.start()].lower()
            if not any(stem == p or stem.endswith(p) for p in PREFIXES):
                want = f[:m.start()] + "ь" + f[m.start() + 1:]
                for v, g in zip(variants, forms):
                    if g == want:
                        return v, ("ъ before a vowel occurs only after a "
                                   f"prefix; {stem!r} is not one")
                return None, (f"rule says {want!r} but no pass read that "
                              "-- CHECK THE SCAN")

    # ---- word-final ------------------------------------------------------
    if all(f and f[-1] in "ъь" for f in forms):
        # compare the WHOLE soft-sign form, not the stem: an earlier version
        # looked up "цар" in a list holding "царь" and so never matched,
        # which made it answer "царъ" and "ролъ".
        soft_form = forms[0][:-1].lower() + "ь"
        soft = soft_form in SOFT_FINAL or soft_form.endswith(SOFT_SUFFIXES)
        # Found on triage page 9: the page prints "юбилярь", a masculine
        # noun in -ярь like январь/словарь/вратарь. The suffix test above
        # matched the STEM, so "юбиляр" never met "ярь".
        want_last = "ь" if soft else "ъ"
        for v, g in zip(variants, forms):
            if g[-1] == want_last:
                return v, ("a word ending in a soft consonant takes ь"
                           if soft else
                           "pre-1918: a word ending in a hard consonant "
                           "takes ъ")
        return None, (f"rule wants a final {want_last!r} but no pass read "
                      "that -- CHECK THE SCAN")

    return None, "no rule applies"


def judge_i_vs_i(variants: list[str]) -> tuple[str | None, str]:
    """і vs и. Positional and exceptionless in pre-1918 orthography:
    і is written before another vowel or before й; и everywhere else."""
    forms = [_strip(v) for v in variants]
    if len({f.replace("і", "и") for f in forms}) != 1:
        return None, "not a pure і/и difference"
    canon = []
    for ch, nxt in zip(forms[0], forms[0][1:] + " "):
        if ch in "иі":
            canon.append("і" if nxt.lower() in VOWELS + "й" else "и")
        else:
            canon.append(ch)
    want = "".join(canon)
    for v, g in zip(variants, forms):
        if g == want:
            return v, "і stands before a vowel or й; и elsewhere"
    return None, f"rule says {want!r} but no pass read that -- CHECK THE SCAN"
