"""Build the request documents sent to the researcher at RGIA, straight from
`docs/rgia_request_log.csv` (the tracker's log, the single source of truth).

Two shapes:
  * a batch request   -- фонд/опись, дело, количество листов, ссылка
  * a follow-up list  -- adds a статус column and highlights the дела that
                         have been requested but not yet received

Both are written as .csv (utf-8-sig, so Excel reads the Cyrillic), .xlsx
(clickable links, frozen header, autofilter) and .docx (A4, repeating header
row). Output goes to outputs/rgia_catalogue/ -- gitignored and disposable,
which is the point: the log is tracked, these regenerate from it.

python-docx is not a project dependency; run this with uv's --with flag:

    uv run --with python-docx python pipeline/rgia_build_request_docs.py --batch 2
    uv run --with python-docx python pipeline/rgia_build_request_docs.py --batch 1 --status
    uv run --with python-docx python pipeline/rgia_build_request_docs.py --all
"""
from __future__ import annotations

import argparse, csv, re, sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
except ModuleNotFoundError:
    raise SystemExit("python-docx missing -- run with:\n"
                     "  uv run --with python-docx python pipeline/rgia_build_request_docs.py ...")
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

LOG = Path("docs/rgia_request_log.csv")
OUT = Path("outputs/rgia_catalogue")
HDR_FILL, WAIT_FILL, WAIT_TEXT = "E7E6E6", "FFF2CC", "9C5700"
WAITING = "ОЖИДАЕТСЯ"

TITLES = {
    "1": "«Ежегодник» (издание и редакция), балет «Волшебное зеркало», музыка балета",
    "2": "«Ежегодник императорских театров» (материалы статей, списки рисунков)",
    "3": "балет (труппа, постановки, художники)",
    "4": "«Ежегодник» — пробные оттиски рисунков",
}


def delo_no(s: str) -> int:
    return int(re.match(r"Д\.\s*(\d+)", s).group(1))


def ru_date(d: str) -> str:
    y, m, dd = d.split("-"); return f"{dd}.{m}.{y}"


def rows_for(batch: str) -> list[dict]:
    rows = [r for r in csv.DictReader(open(LOG, encoding="utf-8")) if r["batch"] == batch]
    if not rows: raise SystemExit(f"no дела assigned to batch {batch} in {LOG}")
    return sorted(rows, key=lambda r: delo_no(r["дело"]))


def build_table(rows: list[dict], status: bool):
    if status:
        head = ["фонд/опись", "дело", "статус", "ссылка"]
        body = [[r["фонд/опись"], r["дело"],
                 f"получено {ru_date(r['date_received'])}" if r["date_received"] else WAITING,
                 r["ссылка"]] for r in rows]
    else:
        head = ["фонд/опись", "дело", "количество листов", "ссылка"]
        body = [[r["фонд/опись"], r["дело"], r["количество листов"], r["ссылка"]] for r in rows]
    return head, body


def write_xlsx(path: Path, head, body, status: bool):
    wb = Workbook(); ws = wb.active; ws.title = "Дела"
    ws.append(head)
    for b in body: ws.append(b)
    thin = Side(style="thin", color="BFBFBF")
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor=HDR_FILL)
        c.alignment = Alignment(vertical="center"); c.border = Border(bottom=thin)
    for i, b in enumerate(body, start=2):
        link = ws.cell(row=i, column=4)
        link.hyperlink = b[3]; link.font = Font(color="0563C1", underline="single")
        ws.cell(row=i, column=3).alignment = Alignment(horizontal="center")
        if status and b[2] == WAITING:
            for col in range(1, 5):
                ws.cell(row=i, column=col).fill = PatternFill("solid", fgColor=WAIT_FILL)
            ws.cell(row=i, column=3).font = Font(bold=True, color=WAIT_TEXT)
    for col, w in zip("ABCD", (16, 12, 22 if status else 18, 42)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"; ws.auto_filter.ref = f"A1:D{len(body)+1}"
    wb.save(path)


def _link(par, url):
    rid = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), rid)
    r = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
    for tag, val in (("w:color", "0563C1"), ("w:u", "single"), ("w:sz", "18")):
        e = OxmlElement(tag); e.set(qn("w:val"), val); rpr.append(e)
    r.append(rpr); t = OxmlElement("w:t"); t.text = url; r.append(t)
    h.append(r); par._p.append(h)


