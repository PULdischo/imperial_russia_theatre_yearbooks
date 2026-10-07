# Administrators audit (issue #137), 2026-10-07

Scope: the 86 `administration_<season>_pNNN` pages of 1890-91..1909-10 (1,834 rows; 1910-11 was read in #135 and is untouched).
Method: two independent blind readers per page (PIL crops, never shown stored values) -> order-independent comparison with the stored rows -> a third blind
verifier on every disputed row (329 items) -> three-way adjudication (stored S / first read R1 / verifier V: V==S keeps, V==R1 applies, else manual).

Stages, in order (all scripts here, all re-runnable; `--write` applies):

| step | script | what it does |
|---|---|---|
| read | `PROMPT.md`, `bundles/`, `reader_reports/` | blind HEAD/ROW reports for all 86 pages |
| compare | `parse_reports.py`, `compare.py` | reader row <-> stored row pairing; classes SURNAME/NAME/CHARS/DATE/HOMOGLYPH/TITLE_IN_NAME/... |
| verify | `disputes.py`, `VERIFY_PROMPT.md`, `verify/` , `adjudicate.py` | 361 disputed rows -> 329 verified -> STORED_WRONG 247 / STORED_OK 63 / DISAGREE 15 / UNPAIRED 3 / MISSING_LINE 1 |
| content | `propose.py`, `apply_fixes.py`, `adm_common.py` | token-aligned field edits + manual rulings; 396 raw edits, 43 noble-title rows normalized, 7 note-only rows removed, 2 missing rows appended, 26 service-period reconciles |
| links | `relink_administrators.py` | person_link renumbered after the 7 removals; the 2 added rows seeded by canonical name |
| structure | `structure_check.py`, `structure_fix.py` | `institution` / `heading_path` rebuilt for every row (below) |

Rebuild after any raw edit: `bash docs/eval/rebuild_after_raw_edit.sh` (it passes `--page-headers` and `--printed-page-numbers`, which parse_and_validate silently needs).

## Structure convention (RG: "option 1", 2026-10-07)
- `institution` = the season's printed list title (`СПИСОКЪ личнаго состава театральнаго управленія.`), the same for every row of the season (it previously had 41 distinct values).
- `heading_path` = `<office> / <department> / <position as printed>`.
  - office = `Дирекція Императорскихъ театровъ` for the first lines of each list (officials over BOTH cities), until the first printed office heading;
    then `С.-Петербургская Контора Императорскихъ театровъ` / `Московская Контора Императорскихъ театровъ`, carried forward across page breaks (a continuation page has no office heading of its own).
  - department/position text comes from the blind readers' headings (stored chains had typos "Контроры/Контролю", truncated "X кл", and headings stuck above unrelated lists), carried across page breaks only when the page starts with no heading of its own.
  - a grade token ("VII кл") is NOT left in `heading_path`: the parser moves it to `service_class` (and now also drops the dangling " /" this left when the grade was a segment of its own; `pipeline/parse_and_validate.py` `_repair_heading_path_rank_class`).
- Rule applied to the readers' stacks: "Врачебная часть" (or the mis-levelled "Старшій врачъ VI кл") only stays above medical positions; chancery grade lists that follow the medical part are nested under "Канцелярскіе чиновники Конторы" only where that list is directly continuing.
- Result: 943 St-Petersburg rows, 758 Moscow, 133 Directorate. 193 St-Petersburg rows that the stored text had labelled Moscow (14 turn-over pages) are now St Petersburg.

Known judgment points: the "Техникъ при С.-Петербургской Конторѣ" line (6 seasons) is printed in the Directorate block before the first office heading, so it carries the Directorate root with its position text naming the SPb office. RG ruling (2026-10-07): in the raw layer these stay as printed (Directorate root, SPb office named only in the position text); any SPb attribution belongs in the research layer, not here. Readers' heading levels are not uniform across pages (a few lists sit at level 2 on one page and level 3 on another); the chain was not forced to a single hierarchy.

## Verification (after rebuild)
23,981 entries; live persons 3,135 / tombstones 3,217 (unchanged by the structure stage); receipts identical; 0 orphan links; 0 links to tombstoned persons; 0 entries without a link; 0 shift blocks; quality flags 566.
Backups: `outputs/full_run_pre_promote_backup_2026-10-07_administrators` (before the content stage) and `..._administrators_structure` (before the structure stage).
