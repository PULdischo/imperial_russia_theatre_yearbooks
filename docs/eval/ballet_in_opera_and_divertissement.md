# Ballet inside opera, and opera music inside ballet

Evidence for the long-open "drama/opera with ballet or dancers" research thread.
RG, 2026-10-07: *"Confirming that these types of opera-ballet mixes are vitally
important to my research!"*

Reproduce with:

```
uv run python pipeline/find_opera_ballet_crossover.py \
    --reviews-dir outputs/reviews/merged_full \
    --db outputs/full_run/imperial_theaters.duckdb \
    --out outputs/reviews/opera_ballet_crossover.csv
```

## How it surfaced, and why the first count was wrong

Entirely by accident. The mention matcher flagged seven people as absent from
`research.person`: Гуно, Бородинъ, Римскій-Корсаковъ, Верди, Мейерберъ, Бизе,
Фигнеръ. They were an **opera artifact** -- 293 occurrences in opera reviews
against 10 in ballet ones -- because the entity database was built from
ballet-priority sources. The residue of 10 ballet-review occurrences was real
crossover, and got written up here as "nine instances."

**That number was an artifact of the probe, not a finding.** It counted only
passages that happened to name one of seven opera composers. The systematic
sweep finds **32 substantive passages** and, more importantly, a category the
accident could not have reached: the reviews' own season-level tallies of
ballet-opera shared bills, which name no composer at all.

Two corrections to the earlier write-up:

- **1904-05 Moscow is much richer than recorded.** It was logged as Gorsky
  staging dances in two operas. The passage names **five operas and two
  balletmasters**: Горскій in Глинка's «Жизнь за Царя» (вальсъ и финалъ),
  Вагнер's «Тангейзеръ» (acts 1 and 3), Рубинштейн's «Демонъ» (a Solo for
  г-жа Федорова 5), А. Сѣровъ's «Юдифь» (act 3), and **Манохинъ** in Тома's
  «Гамлетъ» (крестьянскій танецъ).
- **The method had a silent bug.** The stored review text keeps the printed line
  breaks, so a word split across one arrives as `сопер- никамъ` or
  `спек- такля`. Every pattern spanning a break failed silently, and a non-match
  is indistinguishable from an absent phenomenon. `find_opera_ballet_crossover.py`
  reflows before matching. Worth remembering for any future regex over this
  corpus.

## The taxonomy

| category | n | what it is |
|---|---|---|
| `mixed_bill` | 16 | one evening programmed from both repertoires |
| `opera_music_for_dance` | 4 | opera numbers danced as ballet |
| `season_closed_with_opera` | 2 | the ballet season's last night was an opera |
| `foreign_opera_house_credential` | 2 | a guest billed as of the Paris/Berlin opera |
| `gala_or_benefit_programme` | 2 | charity and benefit bills drawing on both |
| `dancer_appeared_in_opera` | 2 | a named dancer performing inside an opera |
| `opera_excerpt_on_ballet_bill` | 1 | an opera scene, with its singers, in a ballet review |
| `shared_production_resources` | 1 | sets or costumes reused across the two |
| `opera_influence_noted` | 1 | a critic hearing opera in a ballet score |
| `dances_staged_in_opera` | 1 | a balletmaster credited for choreography in operas |

Ten more passages are labelled noise rather than dropped, so the suppression
stays auditable: `roster_bleed` (9) is singer-transfer prose that reaches ballet
reviews only because the same printed page was scanned into both PDFs, and
`narrative_comparison` (1) is a remark about ticket queues.

The stem `опер` cannot be used raw here. It collides with
`соперникъ`/`соперница` (rival -- pervasive in ballet synopses), `Фебъ де
Шатоперъ`, `Поперекъ`, `поперемѣнно`. The test that works is per occurrence: a
passage is noise only when *every* `опер` in it sits inside a collision word.
Asking merely whether a collision word is present throws away real passages;
asking only after no category matched keeps false ones -- the Баядерка scenery
list names a scene `Двѣ соперницы` inside a passage whose other words look
exactly like an opera excerpt.

## The strongest result: two pipelines agreeing on nine counts

Several ballet reviews open by tallying the season, including how many
performances were `смѣшанные спектакли` shared with opera. That is a
season-level number sitting in narrative prose, and the Repertoire tables
produce the same number independently -- different source PDFs, different
extraction method, different schema.

| season | city | the review says | Repertoire |
|---|---|---|---|
| 1891-92 | SP | 4 of 45, `балета «Сильфида» и одноактной оперы «Поэтъ»` | **4** |
| 1892-93 | SP | 41 ballet + 11 mixed, `балетъ «Щелкунчикъ» и опера «Іоланта»` | **11** |
| 1893-94 | Moscow | 43 ballet + `2 смѣшанныхъ (балетъ и опера вмѣстѣ)` | **2** |
| 1893-94 | SP | `балетъ и опера—2`, plus one four-way bill | 2 (see below) |
| 1894-95 | Moscow | 27 ballet + 3 mixed, `2—съ оперой` | **2** |
| 1894-95 | SP | 8 mixed: `4—вмѣстѣ съ русской драмой и 4 — вмѣстѣ съ оперой` | **4** |
| 1895-96 | Moscow | 31 ballet + `13 смѣшанныхъ ... совмѣстно съ оперой` | **13** |
| 1896-97 | Moscow | 53 ballet + 4 mixed `совмѣстно съ оперой` | **4** |
| 1897-98 | Moscow | 48 ballet + 3 mixed `совмѣстно съ оперой` | **3** |

Eight exact. For 1892-93 SP the eleven dates are all recoverable:
6, 8, 11, 13, 14, 16, 17, 26 December 1892 and 1, 12, 15 January 1893, all at
the Маріинскій -- the review's bare number gains a date list, the Repertoire's
dates gain the review's framing.

