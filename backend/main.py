import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

# Make project root available so we can import agents/
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_PATH = os.path.join(
    BASE_DIR,
    "backend",
    ".env"
)

load_dotenv(ENV_PATH)


# Supply chain pipeline router (Dinuja's component)
from backend.supply_chain.router import supply_chain_router


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="OMNI Operations API",
    description="Operational Multi-Agent Network Intelligence API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# Mount supply chain router under /supply-chain prefix
app.include_router(supply_chain_router, prefix="/supply-chain", tags=["Supply Chain"])


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):
    message: str
    session_id: str | None = None
    payload: dict | None = None


class MaterialRequest(BaseModel):
    material_name: str | None = None
    material_code: str | None = None


class ForecastRequest(BaseModel):
    sku: str
    periods: int = 1
    save_audit: bool = True


class FeasibilityRequest(BaseModel):
    sku: str | None = None
    product_name: str | None = None
    quantity: float
    required_date: str


# ============================================================
# PROCUREMENT SESSIONS
# ============================================================

procurement_sessions = {}

def handle_procurement_turn(session_id: str, request: AskRequest):
    from backend.supply_chain.supervisor import gather_requirements
    from backend.supply_chain.orchestrator import start_pipeline
    import asyncio
    
    if session_id not in procurement_sessions or isinstance(procurement_sessions.get(session_id), list):
        procurement_sessions[session_id] = {"phase": "gathering", "history": [], "requirements": {}}
        
    session = procurement_sessions[session_id]
    
    user_message = request.message
    payload = request.payload or {}
    
    # ── PHASE: gathering ──
    if session["phase"] == "gathering":
        session["history"].append({"role": "user", "content": user_message})
        decision = gather_requirements(session["history"])
        
        if decision.get("status") in ("needs_more_info", "needs_shade_selection"):
            assistant_reply = decision.get("question", "Could you provide more details?")
            session["history"].append({"role": "assistant", "content": assistant_reply})
            
            q_lower = assistant_reply.lower()
            return_status = decision.get("status")
            if "color" in q_lower or "colour" in q_lower or "shade" in q_lower:
                return_status = "needs_shade_selection"
                
            return {
                "agent": "Supply Chain Agent",
                "task": "Procurement Requirements",
                "intent": "procurement",
                "status": return_status,
                "answer": assistant_reply,
                "shades": decision.get("shades", [])
            }
            
        elif decision.get("status") == "ready":
            session["requirements"] = decision
            session["phase"] = "selecting"
            
            # Fetch suppliers from DB directly
            import sys, os
            DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "supply_chain", "sqlite_db"))
            if DB_DIR not in sys.path:
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
                (decision.get("material_type"),),
            ).fetchall()
            conn.close()

            suppliers = []
            min_price = None
            min_lead  = None
            qty = float(decision.get("qty", 300))
            for r in rows:
                s = dict(r)
                ppu = s["price_per_unit"]
                s["estimated_total"] = round(qty * ppu, 2)
                suppliers.append(s)
                if min_price is None or ppu < min_price: min_price = ppu
                if min_lead  is None or s["lead_time_days"] < min_lead: min_lead = s["lead_time_days"]

            for s in suppliers:
                s["badge_best_price"] = (s["price_per_unit"] == min_price)
                s["badge_fastest"]    = (s["lead_time_days"] == min_lead)
            
            return {
                "agent": "Supply Chain Agent",
                "task": "Select Supplier",
                "intent": "procurement",
                "status": "selecting",
                "answer": "Here are the top suppliers that match your requirements. Please select one to proceed.",
                "suppliers": suppliers
            }

    # ── PHASE: selecting ──
    elif session["phase"] == "selecting":
        if "supplier" not in payload:
            return {
                "agent": "Supply Chain Agent",
                "task": "Select Supplier",
                "intent": "procurement",
                "status": "selecting",
                "answer": "Please select a supplier by clicking one of the options below.",
            }
            
        selected_supplier = payload["supplier"]
        decision = session["requirements"]
        
        # We draft the PO and enter approving phase
        # Wait, start_pipeline does EVERYTHING (Sourcing -> Purchasing -> Freight).
        # We want to mimic the frontend's step-by-step.
        # But wait, CopilotChat calls /run which runs the WHOLE pipeline, and then just says "done" or waits for approval.
        # We draft the PO
        result = asyncio.run(start_pipeline(
            material_type=decision.get("material_type"),
            requirement_id=decision.get("requirement_id"),
            qty=float(decision.get("qty", 300)),
            total_value=selected_supplier.get("estimated_total", decision.get("total_value")),
            compliance_keywords=decision.get("compliance_keywords", []),
            destination=decision.get("destination", "Colombo, Sri Lanka"),
            targeted_supplier=selected_supplier.get("name"),
            po_details={
                "color_spec": decision.get("color_spec"),
                "material_name": decision.get("material_name"),
            }
        ))
        
        # Clear the session since the frontend OmniProcurementCard handles the approval directly
        del procurement_sessions[session_id]
        
        return {
            "agent": "Operations Agent",
            "task": "Procurement Request",
            "delegated_to": "Supply Chain Agent",
            "intent": "procurement",
            "status": "success",
            "workflow": ["Operations Agent", "Supply Chain Agent", "Sourcing Agent", "Purchasing Agent"],
            "answer": "I drafted a Purchase Order for your selected supplier. Please review the details below to authorize the purchase.",
            "data": result
        }

# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "system": "OMNI",
        "message": "OMNI backend is running!",
        "status": "online"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "system": "OMNI",
        "message": "System healthy",
        "status": "online"
    }


# ============================================================
# OPERATIONS AGENT
# ============================================================

import uuid

@app.post("/ask")
def ask_agent(request: AskRequest):

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        # Check active session
        session_id = request.session_id
        if session_id and session_id in procurement_sessions:
            return handle_procurement_turn(session_id, request)

        from agents.operations_agent import process_request
        result = process_request(request.message)

        if result.get("status") == "init_session":
            # Start new session
            new_session = session_id or str(uuid.uuid4())
            result["session_id"] = new_session
            # Immediately take the first turn
            return handle_procurement_turn(new_session, request)

        return result

    except Exception as error:
        print(f"Operations Agent error: {error}")
        raise HTTPException(status_code=500, detail="Operations Agent failed to process the request.")



# ============================================================
# DEMAND FORECAST AGENT
# ============================================================

@app.get("/forecast/data-quality/{sku}")
def demand_quality(sku: str):
    try:
        from agents.forecast_agent import get_demand_quality
        return get_demand_quality(sku)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"message": str(error)})
    except Exception:
        raise HTTPException(status_code=503, detail={"message": "Unable to check demand data. Check MongoDB connectivity."})


@app.get("/forecast/products")
def forecast_products():
    try:
        from agents.forecast_agent import get_forecast_products
        return {"products": get_forecast_products()}
    except Exception:
        raise HTTPException(status_code=503, detail={"message": "Unable to load products from MongoDB. Check database connectivity and MONGO_URI."})


@app.post("/forecast")
def demand_forecast(request: ForecastRequest):
    """Send a demand-forecast request directly to the Forecast Agent."""
    from agents.forecast_agent import forecast_demand

    result = forecast_demand(request.sku, request.periods, request.save_audit)

    if result["status"] == "error":
        status_code = 404 if result["error_code"] == "not_found" else 503 if result["error_code"] in {"configuration_error", "data_access_error"} else 400
        raise HTTPException(status_code=status_code, detail=result)

    return result


# ============================================================
# INVENTORY — ALL ITEMS
# ============================================================

@app.get("/inventory")
def inventory():

    try:
        from agents.inventory_agent import check_inventory

        return check_inventory()

    except Exception as error:

        print(
            f"Inventory error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve inventory."
        )


# ============================================================
# INVENTORY — LOW STOCK
# ============================================================

@app.get("/inventory/low-stock")
def low_stock():

    try:
        from agents.inventory_agent import get_low_stock

        return get_low_stock()

    except Exception as error:

        print(
            f"Low stock error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve low-stock materials."
        )


# ============================================================
# INVENTORY — SPECIFIC MATERIAL
# ============================================================

