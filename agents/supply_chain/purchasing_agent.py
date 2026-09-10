"""
purchasing_agent.py — Agent 2: Purchasing & PO Agent
Drafts a Purchase Order via the ERP MCP server, then pauses
for Human-in-the-Loop approval before proceeding.
"""

import asyncio
import os
import sys

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")

ERP_SERVER = os.path.join(MCP_DIR, "erp_server.py")


# ------------------------------------------------------------------
# Agent 2 — Main function
# ------------------------------------------------------------------

async def run_purchasing_agent(
    supplier_id: int,
    supplier_name: str,
    requirement_id: int,
    qty: float,
    total_value: float,
    auto_approve: bool = False,
    approved_by: str = "Human Manager"
) -> dict | None:
    """
    Draft a Purchase Order and wait for human approval.

    Args:
        supplier_id:     ID of the chosen supplier.
        supplier_name:   Display name (for human-readable summary).
        requirement_id:  ID from production_plan table.
        qty:             Quantity to order.
        total_value:     Total cost of the order.
        auto_approve:    If True, skips human input (for pipeline testing).
        approved_by:     Name to record in the PO on approval.

    Returns:
        dict with po_id and status='approved', or None if rejected.
    """
    from fastmcp import Client

    print(f"\n[Agent 2 - Purchasing] Drafting Purchase Order...")

    # ------------------------------------------------------------------
    # Step 1: Draft the PO via ERP MCP server
    # ------------------------------------------------------------------
    async with Client(ERP_SERVER) as erp:
        draft_result = await erp.call_tool(
            "draft_po",
            {
                "supplier_id":    supplier_id,
                "requirement_id": requirement_id,
                "qty":            qty,
                "total_value":    total_value,
            }
        )

    po_data = draft_result.data if hasattr(draft_result, "data") else draft_result
    if isinstance(po_data, dict) and "result" in po_data:
        po_data = po_data["result"]

    if "error" in po_data:
        print(f"  [Agent 2] Error drafting PO: {po_data['error']}")
        return None

    po_id = po_data["po_id"]

    # ------------------------------------------------------------------
    # Step 2: Human-in-the-Loop gate
    # ------------------------------------------------------------------
    print(f"""
  +==============================================+
  |       PURCHASE ORDER - AWAITING APPROVAL     |
  +==============================================+
  |  PO ID      : #{po_id:<36}|
  |  Supplier   : {supplier_name:<36}|
  |  Qty        : {str(qty):<36}|
  |  Total Cost : LKR {str(f'{total_value:,.2f}'):<33}|
  |  Status     : Pending Approval               |
  +==============================================+""")

    if auto_approve:
        decision = "approve"
        print(f"  [Auto-approve mode] Decision: approve")
    else:
        decision = input(
            "\n  Type 'approve' to proceed or 'reject' to cancel: "
        ).strip().lower()

    # ------------------------------------------------------------------
    # Step 3a: Approved → call approve_po
    # ------------------------------------------------------------------
    if decision == "approve":
        async with Client(ERP_SERVER) as erp:
            approve_result = await erp.call_tool(
                "approve_po",
                {"po_id": po_id, "approved_by": approved_by}
            )

        approved = approve_result.data if hasattr(approve_result, "data") else approve_result
        if isinstance(approved, dict) and "result" in approved:
            approved = approved["result"]

        print(f"\n  [Agent 2] [OK] PO #{po_id} approved by {approved_by}.")
        print(f"  Handing off to Freight Booking Agent...")

        return {
            "po_id":       po_id,
            "status":      "approved",
            "approved_by": approved_by,
            "supplier_id": supplier_id,
            "qty":         qty,
        }

    # ------------------------------------------------------------------
    # Step 3b: Rejected
    # ------------------------------------------------------------------
    else:
        print(f"\n  [Agent 2] [X] PO #{po_id} rejected. Pipeline stopped.")
        return None


if __name__ == "__main__":
    result = asyncio.run(
        run_purchasing_agent(
            supplier_id=4,
            supplier_name="EcoWeave Bangladesh",
            requirement_id=2,
            qty=300.0,
            total_value=78000.0,
            auto_approve=False
        )
    )
    print("\n[Agent 2 Result]:", result)
