"""
router.py
FastAPI router for all /supply-chain/* endpoints.
Mounted in backend/main.py under the /supply-chain prefix.
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated

from backend.auth import current_user_name

supply_chain_router = APIRouter()
logger = logging.getLogger(__name__)
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------

class RunRequest(BaseModel):
    material_type: Literal["fabric_mill", "trim_vendor", "dye_house"] = "fabric_mill"
    requirement_id: int = Field(default=2, gt=0)
    qty: float = Field(default=300.0, gt=0, allow_inf_nan=False)
    total_value: float = Field(default=78000.0, ge=0, allow_inf_nan=False)
    compliance_keywords: list[ShortText] = Field(default_factory=list, max_length=20)
    destination: str = Field(default="Colombo, LK", max_length=120)
    targeted_supplier: str | None = Field(default=None, max_length=120)
    po_details: dict = Field(default_factory=dict)


class ApproveRequest(BaseModel):
    approved_by: str | None = None

class UpdateSupplierRequest(BaseModel):
    category: Literal["fabric_mill", "trim_vendor", "dye_house"]
    lead_time_days: int = Field(ge=0, le=365)
    rating: float = Field(ge=0, le=5, allow_inf_nan=False)

class UpdateShipmentStatusRequest(BaseModel):
    status: Literal["booked", "in_transit", "delayed", "delivered", "cancelled"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class GatherRequest(BaseModel):
    conversation_history: list[ChatTurn] = Field(max_length=30)


class FindSuppliersRequest(BaseModel):
    material_type: Literal["fabric_mill", "trim_vendor", "dye_house"]
    qty: float = Field(default=300.0, gt=0, allow_inf_nan=False)
    color_spec: str = Field(default="any", max_length=120)
    compliance_keywords: list[ShortText] = Field(default_factory=list, max_length=20)
    dimensions: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# POST /supply-chain/gather
# Multi-turn LLM-driven requirements collection
# ------------------------------------------------------------------

@supply_chain_router.post("/gather")
async def gather_requirements_endpoint(request: GatherRequest):
    """
    Drive a multi-turn conversation to collect procurement requirements.
    Returns either a follow-up question or completed requirements.
    """
    try:
        from backend.supply_chain.supervisor import gather_requirements
        result = gather_requirements([turn.model_dump() for turn in request.conversation_history])
        return result
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# POST /supply-chain/find-suppliers
# Query real DB for matching suppliers, return ranked list
# ------------------------------------------------------------------

@supply_chain_router.post("/find-suppliers")
async def find_suppliers_endpoint(request: FindSuppliersRequest):
    """
    Return all suppliers for a given material_type from the ERP DB,
    ranked by rating, with per-supplier individual pricing.
    """
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        rows = conn.execute(
            """
            SELECT supplier_id, name, country, category, lead_time_days, rating,
                   COALESCE(email, '') as email,
                   COALESCE(price_per_unit, 260.0) as price_per_unit
            FROM suppliers
            WHERE category = ?
            ORDER BY rating DESC
            """,
            (request.material_type,),
        ).fetchall()
        conn.close()

        suppliers = []
        min_price = None
        min_lead  = None
        for r in rows:
            s = dict(r)
            ppu = s["price_per_unit"]
            s["estimated_total"] = round(request.qty * ppu, 2)
            suppliers.append(s)
            if min_price is None or ppu < min_price: min_price = ppu
            if min_lead  is None or s["lead_time_days"] < min_lead: min_lead = s["lead_time_days"]

        # Add badges: best_price & fastest
        for s in suppliers:
            s["badge_best_price"] = (s["price_per_unit"] == min_price)
            s["badge_fastest"]    = (s["lead_time_days"] == min_lead)

        return {"suppliers": suppliers, "total": len(suppliers)}
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# POST /supply-chain/chat

# Natural language entry point — Supervisor LLM parses the message
# and triggers the right sourcing scenario automatically.
# ------------------------------------------------------------------

@supply_chain_router.post("/chat")
async def chat_pipeline(request: ChatRequest):
    """
    Accept a raw natural language message, route it through the
    Supervisor LLM, and start the correct sourcing pipeline.
    """
    try:
        from backend.supply_chain.orchestrator import start_pipeline
        from backend.supply_chain.supervisor import process_chat_message

        decision = process_chat_message(request.message)

        if decision.scenario == "unrelated":
            return {
                "status": "unrelated",
                "message": "I can help you source and procure materials. Try: 'I need 400 meters of organic cotton'."
            }

        result = await start_pipeline(
            material_type=decision.material_type,
            requirement_id=decision.requirement_id,
            qty=float(decision.qty),
            total_value=decision.total_value,
            compliance_keywords=["Organic Cotton", "Child-Labor Free"],
            destination="Colombo, LK",
            # For Scenario A (targeted), pass the supplier name so
            # sourcing_agent can skip the search and go straight to RAG
            targeted_supplier=decision.supplier_name,
        )
        return result
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# POST /supply-chain/run
# Starts the pipeline: sourcing → draft PO → pause
# ------------------------------------------------------------------

@supply_chain_router.post("/run")
async def run_pipeline(request: RunRequest):
    """
    Start the supply chain pipeline.
    Returns a run_id and a pending PO for human review.
    """
    try:
        from backend.supply_chain.orchestrator import start_pipeline

        result = await start_pipeline(
            material_type=request.material_type,
            requirement_id=request.requirement_id,
            qty=request.qty,
            total_value=request.total_value,
            compliance_keywords=request.compliance_keywords,
            destination=request.destination,
            targeted_supplier=request.targeted_supplier,
            po_details=request.po_details,
        )

        if result.get("status") == "failed":
            # Return graceful failure so frontend can show error instead of crashing
            return {
                "status": "failed",
                "error": result.get("error", "Pipeline failed."),
                "run_id": None,
            }

        supplier = result.get("supplier") or {}
        po       = result.get("po") or {}

        return {
            "run_id":       result["run_id"],
            "status":       result.get("status"),
            "supplier":     supplier.get("supplier_name", "Unknown"),
            "country":      supplier.get("country", ""),
            "rating":       supplier.get("rating", 0),
            "compliance":   supplier.get("matched_keywords", []),
            "proof":        supplier.get("compliance_proof", "")[:300],
            "po_id":        po.get("po_id"),
            "qty":          request.qty,
            "total_value":  request.total_value,
            "message":      f"PO #{po.get('po_id')} drafted for {supplier.get('supplier_name')}. Awaiting manager approval.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# GET /supply-chain/shipments/{shipment_id}/track
# Poll current shipment status using the LangChain tracking agent
# ------------------------------------------------------------------

@supply_chain_router.get("/shipments/{shipment_id}/track")
async def track_shipment(shipment_id: int):
    """Run the tracking agent dynamically for a specific shipment."""
    import sys, os
    AGENTS_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "agents", "supply_chain")
    )
    if AGENTS_DIR not in sys.path:
        sys.path.insert(0, AGENTS_DIR)
        
    try:
        from tracking_agent import run_tracking_agent
        result = await run_tracking_agent(shipment_id=shipment_id, check_weather=True)
        if "error" in result:
            raise HTTPException(status_code=503, detail="Shipment tracking is unavailable.")
        return result
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# POST /supply-chain/approve/{run_id}
# Human approves PO → triggers freight + tracking
# ------------------------------------------------------------------

@supply_chain_router.post("/approve/{run_id}")
async def approve_po(run_id: str, request: ApproveRequest = ApproveRequest()):
    """
    Approve a pending PO, complete the pipeline (freight + tracking),
    and automatically send a PO email to the supplier via Brevo SMTP.
    """
    try:
        from backend.supply_chain.orchestrator import approve_pipeline

        result = await approve_pipeline(run_id=run_id, approved_by=current_user_name())

        if result.get("status") == "failed":
            raise HTTPException(status_code=422, detail="Approval could not be completed. Check the pipeline status.")

        if result.get("error"):
            raise HTTPException(status_code=409, detail=result["error"])

        shipment = result.get("shipment") or {}
        tracking = result.get("tracking") or {}
        po_info  = result.get("po") or {}

        # ── Auto-send PO email to supplier via Brevo ──────────────────────────

        return {
            "run_id":           run_id,
            "status":           "completed",
            "po_id":            po_info.get("po_id"),
            "approved_by":      current_user_name(),
            "shipment_id":      shipment.get("shipment_id"),
            "carrier":          shipment.get("carrier_name"),
            "mode":             shipment.get("mode"),
            "origin":           shipment.get("origin"),
            "destination":      shipment.get("destination"),
            "eta":              shipment.get("eta"),
            "track_status":     tracking.get("status"),
            "summary":          tracking.get("summary", ""),
            "email_sent":       result.get("email_sent", False),
            "email_recipient":  result.get("email_recipient", ""),
            "email_error":      result.get("email_error", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# POST /supply-chain/reject/{run_id}
# Human rejects PO
# ------------------------------------------------------------------

@supply_chain_router.post("/reject/{run_id}")
async def reject_po(run_id: str):
    """Mark a pipeline as rejected by the human manager."""
    from backend.supply_chain.orchestrator import reject_pipeline
    result = await reject_pipeline(run_id)
    if result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])
    return result


# ------------------------------------------------------------------
# POST /supply-chain/resend-po-email/{po_id}
# Re-send PO email (available in PurchaseOrdersTab for approved POs)
# ------------------------------------------------------------------

class ResendEmailRequest(BaseModel):
    notes: str = ""

@supply_chain_router.post("/resend-po-email/{po_id}")
async def resend_po_email(po_id: int, request: ResendEmailRequest = ResendEmailRequest()):
    """Re-send the Purchase Order email to the supplier. For approved POs only."""
    try:
        import sys, os, json
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        row = conn.execute("""
            SELECT po.po_id, po.qty, po.total_value, po.order_date, po.status,
                   po.expected_delivery_date, po.approved_by, po.po_details,
                   s.name AS supplier_name, s.country, s.email, s.price_per_unit
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
            WHERE po.po_id = ?
        """, (po_id,)).fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"PO #{po_id} not found.")

        row_dict = dict(row)
        if row_dict["status"] != "approved":
            raise HTTPException(status_code=409, detail="Approve the purchase order before sending its email.")
        supplier_email = row_dict.get("email") or ""
        if not supplier_email:
            raise HTTPException(status_code=422, detail="No email address on file for this supplier. Update the supplier record first.")

        po_details = {}
        if row_dict.get("po_details"):
            try: po_details = json.loads(row_dict["po_details"])
            except Exception: pass

        po_data = {
            "po_id":                 row_dict["po_id"],
            "supplier_name":         row_dict["supplier_name"] or "—",
            "supplier_email":        supplier_email,
            "country":               row_dict["country"] or "",
            "qty":                   row_dict["qty"],
            "unit":                  po_details.get("unit", "units"),
            "total_value":           row_dict["total_value"],
            "price_per_unit":        row_dict["price_per_unit"] or 260.0,
            "order_date":            row_dict["order_date"] or "",
            "expected_delivery_date": row_dict["expected_delivery_date"] or "",
            "approved_by":           row_dict["approved_by"] or "Human Manager",
            "material_name":         po_details.get("material_name", "—"),
            "color_spec":            po_details.get("color_spec", "—"),
            "dimensions":            po_details.get("dimensions", {}),
            "compliance_keywords":   po_details.get("compliance_keywords", []),
            "destination":           po_details.get("destination", ""),
        }

        from backend.supply_chain.email_service import send_po_email
        result = send_po_email(po_data, supplier_email, notes=request.notes)

        if not result.get("sent"):
            raise HTTPException(status_code=503, detail="Supplier email could not be sent. Check email configuration.")

        return {
            "status":    "sent",
            "po_id":     po_id,
            "recipient": supplier_email,
            "message":   f"PO #{po_id:04d} successfully re-sent to {supplier_email}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")



# ------------------------------------------------------------------
# GET /supply-chain/status/{run_id}
# Poll current pipeline state
# ------------------------------------------------------------------

@supply_chain_router.get("/status/{run_id}")
async def pipeline_status(run_id: str):
    """Return the current state of a pipeline by run_id."""
    try:
        from backend.supply_chain.orchestrator import get_pipeline_state

        result = await get_pipeline_state(run_id)
        if result.get("error") and not result.get("status"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# GET /supply-chain/track/{shipment_id}
# Live shipment tracking
# ------------------------------------------------------------------

@supply_chain_router.get("/track/{shipment_id}")
async def track_shipment(shipment_id: int):
    """Get real-time tracking status for a shipment."""
    try:
        from agents.supply_chain.tracking_agent import run_tracking_agent
        result = await run_tracking_agent(shipment_id=shipment_id, check_weather=False)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# GET /supply-chain/suppliers
# Returns all suppliers from ERP database
# ------------------------------------------------------------------

@supply_chain_router.get("/suppliers")
async def list_suppliers():
    """Return all suppliers from mock-erp.db."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        rows = conn.execute(
            "SELECT supplier_id, name, country, category, lead_time_days, rating FROM suppliers ORDER BY rating DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# PUT /supply-chain/suppliers/{supplier_id}
