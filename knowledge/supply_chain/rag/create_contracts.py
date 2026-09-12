"""
create_contracts.py
Generates 3 mock supplier PDF contracts for the RAG compliance pipeline.
Run once: python knowledge/rag/create_contracts.py
"""

import os
from fpdf import FPDF, XPos, YPos

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "contracts")
os.makedirs(CONTRACTS_DIR, exist_ok=True)


def make_pdf(filename: str, title: str, body: str):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    for line in body.strip().split("\n"):
        # Replace unicode characters with ASCII equivalents
        line = (line.strip()
                .replace("\u2014", "-")
                .replace("\u2013", "-")
                .replace("\u2019", "'")
                .replace("\u201c", '"')
                .replace("\u201d", '"'))
        if line == "":
            pdf.ln(3)   # blank line spacer
        else:
            pdf.multi_cell(page_w, 6, line)
    pdf.output(os.path.join(CONTRACTS_DIR, filename))
    print(f"Created: {filename}")


# ------------------------------------------------------------------
# Contract 1 -- EcoWeave Bangladesh (COMPLIANT)
# ------------------------------------------------------------------
make_pdf(
    "ecoweave_contract.pdf",
    "Supplier Agreement - EcoWeave Bangladesh",
    """
    Supplier:        EcoWeave Bangladesh Ltd.
    Country:         Bangladesh
    Category:        Fabric Mill
    Contract Date:   2024-01-15
    Valid Until:     2027-01-15

    CERTIFICATIONS AND STANDARDS
    -----------------------------
    This supplier holds the following active certifications:

    1. GOTS Certified (Global Organic Textile Standard) - Certificate GOTS-BD-2024-4471
       Confirms all cotton fabric is Organic Cotton Certified.

    2. Child-Labor Free Certification - Issued by Fair Labor Association (FLA)
       Audited annually. Zero tolerance for underage workers.

    3. Fair Trade Certified - FLO-CERT License FLO-BD-8821
       Workers receive fair wages above national minimum.

    4. ISO 9001:2015 Quality Management - Certificate ISO-BD-9001-3302

    MATERIAL SOURCING
    -----------------
    All raw cotton sourced exclusively from organic farms certified under
    the National Organic Program (NOP). No synthetic pesticides or GMO seeds used.

    ENVIRONMENTAL COMPLIANCE
    ------------------------
    EcoWeave operates under strict environmental standards:
    - Zero liquid discharge (ZLD) water treatment plant on premises.
    - Renewable energy (solar) accounts for 40% of factory power consumption.
    - Carbon neutral operations certified by Carbon Trust.

    ETHICAL SOURCING POLICY
    -----------------------
    EcoWeave Bangladesh is committed to ethical sourcing and human rights.
    All employees work in safe, humane conditions. Regular third-party audits
    conducted by Bureau Veritas.

    AGREED TERMS
    ------------
    Lead Time:    18 days
    Payment:      Net 30
    Incoterms:    FOB Chittagong
    """
)

# ------------------------------------------------------------------
# Contract 2 -- Textiles Lanka (COMPLIANT)
# ------------------------------------------------------------------
make_pdf(
    "textiles_lanka_contract.pdf",
    "Supplier Agreement - Textiles Lanka",
    """
    Supplier:        Textiles Lanka (Pvt) Ltd.
    Country:         Sri Lanka
    Category:        Fabric Mill
    Contract Date:   2023-06-01
    Valid Until:     2026-06-01

    CERTIFICATIONS AND STANDARDS
    -----------------------------
    1. Organic Cotton Certified - Certified under USDA National Organic Program.
       All fabric lines are produced from certified organic cotton feedstock.

    2. Child-Labor Free Certification - Verified by Social Accountability International (SA8000).
       No workers under the age of 15 are employed. Audit completed March 2024.

    3. ISO 9001:2015 Certified - Quality Management System.

    4. Oeko-Tex Standard 100 Certified - Ensures textiles are free from harmful substances.

    MATERIAL SOURCING
    -----------------
    Raw materials sourced from certified organic farms in Sri Lanka and India.
    Supplier maintains full traceability from farm to finished fabric.

    ETHICAL SOURCING POLICY
    -----------------------
    Textiles Lanka maintains a strict ethical sourcing policy. All subcontractors
    are vetted and must comply with SA8000 labor standards.

    AGREED TERMS
    ------------
    Lead Time:    21 days
    Payment:      Net 45
    Incoterms:    CIF Colombo
    """
)

# ------------------------------------------------------------------
# Contract 3 -- Zipper King China (NON-COMPLIANT -- intentional)
# ------------------------------------------------------------------
make_pdf(
    "zipper_king_contract.pdf",
    "Supplier Agreement - Zipper King China",
    """
    Supplier:        Zipper King Manufacturing Co. Ltd.
    Country:         China
    Category:        Trim Vendor (Zippers, Buttons)
    Contract Date:   2024-03-10
    Valid Until:     2027-03-10

    PRODUCT SPECIFICATION
    ----------------------
    Zipper King specializes in standard production of metal and nylon zippers,
    buttons, and trim accessories for garment manufacturers.

    Products are manufactured using standard industrial processes.
    Non-organic materials are used in all product lines.

    QUALITY STANDARDS
    -----------------
    Products meet standard ISO dimensional tolerances.
    Internal quality control checks performed on random sample basis.

    AGREED TERMS
    ------------
    Lead Time:    10 days
    Payment:      Net 15
    Incoterms:    EXW Shanghai

    NOTE: This supplier does not currently hold organic certification,
    Fair Trade certification, or child-labor auditing certification.
    Products are competitively priced for standard (non-ethical-label) supply chains.
    """
)

print("\nAll 3 contracts generated in knowledge/contracts/")
