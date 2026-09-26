"""Choose among the readings several extraction VIEWS produced for one word.

The safety property is the same one `orthography.py` holds, and it is the
whole design: **a selector may only ever choose among readings a view
actually produced.** It never invents a form, and it never "corrects" the
page towards a norm. Pre-reform orthography is unstable by nature (RG,
2026-09-25), so every rule here is a REJECTION of something impossible,
not a preference for something expected -- with two explicitly-marked
exceptions (`hyphen`, `-аго`) that encode a known direction of MODEL bias,
not a claim about the print.

Order matters: filters run first and narrow the candidate set, then the
orthographic judges pick inside what survives, then majority decides.
"""
from __future__ import annotations
import re, collections
from orthography import judge_hard_soft, judge_i_vs_i

VOWELS_I = 'аеиоуыэюяѣіѵ'
CYR = re.compile(r'[а-яёѣіѳѵъь]', re.I)
LAT = re.compile(r'[a-z]', re.I)

def _mixed(tok: str) -> bool:
    """Cyrillic and Latin letters inside one token -- always a model slip."""
    return bool(CYR.search(tok)) and bool(LAT.search(tok))

def _dehyphen(t: str) -> str:
    return t.replace('-', '')

def select(cands: list[str], prefer: str | None = None,
           allow_ago: bool = False) -> tuple[str, str]:
    """Return (chosen reading, reason). `prefer` breaks ties (the full-page view)."""
    if not cands:
        return '', 'no candidates'
    pool = list(cands)

    # 1. a dropped word never beats a read one
    if any(c for c in pool) and not all(pool):
        pool = [c for c in pool if c]
        if len(set(pool)) == 1:
            return pool[0], 'dropped by some views; only one reading offered'

    # 2. a single gold word is one token: multi-token candidates are
    #    alignment debris from a view that merged or shifted lines
    single = [c for c in pool if ' ' not in c.strip()]
    if single and len(single) < len(pool):
        pool = single

    # 3. mixed Cyrillic/Latin inside one word is never right when a clean
    #    reading exists (parse_reviews.repair_mixed_script covers the
    #    single-pass case; this covers disagreement across views)
    clean = [c for c in pool if not _mixed(c)]
    if clean and len(clean) < len(pool):
        pool = clean
        if len(set(pool)) == 1:
            return pool[0], 'other views put Latin letters inside a Cyrillic word'

    if len(set(pool)) == 1:
        return pool[0], 'unanimous after filtering'

    # 4. end-of-line hyphen: gold policy KEEPS it, and the model's bias is to
    #    drop it (4 of 4 observed). Marked: this encodes model bias, not print.
    if len({_dehyphen(c) for c in pool}) == 1:
        hy = [c for c in pool if '-' in c]
        if hy:
            return hy[0], 'candidates differ only by an end-of-line hyphen; kept'

    # 5. orthographic judges -- may only pick a reading present in `pool`
    pick, why = judge_hard_soft(pool)
    if pick is not None:
        return pick, f'ъ/ь: {why}'

    # і/и is applied in ONE DIRECTION ONLY. "і before a vowel or й" holds;
    # the converse ("и everywhere else") does not, because the print is not
    # consistent -- this corpus prints both Тихоміровъ and Тихомировъ, and
    # the unrestricted rule overwrote the first with the second twice on the
    # gold set while fixing nothing. Accept the judge only when its answer
    # actually puts і before a vowel or й.
    pick, why = judge_i_vs_i(pool)
    if pick is not None and re.search(r'і[%sй]' % VOWELS_I, pick, re.I):
        return pick, f'і/и: {why}'

    # 6. -аго/-ого. OFF by default: it asserts a norm the print may not hold.
    if allow_ago and len({c.replace('аго', 'ого') for c in pool}) == 1:
        ago = [c for c in pool if 'аго' in c]
        if ago:
            return ago[0], 'pre-reform -аго over modernised -ого (OPT-IN)'

    # 7. majority, ties to the preferred view.
    #    When nothing wins more than one vote the pick is ARBITRARY, and the
    #    selector says so rather than pretending: the reason is prefixed
    #    REVIEW: and the caller routes it to a human. This is the case that
    #    caught юбилияръ/юбиляръ/юбилярь, where the 2-run majority was wrong
    #    and RG had to read the scan at 9x.
    c = collections.Counter(pool)
    best = max(c.most_common(), key=lambda kv: (kv[1], kv[0] == prefer))
    if best[1] <= 1:
        return best[0], f'REVIEW: no majority, {len(set(pool))} distinct readings'
    return best[0], f'majority {best[1]}/{len(pool)}'


