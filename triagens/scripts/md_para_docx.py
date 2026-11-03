#!/usr/bin/env python3
"""Converte um subconjunto de Markdown em .docx (python-docx).

Suporta: # ## ### ####, paragrafos, - bullets, 1. listas numeradas,
tabelas com pipes, **negrito** inline, --- (separador) e [ ]/checkbox.
"""
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Calibri"
BASE_SIZE = Pt(11)


def add_page_number_footer(section, text):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text + " — página ")
    run.font.size = Pt(8)
    run.font.name = FONT
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    p._p.append(fld)


def add_runs(paragraph, text):
    """Interpreta **negrito** preservando o restante."""
    for i, chunk in enumerate(re.split(r"(\*\*[^*]+\*\*)", text)):
        if not chunk:
            continue
        bold = chunk.startswith("**") and chunk.endswith("**")
        run = paragraph.add_run(chunk[2:-2] if bold else chunk)
        run.bold = bold
        run.font.name = FONT
        run.font.size = BASE_SIZE


def emit_table(doc, rows):
    header, body = rows[0], rows[1:]
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    for i, value in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = ""
        add_runs(cell.paragraphs[0], value)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for row in body:
        cells = table.add_row().cells
        for i, value in enumerate(row[: len(header)]):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], value)
    doc.add_paragraph()


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(src, dst):
    with open(src, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = BASE_SIZE
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21)
    sec.top_margin, sec.bottom_margin = Cm(3), Cm(2)
    sec.left_margin, sec.right_margin = Cm(3), Cm(2)
    add_page_number_footer(sec, "Triagem de Infodemia SVI-AC nº 01/2026 — miocardite/pericardite e vacina COVID-19")

    i, in_table = 0, False
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = split_row(lines[i])
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in row):
                    block.append(row)
                i += 1
            if block:
                emit_table(doc, block)
            continue

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(10)
            pPr = p._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "999999")
            borders.append(bottom)
            pPr.append(borders)
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), m.group(2)
            if level == 1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(text)
                run.bold = True
                run.font.name = FONT
                run.font.size = Pt(16)
                run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
            elif level == 2:
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.bold = True
                run.font.name = FONT
                run.font.size = Pt(13)
                run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
                p.paragraph_format.space_before = Pt(14)
            elif level == 3:
                p = doc.add_paragraph()
                run = p.add_run(text)
                run.bold = True
                run.font.name = FONT
                run.font.size = Pt(11.5)
                run.font.color.rgb = RGBColor(0x9B, 0x2D, 0x1F)
                p.paragraph_format.space_before = Pt(10)
            else:
                p = doc.add_paragraph()
                add_runs(p, text)
                for run in p.runs:
                    run.bold = True
            i += 1
            continue

        if stripped.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            add_runs(p, stripped[2:])
            i += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_after = Pt(3)
            add_runs(p, stripped)
            i += 1
            continue

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, stripped)
        i += 1

    doc.save(dst)
    print("ok:", dst)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