@app.post("/inventory/material")
def material(request: MaterialRequest):

    if not request.material_name and not request.material_code:

        raise HTTPException(
            status_code=400,
            detail="Provide material_name or material_code."
        )

    try:
        from agents.inventory_agent import get_material

        result = get_material(
            material_name=request.material_name,
            material_code=request.material_code
        )

        if result is None:

            raise HTTPException(
                status_code=404,
                detail="Material not found."
            )

        return result

    except HTTPException:

        raise

    except Exception as error:

        print(
            f"Material lookup error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve material."
        )


# ============================================================
# INVENTORY — TOTAL STOCK
# ============================================================

@app.get("/inventory/total")
def total_stock():

    try:
        from agents.inventory_agent import get_total_stock

        return get_total_stock()

    except Exception as error:

        print(
            f"Total stock error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to calculate total stock."
        )

# ============================================================
# PRODUCTION — LINES
# ============================================================

@app.get("/production/lines")
def production_lines():

    try:
        from agents.production_agent import get_all_lines

        return get_all_lines()

    except Exception as error:

        print(
            f"Production lines error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve production lines."
        )


# ============================================================
# PRODUCTION — UTILIZATION
# ============================================================

@app.get("/production/utilization")
def production_utilization():

    try:
        from agents.production_agent import get_line_utilization

        return get_line_utilization()

    except Exception as error:

        print(
            f"Production utilization error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve line utilization."
        )


# ============================================================
# PRODUCTION — BOTTLENECKS
# ============================================================

@app.get("/production/bottlenecks")
def production_bottlenecks():

    try:
        from agents.production_agent import identify_bottlenecks

        return identify_bottlenecks()

    except Exception as error:

        print(
            f"Production bottleneck error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to identify production bottlenecks."
        )


# ============================================================
# PRODUCTION — ORDERS
# ============================================================

@app.get("/production/orders")
def production_orders():

    try:
        from agents.production_agent import get_production_orders

        return get_production_orders()

    except Exception as error:

        print(
            f"Production orders error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve production orders."
        )


# ============================================================
# PRODUCTION — SINGLE ORDER PROGRESS
# ============================================================

@app.get("/production/orders/{order_id}")
def production_order_progress(order_id: str):

    try:
        from agents.production_agent import get_production_progress

        result = get_production_progress(
            order_id=order_id,
            production_order_id=order_id
        )

        if result is None:

            raise HTTPException(
                status_code=404,
                detail="Production order not found."
            )

        return result

    except HTTPException:

        raise

    except Exception as error:

        print(
            f"Production progress error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve production order progress."
        )


# ============================================================
# PRODUCTION — FEASIBILITY (PRODUCTION -> INVENTORY AGENT)
# ============================================================

@app.post("/production/feasibility")
def production_feasibility(request: FeasibilityRequest):

    if not request.sku and not request.product_name:

        raise HTTPException(
            status_code=400,
            detail="Provide sku or product_name."
        )

    if request.quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero."
        )

    try:
        from agents.production_agent import check_production_feasibility

        result = check_production_feasibility(
            sku=request.sku,
            product_name=request.product_name,
            quantity=request.quantity,
            required_date=request.required_date
        )

        if result.get("status") == "NOT_FOUND":

            raise HTTPException(
                status_code=404,
                detail="Product not found."
            )

        return result

    except HTTPException:

        raise

    except Exception as error:

        print(
            f"Production feasibility error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to assess production feasibility."
        )


# ============================================================
# PRODUCTION — KPIs
# ============================================================

@app.get("/production/kpis")
def production_kpis():

    try:
        from agents.production_agent import get_production_kpis

        return get_production_kpis()

    except Exception as error:

        print(
            f"Production KPI error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to calculate production KPIs."
        )


# ============================================================
# PRODUCTION — SUMMARY
# ============================================================

@app.get("/production/summary")
def production_summary():

    try:
        from agents.production_agent import get_production_summary

        return get_production_summary()

    except Exception as error:

        print(
            f"Production summary error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve production summary."
        )


# ============================================================
# PRODUCTION — PRODUCIBLE PRODUCTS
# ============================================================

@app.get("/production/products")
def production_products():

    try:
        from agents.production_agent import get_producible_products

        return get_producible_products()

    except Exception as error:

        print(
            f"Producible products error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve producible products."
        )