def _shade(cell, colour):
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), colour)
    cell._tc.get_or_add_tcPr().append(s)


def write_docx(path: Path, head, body, title: str, note: str, status: bool):
    doc = Document(); sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(2))
    st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    h = doc.add_paragraph(); h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run(title); r.bold = True; r.font.size = Pt(14)
    n = doc.add_paragraph(); n.alignment = WD_ALIGN_PARAGRAPH.CENTER
    n.add_run(note).font.size = Pt(11)

    widths = (Cm(3.3), Cm(2.3), Cm(3.6 if status else 2.6), Cm(7.8 if status else 8.8))
    tbl = doc.add_table(rows=1, cols=4); tbl.style = "Table Grid"
    for cell, text, w in zip(tbl.rows[0].cells, head, widths):
        cell.width = w; cell.text = ""
        cell.paragraphs[0].add_run(text).bold = True; _shade(cell, HDR_FILL)
    trPr = tbl.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for b in body:
        cells = tbl.add_row().cells
        waiting = status and b[2] == WAITING
        for cell, w in zip(cells, widths):
            cell.width = w
            if waiting: _shade(cell, WAIT_FILL)
        for idx, val in enumerate(b):
            p = cells[idx].paragraphs[0]
            if idx == 3: _link(p, val); continue
            if idx == 2: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(val); run.font.size = Pt(10)
            if waiting and idx in (1, 2):
                run.bold = True; run.font.color.rgb = RGBColor(0x9C, 0x57, 0x00)
    doc.save(path)


def build(batch: str, status: bool, title: str | None) -> None:
    rows = rows_for(batch)
    head, body = build_table(rows, status)
    OUT.mkdir(parents=True, exist_ok=True)
    base = OUT / (f"rgia_batch{batch}_status" if status else f"rgia_batch{batch}")
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(body)
    subject = title or TITLES.get(batch, "")
    if status:
        sent = {r["date_requested"] for r in rows if r["date_requested"]}
        got = [r for r in rows if r["date_received"]]
        when = f" (от {ru_date(sorted(sent)[0])})" if sent else ""
        doc_title = f"РГИА, Ф. 497, Оп. 18 — заказ {batch}{when}: что получено и что ожидается"
        dates = sorted({ru_date(r["date_received"]) for r in got})
        note = (f"Всего в заказе: {len(rows)} дел. Получено: {len(got)}"
                + (f" ({', '.join(dates)})" if dates else "")
                + f". Ожидается: {len(rows)-len(got)} — выделены ниже.")
    else:
        doc_title = f"РГИА, Ф. 497, Оп. 18 — заказ {batch}" + (f": {subject}" if subject else "")
        note = f"Список дел ({len(rows)})"
    write_xlsx(base.with_suffix(".xlsx"), head, body, status)
    write_docx(base.with_suffix(".docx"), head, body, doc_title, note, status)
    extra = f", {sum(1 for b in body if b[2] == WAITING)} ожидается" if status else ""
    print(f"batch {batch}{' (status)' if status else ''}: {len(rows)} дела{extra} -> {base}.csv/.xlsx/.docx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch")
    ap.add_argument("--status", action="store_true",
                    help="follow-up list: статус column, outstanding дела highlighted")
    ap.add_argument("--title", help="override the subject line in the .docx heading")
    ap.add_argument("--all", action="store_true", help="rebuild every assigned batch")
    a = ap.parse_args()
    if a.all:
        batches = sorted({r["batch"] for r in csv.DictReader(open(LOG, encoding="utf-8")) if r["batch"]},
                         key=int)
        for b in batches: build(b, False, None)
        return
    if not a.batch: raise SystemExit("give --batch N (optionally --status), or --all")
    build(a.batch, a.status, a.title)


if __name__ == "__main__":
    main()
