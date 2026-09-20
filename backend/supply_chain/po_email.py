import json
import os
import sys


def _get_erp_connection():
    db_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "database",
            "supply_chain",
            "sqlite_db",
        )
    )
    if db_dir not in sys.path:
        sys.path.insert(0, db_dir)

    from db import ensure_erp_db_ready, get_erp_db_connection

    ensure_erp_db_ready()
    return get_erp_db_connection()


def build_po_email_data(po_id: int, approved_by: str = "Human Manager") -> tuple[dict | None, str]:
    conn = _get_erp_connection()
    try:
        row = conn.execute(
            """
            SELECT po.po_id, po.qty, po.total_value, po.order_date,
                   po.expected_delivery_date, po.approved_by, po.po_details,
                   s.name AS supplier_name, s.country, s.email, s.price_per_unit
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.po_id = ?
            """,
            (po_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None, f"PO #{po_id} not found."

    row_dict = dict(row)
    po_details = {}
    if row_dict.get("po_details"):
        try:
            po_details = json.loads(row_dict["po_details"])
        except Exception:
            po_details = {}

    supplier_email = row_dict.get("email") or ""
    po_data = {
        "po_id": row_dict["po_id"],
        "supplier_name": row_dict["supplier_name"] or "Supplier",
        "supplier_email": supplier_email,
        "country": row_dict["country"] or "",
        "qty": row_dict["qty"],
        "unit": po_details.get("unit", "units"),
        "total_value": row_dict["total_value"],
        "price_per_unit": row_dict["price_per_unit"] or 260.0,
        "order_date": row_dict["order_date"] or "",
        "expected_delivery_date": row_dict["expected_delivery_date"] or "",
        "approved_by": row_dict["approved_by"] or approved_by,
        "material_name": po_details.get("material_name", "Material"),
        "color_spec": po_details.get("color_spec", "-"),
        "dimensions": po_details.get("dimensions", {}),
        "compliance_keywords": po_details.get("compliance_keywords", []),
        "destination": po_details.get("destination", ""),
    }

    return po_data, supplier_email


def send_approved_po_email(po_id: int, approved_by: str = "Human Manager", notes: str = "") -> dict:
    po_data, supplier_email = build_po_email_data(po_id, approved_by)

    if not po_data:
        return {"sent": False, "error": supplier_email}

    if not supplier_email:
        return {"sent": False, "error": "No email on file for this supplier"}

    from backend.supply_chain.email_service import send_po_email

    return send_po_email(po_data, supplier_email, notes=notes)
