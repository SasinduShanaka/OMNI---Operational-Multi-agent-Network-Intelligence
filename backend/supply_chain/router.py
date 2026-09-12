"""
router.py
FastAPI router for all /supply-chain/* endpoints.
Mounted in backend/main.py under the /supply-chain prefix.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.supply_chain.orchestrator import (
    start_pipeline,
    approve_pipeline,
    get_pipeline_state,
)
from backend.supply_chain.supervisor import process_chat_message

supply_chain_router = APIRouter()


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------

class RunRequest(BaseModel):
    material_type:       str        = "fabric_mill"
    requirement_id:      int        = 2
    qty:                 float      = 300.0
    total_value:         float      = 78000.0
    compliance_keywords: list[str]  = ["Organic Cotton", "Child-Labor Free"]
    destination:         str        = "Colombo, LK"


class ApproveRequest(BaseModel):
    approved_by: str = "Human Manager"

class UpdateSupplierRequest(BaseModel):
    category: str
    lead_time_days: int
    rating: float

class UpdateShipmentStatusRequest(BaseModel):
    status: str


class ChatRequest(BaseModel):
    message: str


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
        raise HTTPException(status_code=500, detail=str(e))


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
        result = await start_pipeline(
            material_type=request.material_type,
            requirement_id=request.requirement_id,
            qty=request.qty,
            total_value=request.total_value,
            compliance_keywords=request.compliance_keywords,
            destination=request.destination,
        )

        if result.get("status") == "failed":
            raise HTTPException(status_code=422, detail=result.get("error", "Pipeline failed."))

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
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# POST /supply-chain/approve/{run_id}
# Human approves PO → triggers freight + tracking
# ------------------------------------------------------------------

@supply_chain_router.post("/approve/{run_id}")
async def approve_po(run_id: str, request: ApproveRequest = ApproveRequest()):
    """
    Approve a pending PO and complete the pipeline (freight + tracking).
    """
    try:
        result = await approve_pipeline(run_id=run_id, approved_by=request.approved_by)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        if result.get("status") == "failed":
            raise HTTPException(status_code=422, detail=result.get("error", "Pipeline failed after approval."))

        shipment = result.get("shipment") or {}
        tracking = result.get("tracking") or {}

        return {
            "run_id":      run_id,
            "status":      "completed",
            "po_id":       result.get("po", {}).get("po_id"),
            "approved_by": request.approved_by,
            "shipment_id": shipment.get("shipment_id"),
            "carrier":     shipment.get("carrier_name"),
            "mode":        shipment.get("mode"),
            "origin":      shipment.get("origin"),
            "destination": shipment.get("destination"),
            "eta":         shipment.get("eta"),
            "track_status": tracking.get("status"),
            "summary":     tracking.get("summary", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# POST /supply-chain/reject/{run_id}
# Human rejects PO
# ------------------------------------------------------------------

@supply_chain_router.post("/reject/{run_id}")
async def reject_po(run_id: str):
    """Mark a pipeline as rejected by the human manager."""
    return {
        "run_id":  run_id,
        "status":  "rejected",
        "message": "PO has been rejected. Pipeline stopped.",
    }


# ------------------------------------------------------------------
# GET /supply-chain/status/{run_id}
# Poll current pipeline state
# ------------------------------------------------------------------

@supply_chain_router.get("/status/{run_id}")
async def pipeline_status(run_id: str):
    """Return the current state of a pipeline by run_id."""
    try:
        result = await get_pipeline_state(run_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


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
        from db import get_erp_db_connection
        conn = get_erp_db_connection()
        rows = conn.execute(
            "SELECT supplier_id, name, country, category, lead_time_days, rating FROM suppliers ORDER BY rating DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        from db import get_erp_db_connection
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
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: int):
    """Delete a supplier."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_erp_db_connection
        conn = get_erp_db_connection()
        conn.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "supplier_id": supplier_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# GET /supply-chain/purchase-orders
# Returns all POs with joined supplier name and production plan
# ------------------------------------------------------------------

@supply_chain_router.put("/purchase-orders/{po_id}/approve")
async def manual_approve_po(po_id: int):
    """Directly approve a PO in the database."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_erp_db_connection
        conn = get_erp_db_connection()
        conn.execute(
            "UPDATE purchase_orders SET status = 'approved', approved_by = 'Human Manager' WHERE po_id = ?",
            (po_id,)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "po_id": po_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.put("/purchase-orders/{po_id}/reject")
async def manual_reject_po(po_id: int):
    """Directly reject a PO in the database."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_erp_db_connection
        conn = get_erp_db_connection()
        conn.execute(
            "UPDATE purchase_orders SET status = 'rejected' WHERE po_id = ?",
            (po_id,)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "po_id": po_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.delete("/purchase-orders/{po_id}")
async def delete_purchase_order(po_id: int):
    """Delete an approved or rejected purchase order."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_erp_db_connection
        conn = get_erp_db_connection()
        conn.execute("DELETE FROM purchase_orders WHERE po_id = ?", (po_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "po_id": po_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.get("/purchase-orders")
async def list_purchase_orders():
    """Return all purchase orders with supplier name from mock-erp.db."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_erp_db_connection
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
        raise HTTPException(status_code=500, detail=str(e))


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
        from db import get_tms_db_connection
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
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.put("/shipments/{shipment_id}/status")
async def update_shipment_status_manual(shipment_id: int, request: UpdateShipmentStatusRequest):
    """Manually update the status of a shipment."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_tms_db_connection
        conn = get_tms_db_connection()
        conn.execute(
            "UPDATE shipments SET status = ? WHERE shipment_id = ?",
            (request.status, shipment_id)
        )
        conn.commit()
        conn.close()
        return {"status": "success", "shipment_id": shipment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@supply_chain_router.delete("/shipments/{shipment_id}")
async def delete_shipment(shipment_id: int):
    """Delete a shipment."""
    try:
        import sys, os
        DB_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "database", "supply_chain", "sqlite_db")
        )
        sys.path.insert(0, DB_DIR)
        from db import get_tms_db_connection
        conn = get_tms_db_connection()
        conn.execute("DELETE FROM shipments WHERE shipment_id = ?", (shipment_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "shipment_id": shipment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
