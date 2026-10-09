# Printed-page-range audit (issue #139 follow-up), 2026-10-09

Question: the backfill in `parse_and_validate.py` gives each Repertoire event its `printed_page_number` by matching `date_undate` against the date ranges in `outputs/full_run/printed_page_numbers_all.csv` (gitignored). #139 found three ranges that ended too early (events fell outside every range). A range that is wrong but has no stray events would go unnoticed, so every range of every two-page-spread season (1890-91..1897-98) was checked against the scans.

Scope: 91 spreads = 182 printed pages (single-page seasons 1898-99..1910-11 carry one folio per page_id with no date ranges, so there is nothing to mis-bound there).

1. `compare_headers.py`: each spread's OUTER boundaries against the extracted page headers (`all_page_headers.csv`): 99 of 100 spread/page ids match; 1 differs (1891-92 pair002, header extracted as "1 августа", a misread of 16 августа) and 1 has no header on file (1892-93 pair016).
2. Blind reads: `READER_PROMPT.md`, `bundle_*.json`, `reader_reports/`: six readers each read the header band (each printed page's own date header + first/last day columns) of ~15 spreads, never shown the stored ranges.
3. `compare_reads.py` (`step2_result.json`): 168 of 182 printed pages matched exactly; 12 differed and 2 were partly unreadable. Adjudicated by zooming on the scans:
   - 5 differences are the file splitting ONE printed page over two page_ids with the same folio (1890-91 pair014/p015, pair022/p023, pair024/p023, 1891-92 pair002/p003): folios are correct, no change.
   - 1890-91 pair008: the reader looked at the wrong image (the extra `_002a` photograph shifts the pair-to-scan arithmetic for 1890-91); the right scan reads 12-21 Oct and 22-31 Oct, as in the file.
   - 1896-97 pair002 (file p. 2 ends 31 Aug, print 27 Aug) and 1897-98 pair020 (file p. 21 ends 13 Mar, print 12 Mar): the file's range is wider than the print, with no events in the extra days: harmless, left as is.
   - 1894-95 pair002 right page: tape hides the first digit of the header, the first column reads "30 Вторникъ" = the file. 1892-93 pair002 right page "27 августа" (checked in #139): fine.
   - **2 real boundary errors (fixed):** 1892-93 pair024: the left page's header ends "2 мая" and its last column is the 2nd; the right page begins "3 мая" -> p. 24 = 22 Apr-2 May, p. 25 = 3-14 May (the 5 events of 2 May 1893 move p. 25 -> p. 24). 1897-98 pair024: left page ends "15 апрѣля", right page begins "16 апрѣля" / "16 Четвергъ" -> p. 24 = 9-15 Apr, p. 25 = 16-25 Apr (the 5 events of 16 Apr 1898 move p. 24 -> p. 25).
Result: 10 events changed folio; none has a null page number; receipts, research.event (32,901), research.performance (30,909) and person links unchanged. Backup `outputs/full_run_pre_promote_backup_2026-10-09_pagerange_audit` (DB + the CSV before the edits).