The script prints the review's tally sentence **verbatim** beside the database
count and deliberately does not parse it into a number. Prose like
`4—вмѣстѣ съ русской драмой и 4 — вмѣстѣ съ оперой` is exactly where an
automatic reading goes wrong quietly, and a misparse here would look like a data
error in one of the two layers rather than in the comparison.

### The ninth is the interesting one

1893-94 SP reports `балетъ и опера—2` **plus** one four-way bill,
`балетъ, русская драма, опера и французская драма—1`, so three bills involve
opera. The database finds two. The missing one is the Greek earthquake benefit
at the Михайловскій, 29 April 1894, which the Repertoire records as:

> `Въ пользу пострадавшихъ отъ землетрясенія въ Греціи + Жены [этюдъ] +
> Le petit Hôtel [com.] + Концертное отдѣленіе + 1-е и 2-е д. бал. Коппелія`

Russian drama, French drama and ballet are all named. The opera troupe is inside
`Концертное отдѣленіе` -- an entry that names no works -- so no genre test can
ever see it. The shortfall is not an extraction error in either layer; it is the
tabular source declining to itemize, and the review supplying what it withheld.

## Where the reviews carry what the tables cannot

**128 events** have a programme entry whose content the Repertoire does not name:
`Дивертиссементъ` (82 occurrences, in 19 of the 21 seasons in the database), `Балетный
дивертиссементъ` (9), `Концертное отдѣленіе` (9), various `Концертъ` forms.
Written to `opera_ballet_crossover_unnamed_programme.csv`.

The reviews itemize many of these, and the opera-derived dance numbers live
precisely inside the itemizations. Two worked examples, both 1901-02 SP, joined
on season + city + date + theatre:

| | Repertoire | the review |
|---|---|---|
| 21 Nov 1901 | `Пахита + Дивертиссементъ`, Маріинскій, 673,163 kop. | Bekefi's 25-year benefit; Пахита in its 17th revival performance, Замбелли as Пахита (first time), Гердтъ as Count d'Hervilly; divertissement with the Moscow guests Гельцеръ and Тихомировъ plus Преображенская, Петипа, Гердтъ, Бекефи — item 1) **`Танцы изъ оперы „Жизнь за Царя“, муз. Глинки`** |
| 27 Jan 1902 | `Донъ Кихотъ Ламанчскій + Дивертиссементъ`, Маріинскій, 657,543 kop. | divertissement with О. Преображенская: 1) Valse Empire 2) Kracovienne 3) Pas de la Fascination 4) Русская пляска 5) Tarantelle — each with its full cast |

The Repertoire holds the date, theatre and receipts; the review holds the
programme, the casts and the opera provenance. Neither is recoverable from the
other, and the join key is exact.

This is the same asymmetry noted for the mention layer generally: the spiski
carry role + work with no date, the Repertoire carries dates with no role, and
the reviews carry both.

## Why it matters

Four phenomena, none capturable from the Repertoire tables alone:

1. **Opera music used for ballet** -- divertissement numbers set to Глинка,
   Чайковскій, Гуно. The work exists in the repertoire as an opera; its ballet
   use is recorded only in prose.
2. **Ballet staged inside opera** -- Горскій's and Манохинъ's dances for five
   operas in 1904-05 Moscow alone. This is ballet labour, credited to a
   balletmaster, that appears in no ballet production list.
3. **Shared bills** -- counted season by season, and confirmed against the
   Repertoire to the exact number.
4. **Shared production resources** -- the 1896-97 «Млада» revival reusing the
   1892 sets built for Римскій-Корсаковъ's opera of the same name; the 1905-06
   Moscow «Дочь фараона» benefit taking most of its sets from the opera
   «Моисей» (Зора).

## Consequence for scope

RG scoped the mention work to ballet reviews on 2026-10-07 and deferred opera.
That holds -- but these 32 passages stay in, and the filter for the eventual
opera pass should be *"unknown name in a ballet context"* rather than *"unknown
name"*, which is a short list where every entry is on topic.

Related: works in the Ballet Production lists take parent genre ballet while the
printed genre stays verbatim. These cases are the inverse -- ballet activity
attached to works whose genre is opera -- and may need their own treatment
rather than a genre reassignment.

**Open, not started:** itemizing the 128 unnamed-programme events against the
reviews. That is the concrete worklist this sweep produced, and it is where the
remaining crossover is most likely to be hiding.

## The cross-check generalises beyond mixed bills — two open items

The reviews also state **per-work performance counts**, and those check out too
(1903-04 SP: `Раймонда` 5 = 5; `Конекъ-Горбунокъ ... данный 6 разъ` = 4 full
appearances + 2 excerpt appearances. 1904-05 Moscow: `Донъ-Кихотъ` 4 = 4,
`Золотая рыбка` 7 = 7, `Конекъ-Горбунокъ` 7 = 7).

Note the counting subtlety before automating this: the review's "6 times"
folds full performances together with excerpt appearances. A naive comparison
would read that as a discrepancy.

**Two that did not reconcile, found 2026-10-07, NOT yet investigated** (logged
per RG's rule on tangents, not chased):

1. **`Гаарлемскій тюльпанъ`, 1903-04 SP** — the review says it had 4
   performances (`4 представленія выдержалъ Гаарлемскій...`). No work matching
   `%аарлемск%` is in `research.work` for that season. Either a spelling
   variant the title match missed, or a genuinely absent work.
2. **`Баядерка`, 1904-05 Moscow** — the review says 2 performances plus acts 1,
   2 and 3 given once each; the database has 1.

Both are candidate Repertoire gaps rather than review errors, on the strength
of the eight exact matches above, but neither has been checked against a scan.
