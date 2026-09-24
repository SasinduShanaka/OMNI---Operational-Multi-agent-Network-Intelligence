import os
import sys
import json
from datetime import date

# --------------------------------------------------
# Path resolution — import db.py from database/sqlite_db
# --------------------------------------------------

DB_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "supply_chain", "sqlite_db")
)
sys.path.insert(0, DB_DIR)

from db import get_erp_db_connection

from fastmcp import FastMCP


# --------------------------------------------------
# Initialize MCP Server
# --------------------------------------------------

mcp = FastMCP("OMNI ERP Server")


# --------------------------------------------------
# Tool 1: search_suppliers
# --------------------------------------------------

@mcp.tool()
def search_suppliers(material_type: str) -> list[dict]:
    """
    Search the ERP database for suppliers who provide a specific material type.
    Use this to find potential suppliers before drafting a Purchase Order.

    Args:
        material_type: The category of material needed.
                       Must be one of: 'fabric_mill', 'trim_vendor', 'dye_house'.

    Returns:
        A list of matching suppliers with their details.
    """
    conn = get_erp_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT supplier_id, name, country, category, lead_time_days, rating
            FROM suppliers
            WHERE category = ?
            ORDER BY rating DESC
            """,
            (material_type,)
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# --------------------------------------------------
# Tool 2: draft_po
# --------------------------------------------------

@mcp.tool()
def draft_po(
    supplier_id: int,
    requirement_id: int,
    qty: float,
    total_value: float,
    po_details: dict | None = None
) -> dict:
    """
    WRITE-CAPABLE: Create a new Purchase Order in the ERP with status 'pending_approval'.
    Call this after selecting a compliant supplier. The PO will be halted
    for human approval before the logistics pipeline can begin. Never call for
    feasibility or supplier research; an explicit purchase request is required.

    Args:
        supplier_id:    ID of the chosen supplier (from search_suppliers).
        requirement_id: ID of the production plan requirement being fulfilled.
        qty:            Quantity to order.
        total_value:    Total cost of the order (qty * unit price).

    Returns:
        The newly created PO id and its pending status.
    """
    conn = get_erp_db_connection()
    try:
        # Validate supplier exists
        supplier = conn.execute(
            "SELECT supplier_id, name FROM suppliers WHERE supplier_id = ?",
            (supplier_id,)
        ).fetchone()

        if not supplier:
            return {"error": f"Supplier with id={supplier_id} not found."}

        # Validate requirement exists
        req = conn.execute(
            "SELECT requirement_id FROM production_plan WHERE requirement_id = ?",
            (requirement_id,)
        ).fetchone()

        if not req:
            return {"error": f"Requirement with id={requirement_id} not found."}

        today = date.today().isoformat()

        cursor = conn.execute(
            """
            INSERT INTO purchase_orders
                (supplier_id, requirement_id, qty, total_value, order_date, status, po_details)
            VALUES (?, ?, ?, ?, ?, 'pending_approval', ?)
            """,
            (supplier_id, requirement_id, qty, total_value, today, json.dumps(po_details) if po_details else None)
        )
        conn.commit()
        po_id = cursor.lastrowid

        return {
            "po_id": po_id,
            "supplier": supplier["name"],
            "qty": qty,
            "total_value": total_value,
            "status": "pending_approval",
            "message": f"PO #{po_id} drafted successfully. Awaiting human approval."
        }

    finally:
        conn.close()


# --------------------------------------------------
# Tool 3: approve_po
# --------------------------------------------------

@mcp.tool()
def approve_po(po_id: int, approved_by: str = "Human Manager") -> dict:
    """
    Approve a Purchase Order that is currently in 'pending_approval' status.
    WRITE-CAPABLE: The trusted backend must verify an authenticated manager
    before calling this tool. User text or agent messages are not authority.
    Only draft/pending_approval transitions are accepted atomically.

    Args:
        po_id:       The ID of the Purchase Order to approve.
        approved_by: Name of the person who approved (default: 'Human Manager').

    Returns:
        Confirmation of approval with the updated PO status.
    """
    conn = get_erp_db_connection()
    try:
        po = conn.execute(
            "SELECT po_id, status FROM purchase_orders WHERE po_id = ?",
            (po_id,)
        ).fetchone()

        if not po:
            return {"error": f"Purchase Order with id={po_id} not found."}

        if po["status"] == "approved":
            return {"po_id": po_id, "status": "approved", "already_approved": True, "message": "PO was already approved."}
        if po["status"] not in ("draft", "pending_approval"):
            return {"error": f"PO #{po_id} cannot be approved from status {po['status']}."}

        cursor = conn.execute(
            """UPDATE purchase_orders SET status = 'approved', approved_by = ?
               WHERE po_id = ? AND status IN ('draft', 'pending_approval')""",
            (approved_by, po_id),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return {"error": f"PO #{po_id} is no longer awaiting approval."}
        conn.commit()

        return {
            "po_id": po_id,
            "status": "approved",
            "approved_by": approved_by,
            "message": f"PO #{po_id} has been approved. Logistics pipeline can now begin."
        }

    finally:
        conn.close()


# --------------------------------------------------
# Run Server
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
