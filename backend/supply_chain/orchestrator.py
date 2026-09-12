"""
orchestrator.py
LangGraph pipeline that chains the 4 supply chain agents.

Run 1: sourcing → draft PO → pause (status=awaiting_approval)
Run 2: approve PO → freight booking → tracking → complete
"""

import asyncio
import os
import sys
import uuid

from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ------------------------------------------------------------------
# Path setup — project root
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from agents.supply_chain.sourcing_agent   import run_sourcing_agent
from agents.supply_chain.purchasing_agent import run_purchasing_agent
from agents.supply_chain.freight_agent    import run_freight_agent
from agents.supply_chain.tracking_agent   import run_tracking_agent


# ------------------------------------------------------------------
# State schema
# ------------------------------------------------------------------

class PipelineState(TypedDict, total=False):
    # Input
    material_type:       str
    requirement_id:      int
    qty:                 float
    total_value:         float
    compliance_keywords: list[str]
    origin:              str
    destination:         str
    approved_by:         str
    targeted_supplier:   str | None   # Scenario A: user named a specific supplier

    # Agent 1 output
    supplier:            dict | None

    # Agent 2 output
    po:                  dict | None

    # Agent 3 output
    shipment:            dict | None

    # Agent 4 output
    tracking:            dict | None

    # Pipeline control
    status:              str   # "running" | "awaiting_approval" | "completed" | "failed"
    error:               str | None


# ------------------------------------------------------------------
# Node: Sourcing (Agent 1)
# ------------------------------------------------------------------

async def node_sourcing(state: PipelineState) -> PipelineState:
    print("\n[Orchestrator] -> Node: Sourcing")
    targeted = state.get("targeted_supplier")
    try:
        supplier = await run_sourcing_agent(
            material_type=state["material_type"],
            requirement_id=state["requirement_id"],
            compliance_keywords=state.get("compliance_keywords", ["Organic Cotton", "Child-Labor Free"]),
            targeted_supplier=targeted,  # Scenario A: skip DB search if set
        )
        if not supplier:
            return {**state, "status": "failed", "error": "No compliant supplier found.", "supplier": None}
        return {**state, "supplier": supplier, "status": "running"}
    except Exception as e:
        return {**state, "status": "failed", "error": f"Sourcing error: {e}", "supplier": None}


# ------------------------------------------------------------------
# Node: Draft PO (Agent 2 — first half only)
# ------------------------------------------------------------------

async def node_draft_po(state: PipelineState) -> PipelineState:
    print("\n[Orchestrator] -> Node: Draft PO")
    try:
        po = await run_purchasing_agent(
            supplier_id=state["supplier"]["supplier_id"],
            supplier_name=state["supplier"]["supplier_name"],
            requirement_id=state["requirement_id"],
            qty=state["qty"],
            total_value=state["total_value"],
            auto_approve=True,          # Draft only — approval via API
            approved_by="__draft__"     # Sentinel: not yet approved
        )
        if not po:
            return {**state, "status": "failed", "error": "PO draft failed.", "po": None}

        # Override status back to pending — real approval comes via /approve endpoint
        return {**state, "po": {**po, "status": "pending_approval"}, "status": "awaiting_approval"}
    except Exception as e:
        return {**state, "status": "failed", "error": f"PO draft error: {e}", "po": None}


# ------------------------------------------------------------------
# Node: Approve PO + Freight + Tracking (Run 2)
# ------------------------------------------------------------------

