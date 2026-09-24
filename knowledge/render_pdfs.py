"""
render_pdfs.py
Render the markdown knowledge documents as PDFs.

The markdown stays the source of truth — it carries the front matter
the retriever uses for scoping — and the PDF is the document the
index actually reads, so retrieval runs on PDF text the same way the
supplier contract corpus does.

Each render also records which page every section starts on, so a
retrieved passage can be cited down to the page.

    python knowledge/render_pdfs.py
    python knowledge/render_pdfs.py market_context
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fpdf import FPDF, XPos, YPos

from knowledge.retriever import CORPORA, parse_document, split_into_sections


# fpdf core fonts are latin-1; swap the typographic characters the
# documents use for ASCII equivalents before writing.
REPLACEMENTS = {
    "—": "-", "–": "-", "’": "'", "‘": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
    "≥": ">=", "≤": "<=",
}


def ascii_safe(text: str) -> str:
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    return text.encode("latin-1", "replace").decode("latin-1")


def render_table(pdf: FPDF, rows: list[str]) -> None:
    """
    Markdown pipe tables are written as aligned text rather than drawn
    cells: it keeps the extracted text readable, which is what the
    embedding sees.
    """

    parsed = []

    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue                      # separator row
        parsed.append(cells)

    if not parsed:
        return

    widths = [max(len(row[i]) if i < len(row) else 0 for row in parsed)
              for i in range(max(len(row) for row in parsed))]

    pdf.set_font("Courier", "", 8.5)

    for index, row in enumerate(parsed):
        line = "  ".join(
            (row[i] if i < len(row) else "").ljust(widths[i])
            for i in range(len(widths))
        )
        pdf.multi_cell(0, 4.6, ascii_safe(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if index == 0:
            pdf.set_font("Courier", "", 8.5)

    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)


def render_document(md_path: Path, out_path: Path) -> dict:
    """
    Write one PDF and return {section_title: page_number}.
    """

    parsed = parse_document(md_path)
    front = parsed["front_matter"]
    sections = split_into_sections(parsed["body"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    # ---- document header -------------------------------------------------
    pdf.set_font("Helvetica", "B", 15)
    pdf.multi_cell(0, 8, ascii_safe(front.get("title", md_path.stem)),
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(100, 100, 100)

    meta_bits = [f"Document {front.get('doc_id', md_path.stem)}"]
    for label, key in (("Type", "doc_type"), ("Effective", "effective_date"),
                       ("Buyer", "buyer"), ("Applies to", "skus")):
        if front.get(key):
            meta_bits.append(f"{label}: {front[key]}")

    pdf.multi_cell(0, 4.6, ascii_safe(" | ".join(meta_bits)),
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # ---- body ------------------------------------------------------------
    page_map = {}

    for title, text in sections:

        pdf.set_font("Helvetica", "B", 11)

        # Keep a heading with at least a little of its body.
        if pdf.get_y() > pdf.h - 45:
            pdf.add_page()

        page_map[title] = pdf.page_no()

        pdf.multi_cell(0, 6.5, ascii_safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)

        table_rows = []

        for line in text.splitlines():

            stripped = line.strip()

            if stripped.startswith("|"):
                table_rows.append(stripped)
                continue

            if table_rows:
                render_table(pdf, table_rows)
                table_rows = []

            if not stripped:
                pdf.ln(2)
                continue

            pdf.multi_cell(0, 5.2, ascii_safe(stripped),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if table_rows:
            render_table(pdf, table_rows)

        pdf.ln(3)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))

    return page_map


def render_corpus(corpus: str, verbose: bool = True) -> dict:

    config = CORPORA[corpus]
    source_dir = config["path"]
    pdf_dir = source_dir / "pdf"

    manifest = {}

    for md_path in sorted(source_dir.glob("*.md")):

        out_path = pdf_dir / f"{md_path.stem}.pdf"
        page_map = render_document(md_path, out_path)

        manifest[md_path.name] = {
            "pdf": out_path.name,
            "pages": page_map,
        }

        if verbose:
            print(f"  {md_path.name} -> pdf/{out_path.name} "
                  f"({len(page_map)} sections)")

    (pdf_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


def main():

    requested = sys.argv[1:] or list(CORPORA)

    for corpus in requested:
        if corpus not in CORPORA:
            print(f"Unknown corpus '{corpus}'. Available: {', '.join(CORPORA)}")
            return 1
        print(f"\nRendering '{corpus}'")
        render_corpus(corpus)

    print("\nRebuild the index so it reads the new PDFs:")
    print("  python knowledge/build_index.py")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
