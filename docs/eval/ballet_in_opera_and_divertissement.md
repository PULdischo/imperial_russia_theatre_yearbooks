# Ballet inside opera, and opera music inside ballet

First concrete evidence for the long-open "drama/opera with ballet or
dancers" research thread, found 2026-10-07 while scoping the Season Reviews
mention work. RG: *"you're right this is important not to lose."*

## How it surfaced

Entirely by accident. The mention matcher flagged seven people as absent
from `research.person`: Гуно, Бородинъ, Римскій-Корсаковъ, Верди,
Мейерберъ, Бизе, Фигнеръ. They turned out to be an **opera artifact** —
293 occurrences in opera reviews against 10 in ballet ones — because the
entity database was built from ballet-priority sources.

The interesting part was the residue. Those **10 ballet-review occurrences**
are not contamination. They are ballet content that happens to involve
opera composers, and they would be invisible to any filter working on genre
alone.

## The instances (genre = Ballet, all from single-genre ballet PDFs)

| season | city | what the review records |
|---|---|---|
| 1901-02 | Moscow | `Вальсъ «Фантазія», муз. Глинки` — danced in a divertissement by г-жи Ѳедорова 5, Чумакова 1, Павлова, Соколова, Молчанова, Некрасова 1 |
| 1901-02 | SP | `Танцы изъ оперы «Жизнь за Царя», муз. Глинки` — opera dances lifted into a divertissement |
| **1904-05** | **Moscow** | **`г. Горскимъ были поставлены вновь танцы въ операхъ: Глинки «Жизнь за Царя» (вальсъ и финалъ); въ «Тангейзерѣ» Вагнера танцы 1-го и 3-го`** — the balletmaster choreographing inside operas |
| 1905-06 | Moscow | `Les ombres Chinoises, муз. Гуно` with a full ballet cast (Дѣвушка, Монахъ, Рыцарь, Воръ) |
| **1905-06** | **SP** | `Вальсъ фантазія (муз. М. Глинки)` — danced by students including **в-къ Нижинскій** |
| 1910-11 | SP | charity gala programme: Meyerbeer `Динора`/`Гугеноты`, Tchaikovsky, Delibes `Лакме`, Leoncavallo, Gounod `Ромео и Джульетта` |
| 1910-11 | SP | Римскій-Корсаковъ, Глазуновъ, Лядовъ, Черепнинъ named as composers who worked with the balletmaster |
| 1896-97 | SP | Rimsky-Korsakov named because an opera's SETS were reused for a ballet |

## Why it matters

Three distinct phenomena, none of them capturable from the Repertoire tables:

1. **Opera music used for ballet** — divertissement numbers set to Glinka and
   Gounod. The work exists in the repertoire as an opera; the ballet use of
   it is recorded only in prose.
2. **Ballet staged inside opera** — Gorsky's dances for `Жизнь за Царя` and
   `Тангейзеръ`. This is ballet labour, credited to the balletmaster, that
   appears in no ballet production list.
3. **Mixed galas** — charity programmes drawing acts from both repertoires.

## Consequence for scope

RG scoped the mention work to ballet reviews on 2026-10-07 and deferred
opera. That holds — but **these nine stay in**, and the filter for the
eventual opera pass should be *"unknown name in a ballet context"* rather
than *"unknown name"*, which is a short list where every entry is on topic.

Related: the standing note that works in the Ballet Production lists get
parent genre ballet while the printed genre stays verbatim. These cases are
the inverse — ballet activity attached to works whose genre is opera — and
may need their own treatment rather than a genre reassignment.