async def node_approve_and_ship(state: PipelineState) -> PipelineState:
    print("\n[Orchestrator] -> Node: Approve + Freight + Tracking")
    try:
        from fastmcp import Client
        MCP_DIR = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")
        ERP_SERVER = os.path.join(MCP_DIR, "erp_server.py")

        po_id      = state["po"]["po_id"]
        approved_by = state.get("approved_by", "Human Manager")

        # Approve the PO via ERP MCP
        async with Client(ERP_SERVER) as erp:
            await erp.call_tool("approve_po", {"po_id": po_id, "approved_by": approved_by})

        approved_po = {**state["po"], "status": "approved", "approved_by": approved_by}

        # Freight booking (Agent 3)
        supplier     = state["supplier"]
        lead_time    = supplier.get("lead_time_days", 21)
        origin       = state.get("origin", f"{supplier.get('country', 'Unknown')}")
        destination  = state.get("destination", "Colombo, LK")

        shipment = await run_freight_agent(
            po_id=po_id,
            lead_time_days=lead_time,
            origin=origin,
            destination=destination
        )
        if not shipment:
            return {**state, "po": approved_po, "status": "failed", "error": "Freight booking failed."}

        # Tracking (Agent 4)
        tracking = await run_tracking_agent(
            shipment_id=shipment["shipment_id"],
            check_weather=False
        )

        return {**state, "po": approved_po, "shipment": shipment, "tracking": tracking, "status": "completed"}

    except Exception as e:
        return {**state, "status": "failed", "error": f"Approval/shipping error: {e}"}


# ------------------------------------------------------------------
# Routing logic
# ------------------------------------------------------------------

def route_after_draft(state: PipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return END   # Always pause here; Run 2 is triggered separately


def route_after_sourcing(state: PipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "draft_po"


# ------------------------------------------------------------------
# Build graphs
# ------------------------------------------------------------------

checkpointer = MemorySaver()


def build_run1_graph():
    """Graph for Run 1: sourcing → draft PO → pause."""
    g = StateGraph(PipelineState)
    g.add_node("sourcing", node_sourcing)
    g.add_node("draft_po", node_draft_po)
    g.set_entry_point("sourcing")
    g.add_conditional_edges("sourcing", route_after_sourcing, {"draft_po": "draft_po", END: END})
    g.add_edge("draft_po", END)
    return g.compile(checkpointer=checkpointer)


def build_run2_graph():
    """Graph for Run 2: approve + freight + tracking → complete."""
    g = StateGraph(PipelineState)
    g.add_node("approve_and_ship", node_approve_and_ship)
    g.set_entry_point("approve_and_ship")
    g.add_edge("approve_and_ship", END)
    return g.compile(checkpointer=checkpointer)


run1_graph = build_run1_graph()
run2_graph = build_run2_graph()


# ------------------------------------------------------------------
# Public API used by router.py
# ------------------------------------------------------------------

async def start_pipeline(
    material_type: str,
    requirement_id: int,
    qty: float,
    total_value: float,
    compliance_keywords: list[str],
    destination: str = "Colombo, LK",
    targeted_supplier: str | None = None,
) -> dict:
    """Run 1: Sourcing + Draft PO. Returns run_id and paused state."""
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}

    initial_state: PipelineState = {
        "material_type":       material_type,
        "requirement_id":      requirement_id,
        "qty":                 qty,
        "total_value":         total_value,
        "compliance_keywords": compliance_keywords,
        "destination":         destination,
        "targeted_supplier":   targeted_supplier,
        "status":              "running",
    }

    final = await run1_graph.ainvoke(initial_state, config=config)
    return {"run_id": run_id, **final}


async def approve_pipeline(run_id: str, approved_by: str = "Human Manager") -> dict:
    """Run 2: Resume from saved state, approve PO, ship, track."""
    config = {"configurable": {"thread_id": run_id}}

    # Load saved state and inject approval
    saved = run1_graph.get_state(config)
    if not saved or not saved.values:
        return {"error": f"No pipeline found for run_id={run_id}"}

    resume_state = {**saved.values, "approved_by": approved_by, "status": "running"}
    final = await run2_graph.ainvoke(resume_state, config={"configurable": {"thread_id": run_id + "_r2"}})
    return {"run_id": run_id, **final}


async def get_pipeline_state(run_id: str) -> dict:
    """Return the current saved state of a pipeline."""
    config = {"configurable": {"thread_id": run_id}}
    saved = run1_graph.get_state(config)
    if not saved or not saved.values:
        return {"error": f"No pipeline found for run_id={run_id}"}
    return {"run_id": run_id, **saved.values}
