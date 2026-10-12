# The 37 remaining title-misread candidates, triaged

`outputs/reviews/mentions/review_title_candidate_misreads.csv`, regenerated
by `pipeline/match_review_mentions.py` on every run. **37 forms, 58
occurrences.** Down from 40 forms / ~90 occurrences after the two large
ones (`Камаріо`→Камарго ×27, `Балдерка`→Баядерка ×7) were scan-checked and
fixed on 2026-10-10.

## What this list costs, measured

**Nothing in the data.** `research.work` is built from the Repertoire
(`raw.event_entry_performance`), never from the reviews, so an unresolved
review title creates no work row and corrupts nothing:

```sql
SELECT count(*) FROM research.work WHERE canonical_title = 'Маркитанка';  -- 0
```
(Same for `Шелкунчикъ`, `Апись и Галатея`, `Облака`, `Гаарлемскій тюльпанъ`.)

The entire cost is **58 unresolved links, 1.6% of the 3,736 work mentions.**

## The triage

**1. Declensions, not misreads — ~30 occurrences, 14 forms.** The review
prints an oblique case of the right work: `Конька-горбунка`,
`Конькѣ-Горбункѣ` (15 between them), `Египетскими ночами`, `Раймондой`,
`Эсмеральдой`, `Шопеніаной`, `Царя Кандавла`, `Дочери Фараона`,
`Оживленномъ саду`, `Феѣ куколъ`.

*Why the matcher misses them, and why it is not worth forcing.*
`stem_key` truncates each word to 4 characters, which is too long for short
words — the inflection lands inside the stem (`ночи`/`ноча`, `сад`/`саду`,
`царь`/`царя`). A per-word stem-prefix rule separates these from genuinely
different works cleanly in 14 of 16 test cases, but fails on exactly the two
that matter: the fleeting vowel in `Конекъ`→`Конька` defeats any prefix
threshold loose enough to admit it without also admitting `Облака`/`Облава`.
Tried and not shipped.

**2. Not works at all — 3 occurrences.** `Облака` is a *scene* name in a
decorations list (`«Облака» (2-я картина)—г. Шеньяномъ`), beside «Дворъ
замка», «Лѣсъ», «Киргизская юрта». The matcher treats any quoted string in
such a list as a title. `Облава` is a comedy and the match is spurious.

**3. Genuinely DIFFERENT works the matcher nearly conflated — 5
occurrences.** `Волшебный островъ` vs `Волшебный стрѣлокъ`, `Волшебное
озеро` vs `Волшебное зеркало`, `La nuit parisienne` vs `La Parisienne`.
These are the reason the list is *reported* rather than applied, and the
reason a loose fuzzy match was never shipped.

**4. Real candidate misreads, worth a scan check if anyone wants the
links — ~15 occurrences.** `Триключенія`/`Прилюченій Флика и Флока`,
`Апись`/`Апсисъ и Галатея`, `Шелкунчикъ`→Щелкунчикъ, `Фея нуколь`,
`Маркитанка`→Маркитантка (the body prints Маркитантка on 1900-01 p030 and
p031), `Испытаніе Далиссы`, `Ѳетида и Пелей`, `Ученики Допро`→Дюпре,
`Золотая рыба`/`рыбка`, `Гаарлемскій`/`Гарлемскій тюльпанъ` (already known
to be one work, similarity 0.973), `La romanesque`/`Les romanesques`.

Two of these point at the **database** rather than the review:
`Испанцы`→`Панцы` and possibly `Ѳетида`/`Ѳемида и Пелей` — `Панцы` is not
a word, so the Repertoire row is the likelier error.

## Recommendation

Leave it. The list regenerates on every run, costs 1.6% of work mentions,
and corrupts nothing. Group 4 is a half-day of scan checks for about 15
links; group 1 is a known matcher limitation with a documented failed fix.