# Update a supplier's intelligence data
# ------------------------------------------------------------------

@supply_chain_router.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: int, request: UpdateSupplierRequest):
    """Update supplier category, lead time, and rating."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        
        # Check if exists
        row = conn.execute("SELECT 1 FROM suppliers WHERE supplier_id = ?", (supplier_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Supplier not found")
            
        conn.execute(
            """
            UPDATE suppliers
            SET category = ?, lead_time_days = ?, rating = ?
            WHERE supplier_id = ?
            """,
            (request.category, request.lead_time_days, request.rating, supplier_id)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Supplier {supplier_id} updated."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: int):
    """Delete a supplier."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        conn.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "supplier_id": supplier_id}
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# GET /supply-chain/purchase-orders
# Returns all POs with joined supplier name and production plan
# ------------------------------------------------------------------

@supply_chain_router.put("/purchase-orders/{po_id}/approve")
async def manual_approve_po(po_id: int):
    """Directly approve a PO in the database."""
    from backend.supply_chain.run_store import load_run
    saved = load_run(po_id=po_id)
    if saved:
        return await approve_po(saved["run_id"])
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        updated = conn.execute(
            "UPDATE purchase_orders SET status = 'approved', approved_by = ? WHERE po_id = ? AND status IN ('draft', 'pending_approval')",
            (current_user_name(), po_id)
        )
        conn.commit()
        conn.close()

        if updated.rowcount != 1:
            raise HTTPException(status_code=409, detail="PO is not awaiting approval. Refresh the purchase orders.")

        from backend.supply_chain.po_email import send_approved_po_email
        email_result = send_approved_po_email(po_id, current_user_name())

        return {
            "status": "success",
            "po_id": po_id,
            "email_sent": email_result.get("sent", False),
            "email_recipient": email_result.get("recipient", ""),
            "email_error": email_result.get("error", "") if not email_result.get("sent") else "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.put("/purchase-orders/{po_id}/reject")
async def manual_reject_po(po_id: int):
    """Directly reject a PO in the database."""
    from backend.supply_chain.run_store import load_run
    saved = load_run(po_id=po_id)
    if saved:
        return await reject_po(saved["run_id"])
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        updated = conn.execute(
            "UPDATE purchase_orders SET status = 'rejected' WHERE po_id = ? AND status IN ('draft', 'pending_approval')",
            (po_id,)
        )
        conn.commit()
        conn.close()
        if updated.rowcount != 1:
            raise HTTPException(status_code=409, detail="PO is not awaiting approval. Refresh the purchase orders.")
        return {"status": "success", "po_id": po_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.delete("/purchase-orders/{po_id}")
async def delete_purchase_order(po_id: int):
    """Delete an approved or rejected purchase order."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        conn.execute("DELETE FROM purchase_orders WHERE po_id = ?", (po_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "po_id": po_id}
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.get("/purchase-orders")
async def list_purchase_orders():
    """Return all purchase orders with supplier name from mock-erp.db."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_erp_db_ready, get_erp_db_connection
        ensure_erp_db_ready()
        conn = get_erp_db_connection()
        rows = conn.execute(
            """
            SELECT po.po_id, po.qty, po.total_value, po.order_date,
                   po.expected_delivery_date, po.status, po.approved_by,
                   s.name AS supplier_name, s.country,
                   pp.style_name, pp.material_name
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
            LEFT JOIN production_plan pp ON po.requirement_id = pp.requirement_id
            ORDER BY po.po_id DESC
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")


# ------------------------------------------------------------------
# GET /supply-chain/shipments
# Returns all shipments with joined carrier name from TMS database
# ------------------------------------------------------------------

@supply_chain_router.get("/shipments")
async def list_shipments():
    """Return all shipments with carrier info from mock-tms.db."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_tms_db_ready, get_tms_db_connection
        ensure_tms_db_ready()
        conn = get_tms_db_connection()
        rows = conn.execute(
            """
            SELECT s.shipment_id, s.reference_type, s.reference_id,
                   s.mode, s.origin, s.destination, s.status,
                   s.booked_date, s.eta, s.actual_arrival,
                   c.name AS carrier_name, c.rate_per_unit
            FROM shipments s
            LEFT JOIN carriers c ON s.carrier_id = c.carrier_id
            ORDER BY s.shipment_id DESC
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.put("/shipments/{shipment_id}/status")
async def update_shipment_status_manual(shipment_id: int, request: UpdateShipmentStatusRequest):
    """Manually update the status of a shipment."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_tms_db_ready, get_tms_db_connection
        ensure_tms_db_ready()
        conn = get_tms_db_connection()
        conn.execute(
            "UPDATE shipments SET status = ? WHERE shipment_id = ?",
            (request.status, shipment_id)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "shipment_id": shipment_id}
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")

@supply_chain_router.delete("/shipments/{shipment_id}")
async def delete_shipment(shipment_id: int):
    """Delete a shipment."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import ensure_tms_db_ready, get_tms_db_connection
        ensure_tms_db_ready()
        conn = get_tms_db_connection()
        conn.execute("DELETE FROM shipments WHERE shipment_id = ?", (shipment_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "shipment_id": shipment_id}
    except Exception as e:
        logger.exception("Supply-chain request failed")
        raise HTTPException(status_code=500, detail="The supply-chain request could not be completed.")
