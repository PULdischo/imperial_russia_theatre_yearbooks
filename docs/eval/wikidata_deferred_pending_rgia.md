# Wikidata matches deferred pending archival evidence

RG, 2026-10-09: *"let's keep these unmatched for now, with the understanding
that perhaps something in the RGIA archival materials might confirm.
Fortunately, administrators are less important than ballet creators or
dancers."*

Four Imperial Theatres administrators whose Wikidata candidates match on name,
patronymic and plausible dates, but whose items are **stubs** — no occupation,
usually no description — so nothing independently ties them to the theatres.
Recorded as `decision = 'defer'` in `entities.wikidata_decision`, which keeps
the candidate QID on record and stops `link_wikidata.py` re-queuing them,
**without** the finality of a `No`. Reopen when an archival source names them.

| ours | post held | candidate | |
|---|---|---|---|
| **Вуичъ, Георгій Ивановичъ** 1902-03–1906-07 | Управляющій С.-Петербургской Конторой | [Q15065141](https://www.wikidata.org/wiki/Q15065141) 1867–1957 | alias `Георгий Иванович Вуич`, ruwiki article; age 35–39 in post |
| **Крупенскій, Александръ Дмитріевичъ** 1902-03–1910-11 | Помощникъ Управляющаго, SP Контора | [Q4242183](https://www.wikidata.org/wiki/Q4242183) 1875–1939 | alias `Александр Дмитриевич Крупенский`, ruwiki article |
| **Хитрово, Георгій Михайловичъ** 1898-99–1901-02 | Чиновникъ особыхъ порученій, камеръ-юнкеръ | [Q138573040](https://www.wikidata.org/wiki/Q138573040) 1875–1916 | bare stub; age 23–26, plausible for a young court official |
| **Бобринскій, Алексѣй Алексѣевичъ** 1900-01–1908-09 | графъ, Чиновникъ особыхъ порученій, Moscow Contora | **two live options** | see below |

Бобринскій is the one that genuinely splits. Four candidates; two are out
(Q4088707 died 1868, Q129434984 born 1893, an actor). The remaining two both
fit a count serving 1900–1909 and nothing in our data separates an official
from a scholar:

- [Q107124870](https://www.wikidata.org/wiki/Q107124870), 1864–1909 — bare stub
- [Q4088702](https://www.wikidata.org/wiki/Q4088702), 1861–1938, "scientist", ruwiki article

All four candidate rows are kept in `entities.wikidata_decision` so the choice
is still there to make.

**What would settle these:** a service record or appointment paper naming the
official — Fond 497 holds the Directorate's own administration, so the
personnel дела are the natural place. See `docs/rgia_request_log.csv`.

To apply a later decision, put the QID (or `No`) in
`outputs/full_run/wikidata_review_queue.csv` and run
`pipeline/apply_wikidata_decisions.py`.