# ---------------------------------------------------------------------------
# Self-test, built from RG's own rulings and the gold set -- the same gate
# orthography.py carries. A rule change that breaks any of these is wrong.
# Run: uv run python pipeline/select_reading.py
# ---------------------------------------------------------------------------
_CASES = [
    # (candidates, expected, note)
    (['Легать', 'Легать', 'Легатъ'], 'Легатъ', "RG 2026-09-24"),
    (['Аслинь,', 'Аслинъ,', 'Аслинь,'], 'Аслинъ,', "RG 2026-09-24"),
    (['говорить', 'говоритъ', 'говорить'], 'говоритъ', "3sg verb takes ъ"),
    (['куколь»', 'куколъ»', 'куколь»'], 'куколъ»', "gen. pl."),
    # RG read this at 9x: HARD sign. The reverted -арь/-ярь rule got it wrong.
    # юбилияръ/юбиляръ/юбилярь is NOT here: three distinct readings, no
    # majority, and no rule can separate them -- the selector must flag it
    # for review rather than guess. Asserted in _MUST_FLAG below.
    (['пожарь', 'пожаръ', 'пожаръ'], 'пожаръ', "hard consonant"),
    # і/и one-directional: the print holds BOTH spellings of this name, so a
    # produced і before a consonant must survive.
    (['Тихоміровъ', 'Тихомировъ', 'Тихоміровъ'], 'Тихоміровъ', "і kept; RG: print is unstable"),
    # end-of-line hyphen is kept in a diplomatic transcription
    (['февраля', 'фев-раля', 'февраля'], 'фев-раля', "printed line break"),
    # Latin inside a Cyrillic word is never right
    (['Чума-kova,', 'Чума-кова,', 'Чума-kova,'], 'Чума-кова,', "mixed script"),
    (['tого', 'tого', 'того'], 'того', "mixed script"),
    # a dropped word never wins
    (['', '', 'II,'], 'II,', "empty loses"),
    # alignment debris (a view that merged lines) never wins
    (['составъ труппы произошли', 'составѣ', 'составъ'], None, "multi-token dropped"),
    # pure-Latin French titles must NOT be touched by the mixed-script filter
    (['Merveilleuses:', 'Merveileuses:', 'Merveilleuses:'], None, "Latin-only untouched"),
]

# Cases the selector must NOT decide silently -- it has to ask for a human.
_MUST_FLAG = [
    (['юбилияръ', 'юбиляръ', 'юбилярь'],
     "RG 2026-09-25: 2-run majority was WRONG; the answer needed the scan at 9x"),
]

if __name__ == '__main__':
    bad = 0
    for cands, want, note in _CASES:
        got, why = select(list(cands), prefer=cands[0])
        if want is None:
            ok = ' ' not in got.strip() and not _mixed(got)
            verdict = 'ok' if ok else 'FAIL'
        else:
            ok = (got == want); verdict = 'ok' if ok else 'FAIL'
        if not ok: bad += 1
        print(f'{verdict:4s} {str(cands)[:52]:54s} -> {got!r:22s} [{note}]')
    for cands, note in _MUST_FLAG:
        got, why = select(list(cands), prefer=cands[0])
        ok = why.startswith('REVIEW:')
        if not ok: bad += 1
        print(f'{"ok" if ok else "FAIL":4s} {str(cands)[:52]:54s} -> flagged={ok}  [{note[:44]}]')
    n = len(_CASES) + len(_MUST_FLAG)
    print(f'\n{n-bad}/{n} pass')
    raise SystemExit(1 if bad else 0)
