"""Extract text content from the official template and current thesis DOCX files."""
import os
from docx import Document

OUT = os.path.join(os.path.dirname(__file__), "extracted")

def extract(path, name):
    doc = Document(path)
    lines = []
    # Walk body elements in order to capture tables too
    from docx.document import Document as _Doc
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.ns import qn

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            p = Paragraph(child, doc)
            style = p.style.name if p.style else ""
            txt = p.text.strip()
            if txt:
                lines.append(f"[{style}] {txt}")
        elif child.tag == qn('w:tbl'):
            t = Table(child, doc)
            lines.append("[TABLE START]")
            for row in t.rows:
                cells = [c.text.strip().replace("\n", " / ") for c in row.cells]
                lines.append(" | ".join(cells))
            lines.append("[TABLE END]")
        elif child.tag == qn('w:sectPr'):
            pass

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Extracted {name}: {len(lines)} lines -> {os.path.join(OUT, name + '.txt')}")

extract(r"C:\Users\Digilians\Desktop\AgeixAISOC\doc\Digilians 9 Months Diploma Cybersecurity Project_2026 (1).docx", "template")
extract(r"C:\Users\Digilians\Desktop\AgeixAISOC\doc\AgeixAISOC_Thesis.docx", "thesis")