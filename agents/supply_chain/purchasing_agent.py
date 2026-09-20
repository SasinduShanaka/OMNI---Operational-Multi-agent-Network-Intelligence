"""
purchasing_agent.py — Agent 2: Purchasing & PO Agent
Drafts a Purchase Order via the ERP MCP server, then pauses
for Human-in-the-Loop approval before proceeding.
"""

import asyncio
import os
import sys
import json
try:
    from langchain_groq import ChatGroq
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
except ImportError:
    ChatGroq = None

    def tool(func):
        return func

    HumanMessage = None

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")
ERP_SERVER = os.path.join(MCP_DIR, "erp_server.py")


def _draft_po_in_sqlite(
    supplier_id: int,
    requirement_id: int,
    qty: float,
    total_value: float,
    po_details: dict | None = None,
) -> dict:
    from datetime import date, timedelta

    sqlite_dir = os.path.join(BASE_DIR, "database", "supply_chain", "sqlite_db")
    if sqlite_dir not in sys.path:
        sys.path.insert(0, sqlite_dir)
    from db import ensure_erp_db_ready, get_erp_db_connection

    ensure_erp_db_ready()
    conn = get_erp_db_connection()
    try:
        expected_delivery = (date.today() + timedelta(days=14)).isoformat()
        po_details_json = json.dumps(po_details or {})
        cur = conn.execute(
            """
            INSERT INTO purchase_orders
                (supplier_id, requirement_id, qty, total_value, order_date, expected_delivery_date, status, approved_by, po_details)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', NULL, ?)
            """,
            (supplier_id, requirement_id, qty, total_value, date.today().isoformat(), expected_delivery, po_details_json),
        )
        conn.commit()
        return {
            "po_id": cur.lastrowid,
            "supplier_id": supplier_id,
            "requirement_id": requirement_id,
            "qty": qty,
            "total_value": total_value,
            "status": "draft",
            "expected_delivery_date": expected_delivery,
        }
    finally:
        conn.close()


def _approve_po_in_sqlite(po_id: int, approved_by: str) -> dict:
    sqlite_dir = os.path.join(BASE_DIR, "database", "supply_chain", "sqlite_db")
    if sqlite_dir not in sys.path:
        sys.path.insert(0, sqlite_dir)
    from db import ensure_erp_db_ready, get_erp_db_connection

    ensure_erp_db_ready()
    conn = get_erp_db_connection()
    try:
        conn.execute(
            "UPDATE purchase_orders SET status = 'approved', approved_by = ? WHERE po_id = ?",
            (approved_by, po_id),
        )
        conn.commit()
        return {"po_id": po_id, "status": "approved", "approved_by": approved_by}
    finally:
        conn.close()


# ------------------------------------------------------------------
# LangChain Tool wrapping MCP
# ------------------------------------------------------------------
@tool
async def draft_po_tool(supplier_id: int, requirement_id: int, qty: float, total_value: float) -> str:
    """Drafts a Purchase Order in the ERP system for a given supplier and requirement."""
    from fastmcp import Client
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
        
    return json.dumps(po_data)


# ------------------------------------------------------------------
# Agent 2 — Main function
# ------------------------------------------------------------------

async def run_purchasing_agent(
    supplier_id: int,
    supplier_name: str,
    requirement_id: int,
    qty: float,
    total_value: float,
    draft_only: bool = False,
    auto_approve: bool = False,
    approved_by: str = "Human Manager",
    po_details: dict | None = None,
) -> dict | None:
    """
    Draft a Purchase Order using an LLM and wait for human approval.
    """
    print(f"\n[Agent 2 - Purchasing] LLM deciding actions to draft Purchase Order...")

    if ChatGroq is None:
        print("  [Agent 2] LangChain Groq unavailable; drafting PO deterministically.")
        try:
            from fastmcp import Client
            async with Client(ERP_SERVER) as erp:
                draft_result = await erp.call_tool(
                    "draft_po",
                    {
                        "supplier_id": supplier_id,
                        "requirement_id": requirement_id,
                        "qty": qty,
                        "total_value": total_value,
                    }
                )
            po_data = draft_result.data if hasattr(draft_result, "data") else draft_result
            if isinstance(po_data, dict) and "result" in po_data:
                po_data = po_data["result"]
        except Exception as error:
            print(f"  [Agent 2] MCP unavailable ({error}); drafting PO in SQLite directly.")
            po_data = _draft_po_in_sqlite(supplier_id, requirement_id, qty, total_value, po_details)
    else:
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
        llm_with_tools = llm.bind_tools([draft_po_tool])

        prompt = f"Please draft a purchase order for supplier_id {supplier_id} (name: {supplier_name}) for requirement_id {requirement_id} with quantity {qty} and total cost {total_value}."

        # Step 1: LLM decides to call tool
        msg = await llm_with_tools.ainvoke([HumanMessage(content=prompt)])

        po_data = None

        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            print(f"  [Agent 2] LLM called tool: {tool_call['name']} with args {tool_call['args']}")

            # Step 2: Execute tool
            tool_result = await draft_po_tool.ainvoke(tool_call['args'])
            po_data = json.loads(tool_result)

    if not po_data or "error" in po_data:
        print(f"  [Agent 2] Error drafting PO: {po_data.get('error', 'No data returned by LLM tool')}")
        return None

    po_id = po_data["po_id"]

    # ------------------------------------------------------------------
    # Step 3: Human-in-the-Loop gate
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

    if draft_only:
        print("  [Draft-only mode] PO is waiting for human approval.")
        return {
            "po_id":       po_id,
            "status":      "pending_approval",
            "approved_by": None,
            "supplier_id": supplier_id,
            "qty":         qty,
            "total_value": total_value,
        }

    if auto_approve:
        decision = "approve"
        print(f"  [Auto-approve mode] Decision: approve")
    else:
        decision = input(
            "\n  Type 'approve' to proceed or 'reject' to cancel: "
        ).strip().lower()

    # ------------------------------------------------------------------
    # Step 4a: Approved → call approve_po
    # ------------------------------------------------------------------
    if decision == "approve":
        try:
            from fastmcp import Client
            async with Client(ERP_SERVER) as erp:
                approve_result = await erp.call_tool(
                    "approve_po",
                    {"po_id": po_id, "approved_by": approved_by}
                )

            approved = approve_result.data if hasattr(approve_result, "data") else approve_result
            if isinstance(approved, dict) and "result" in approved:
                approved = approved["result"]
        except Exception as error:
            print(f"  [Agent 2] MCP unavailable ({error}); approving PO in SQLite directly.")
            approved = _approve_po_in_sqlite(po_id, approved_by)

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
    # Step 4b: Rejected
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
