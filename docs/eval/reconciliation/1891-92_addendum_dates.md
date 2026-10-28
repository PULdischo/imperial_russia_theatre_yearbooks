# 1891-92 addendum (2026-10-28): the 40 not_captured dates read on the scan

To merge into `README.md` (1891-92 section, "Found along the way", replacing the first bullet) and `docs/query_log.md`.
Scan reads appended to `docs/eval/scan_audit/1891-92_scan_reads.csv` (15 rows, "no printed row (source skip)"); the same
commit fixes three rows of that file whose «Донъ-Жуанъ, музыка…» field was split by an unquoted comma.

## README replacement bullet

- 200 `not_captured` placeholders on 40 whole dates (Moscow 80 = 2 × 40, SP 120 = 3 × 40: every date is missing in all
  five theaters at once). **Read on the scan, 2026-10-28** (RG: "do this just in case"): all 15 runs checked in the date
  column (`docs/eval/scan_audit/1891-92_scan_reads.csv`). Each is a skip in the print: the dates on either side sit in
  adjacent cells (e.g. «11 Среда.» → «19 Четвергъ.» over 12-18 Sept 1891; «16 Воскрес.» → «23 Воскр.» over 17-22 Feb 1892;
  «27 Пятница.» → «апрѣль 6 Понед.» over 28 Mar - 5 Apr 1892). 28-29 Aug 1891 fall at the p. 2/3 break (p. 2 closes on
  27 Aug, p. 3 opens on 30 Aug). No content is missing.

## Query-log entry

## 2026-10-28 — 1891-92 not_captured placeholders as runs, with the printed neighbours

```sql
with ev as (select cast(date as date) d, event_status, event_id, printed_page_number pg, date_verbatim dv
            from research.event where season='1891-92'),
nc as (select distinct d from ev where event_status='not_captured'),
runs as (select d, d - cast(row_number() over (order by d) as int) as g from nc),
rr as (select min(d) s, max(d) e, count(*) n from runs group by g)
select s, e, n,
       (select max(d) from ev where event_status<>'not_captured' and d<s) prev,
       (select min(d) from ev where event_status<>'not_captured' and d>e) nxt,
       (select min(dv) from ev where event_status<>'not_captured' and d=(select max(d) from ev where event_status<>'not_captured' and d<s)) prev_dv,
       (select min(dv) from ev where event_status<>'not_captured' and d=(select min(d) from ev where event_status<>'not_captured' and d>e)) next_dv
from rr order by s;
-- then page and pair of each neighbouring date:
select cast(date as varchar) d, string_agg(distinct printed_page_number, '/'), string_agg(distinct split_part(event_id,'__',1), '/')
from research.event where season='1891-92' and event_status<>'not_captured' and cast(date as varchar) in (<the 30 neighbour dates>) group by 1;
```

Result: 15 runs, 40 dates: 17 Aug; 24 Aug; 28-29 Aug; 7 Sept; 12-18 Sept; 23-25 Dec 1891; 5 Jan; 13 Jan; 18 Jan; 17-22 Feb;
1 Mar; 28 Mar - 5 Apr; 1-2 May; 8-9 May; 13-14 May 1892. Neighbours on pp. 2-25, spreads 0, 1, 5, 6, 8, 9, 11. Every stored
neighbour's weekday word skips the gap; all 15 read on the scan as print skips (checked by Claude).
