import os
import sys
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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
from backend.report_router import router as report_router
from backend.auth import authenticate_token, router as auth_router, principal, current_user_name, require_manager


@asynccontextmanager
async def lifespan(app):
    from backend.report_service import start_scheduler
    stop, thread = start_scheduler()
    try:
        yield
    finally:
        stop.set()
        await asyncio.to_thread(thread.join, 5)
        from database.connection import client as database_client
        from agents.inventory import inventory_agent
        from agents.forecast import forecast_agent
        from backend.report_service import get_db
        database_client.close()
        inventory_agent.client.close()
        if forecast_agent.mongo_client is not None:
            forecast_agent.mongo_client.close()
        if get_db.cache_info().currsize:
            get_db().client.close()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    lifespan=lifespan,
    title="OMNI Operations API",
    description="Operational Multi-Agent Network Intelligence API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

PUBLIC_PATHS = {"/", "/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/auth/login", "/auth/register"}
_request_times = defaultdict(deque)
_rate_lock = Lock()


def rate_limited(key: str, limit: int, window: int = 60) -> bool:
    now = monotonic()
    with _rate_lock:
        calls = _request_times[key]
        while calls and calls[0] <= now - window:
            calls.popleft()
        if len(calls) >= limit:
            return True
        calls.append(now)
        return False


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    path = request.url.path
    if request.method in {"POST", "PUT", "PATCH"} and len(await request.body()) > 65_536:
        return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
    if path in {"/auth/login", "/auth/register"} or path in {"/ask", "/ask-omni"} or path.startswith("/supply-chain/gather"):
        client_ip = request.client.host if request.client else "unknown"
        limit = 10 if path in {"/auth/login", "/auth/register"} else 30
        if rate_limited(f"{client_ip}:{path}", limit):
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."})
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    token = token if scheme.lower() == "bearer" and token else request.cookies.get("omni_session", "")
    user = authenticate_token(token) if token else None
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"detail": "Your session is missing or has expired. Please sign in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.user = user
    if request.method not in {"GET", "HEAD"} and "omni_session" in request.cookies:
        origin = request.headers.get("origin")
        if origin and origin not in {
            "http://localhost:5173", "http://127.0.0.1:5173",
            "http://localhost:5174", "http://127.0.0.1:5174",
            "http://localhost:5175", "http://127.0.0.1:5175",
            os.getenv("FRONTEND_ORIGIN", ""),
        }:
            return JSONResponse(status_code=403, content={"detail": "Untrusted request origin."})
    role = user.get("role", "viewer")
    if request.method not in {"GET", "HEAD"} and path not in {"/auth/logout"} and role not in {"manager", "user"}:
        return JSONResponse(status_code=403, content={"detail": "Manager access is required for this action."})
    context_token = principal.set(user)
    try:
        return await call_next(request)
    finally:
        principal.reset(context_token)


# Keep CORS outside authentication so browsers can read 401 responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        *([os.getenv("FRONTEND_ORIGIN")] if os.getenv("FRONTEND_ORIGIN") else []),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount supply chain router under /supply-chain prefix
app.include_router(supply_chain_router, prefix="/supply-chain", tags=["Supply Chain"])
app.include_router(report_router)
app.include_router(auth_router)


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    payload: dict | None = None
    request_id: str | None = Field(default=None, max_length=128)


class MaterialRequest(BaseModel):
    material_name: str | None = Field(default=None, max_length=120)
    material_code: str | None = Field(default=None, max_length=32)


class InventoryCreateRequest(BaseModel):
    material_name: str = Field(min_length=1, max_length=120)
    current_stock: float = Field(ge=0, allow_inf_nan=False)
    reorder_level: float = Field(ge=0, allow_inf_nan=False)
    unit: str = Field(default="units", max_length=32)
    material_code: str | None = Field(default=None, max_length=32)
    classification: str | None = Field(default="B", pattern="^[ABC]$")


class ForecastRequest(BaseModel):
    sku: str = Field(pattern=r"(?i)^GAR-\d{3}$")
    periods: int = Field(default=1, ge=1, le=12)
    save_audit: bool = True


class FeasibilityRequest(BaseModel):
    sku: str | None = Field(default=None, max_length=32)
    product_name: str | None = Field(default=None, max_length=120)
    quantity: float = Field(gt=0, allow_inf_nan=False)
    required_date: str = Field(max_length=32)


# ============================================================
# PROCUREMENT SESSIONS
# ============================================================

procurement_sessions = {}
operations_contexts = {}
agent_activity_log = []


def compact_workflow(workflow):
    if not workflow:
        return workflow

    internal_supply_chain_steps = {
        "Sourcing Agent",
        "Purchasing Agent",
        "Freight Agent",
        "Tracking Agent",
    }
    compacted = []

    for step in workflow:
        if step in internal_supply_chain_steps:
            if "Supply Chain Agent" not in compacted:
                compacted.append("Supply Chain Agent")
            continue
        if step not in compacted:
            compacted.append(step)

    return compacted


def collect_pending_approvals(result: dict):
    pending = []

    def add_run(run, material=None):
        if not isinstance(run, dict) or run.get("status") != "awaiting_approval":
            return
        po = run.get("po") or {}
        pending.append({
            "run_id": run.get("run_id"),
            "po_id": po.get("po_id"),
            "supplier": (run.get("supplier") or {}).get("supplier_name"),
            "material": (material or {}).get("material_name"),
            "status": run.get("status"),
        })

    if isinstance(result.get("data"), dict):
        add_run(result["data"])

    for item in result.get("procurement") or []:
        add_run(item.get("run"), item.get("material"))

    for item in ((result.get("result") or {}).get("procurement") or []):
        add_run(item.get("run"), item)

    return [item for item in pending if item.get("run_id")]


def record_agent_activity(action: str, result: dict | None = None, session_id: str | None = None, severity: str = "Low"):
    result = result or {}
    record = {
        "agent": result.get("agent", "Operations Agent"),
        "action": action,
        "intent": result.get("intent"),
        "status": result.get("status"),
        "workflow": result.get("workflow", []),
        "severity": severity,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Keep only compact operational events; never persist prompts or raw evidence.
    record["supervisor_events"] = [
        {key: event.get(key) for key in ("event", "agent", "status", "round", "reason")
         if key in event}
        for event in (result.get("operational_events") or [])[-20:]
        if isinstance(event, dict)
    ]
    record["retry_counts"] = result.get("retry_counts") or {}
    if result.get("review"):
        record["review_status"] = "valid" if result["review"].get("valid") else "issues"
    if result.get("intent") == "approval_followup":
        record["approval_actor"] = (principal.get() or {}).get("user_id")
    if principal.get():
        record["user_id"] = principal.get()["user_id"]

    try:
        from database.connection import db
        db["agent_activity"].insert_one(record.copy())
    except Exception as error:
        record["storage_warning"] = str(error)

    agent_activity_log.append(record)
    if len(agent_activity_log) > 200:
        del agent_activity_log[:-200]

    return record


def is_low_stock_supply_chain_request(message: str) -> bool:
    text = message.lower()
    low_stock_reference = any(phrase in text for phrase in (
        "low stock",
        "low inventory",
        "these low stock",
        "those low stock",
        "reorder level",
        "below reorder",
    ))
    supply_chain_action = any(word in text for word in (
        "order",
        "buy",
        "procure",
        "source",
        "supplier",
        "suppliers",
        "purchase",
        "replenish",
    ))
    return low_stock_reference and supply_chain_action


def is_contextual_low_stock_order(message: str, session_id: str | None) -> bool:
    if not session_id:
        return False
    from agents.operations.conversation_context import get_context
    user_id = (principal.get() or {}).get("user_id")
    state = get_context(session_id, user_id)
    previous = operations_contexts.get(session_id, {})
    owner = previous.get("owner_id")
    if state:
        relevant = state.last_business_intent == "low_stock_procurement"
    else:
        relevant = previous.get("intent") == "low_stock_procurement" and (not owner or owner == user_id)
    if not relevant:
        return False

    text = message.lower()
    contextual_reference = any(word in text for word in (
        "these",
        "those",
        "them",
        "above",
        "suggested",
        "all",
    ))
    order_action = any(word in text for word in (
        "order",
        "buy",
        "procure",
        "purchase",
        "replenish",
    ))
    return contextual_reference and order_action


def remember_operations_context(session_id: str | None, result: dict):
    if not session_id:
        return

    from agents.operations.conversation_context import remember_pending_approvals
    pending = collect_pending_approvals(result)
    if pending:
        remember_pending_approvals(session_id, (principal.get() or {}).get("user_id"), pending)

    if result.get("intent") == "low_stock_procurement" and result.get("status") == "success":
        operations_contexts[session_id] = {
            "owner_id": (principal.get() or {}).get("user_id"),
            "intent": result.get("intent"),
            "results": result.get("results", []),
            "procurement": result.get("procurement", []),
            "pending_approvals": collect_pending_approvals(result),
        }
        return

    if pending:
        operations_contexts[session_id] = {
            "owner_id": (principal.get() or {}).get("user_id"),
            "intent": result.get("intent"),
            "pending_approvals": pending,
        }


def is_approval_followup(message: str, session_id: str | None) -> bool:
    if not session_id:
        return False
    from agents.operations.conversation_context import get_context
    state = get_context(session_id, (principal.get() or {}).get("user_id"))
    legacy = operations_contexts.get(session_id, {})
    owner = legacy.get("owner_id")
    pending = (state.pending_approvals if state else
               legacy.get("pending_approvals") if not owner or owner == (principal.get() or {}).get("user_id") else [])
    if not pending:
        return False

    text = message.lower()
    return any(word in text for word in ("approve", "authorize", "reject", "cancel"))


def select_pending_approval(message: str, pending: list[dict]):
    text = message.lower()

    po_match = None
    import re
    match = re.search(r"#?(\d+)", text)
    if match:
        po_match = int(match.group(1))

    if po_match is not None:
        for item in pending:
            if item.get("po_id") == po_match:
                return [item], None
        return [], f"I could not find pending PO #{po_match} in this chat."

    if "all" in text or "them" in text or "these" in text:
        return pending, None

    if "first" in text or "1st" in text:
        return pending[:1], None

    if "second" in text or "2nd" in text:
        return pending[1:2], None

    if len(pending) == 1:
        return pending, None

    choices = ", ".join(
        f"PO #{item.get('po_id')} for {item.get('material') or item.get('supplier') or 'the supplier'}"
        for item in pending
    )
    return [], f"I found multiple pending approvals: {choices}. Please say which PO to approve, or say approve all."


def handle_approval_followup(session_id: str, request: AskRequest):
    require_manager()
    from backend.supply_chain.orchestrator import approve_pipeline, reject_pipeline
    import asyncio

    from agents.operations.conversation_context import get_context, remember_pending_approvals
    context = operations_contexts.get(session_id, {})
    user_id = (principal.get() or {}).get("user_id")
    state = get_context(session_id, user_id)
    pending = state.pending_approvals if state else (
        context.get("pending_approvals", []) if not context.get("owner_id") or context["owner_id"] == user_id else [])
    selected, question = select_pending_approval(request.message, pending)

    if question:
        result = {
            "agent": "Operations Agent",
            "task": "Purchase Order Approval",
            "delegated_to": "Supply Chain Agent",
            "intent": "approval_followup",
            "status": "needs_more_info",
            "workflow": ["Operations Agent", "Supply Chain Agent"],
            "answer": question,
        }
        record_agent_activity("Approval follow-up needs clarification", result, session_id, "Medium")
        return result

    rejecting = any(word in request.message.lower() for word in ("reject", "cancel"))
    completed = []
    failed = []

    for item in selected:
        try:
            if rejecting:
                rejected = asyncio.run(reject_pipeline(item["run_id"]))
                if rejected.get("error"):
                    failed.append({**item, "error": rejected["error"]})
                else:
                    completed.append({**item, "approval": rejected, "status": "rejected"})
            else:
                approved = asyncio.run(approve_pipeline(item["run_id"], approved_by=current_user_name()))
                if approved.get("error") or approved.get("status") == "failed":
                    failed.append({**item, "error": approved.get("error", "Approval failed.")})
                else:
                    completed.append({**item, "approval": approved, "status": "approved"})
        except Exception as error:
            failed.append({**item, "error": str(error)})

    completed_run_ids = {item.get("run_id") for item in completed}
    context["pending_approvals"] = [
        item for item in pending
        if item.get("run_id") not in completed_run_ids
    ]
    remember_pending_approvals(session_id, user_id, context["pending_approvals"])

    verb = "rejected" if rejecting else "approved"
    answer = f"I {verb} {len(completed)} purchase order(s)."
    if completed and not rejecting:
        shipments = [
            (item.get("approval", {}).get("shipment") or {}).get("shipment_id")
            for item in completed
            if (item.get("approval", {}).get("shipment") or {}).get("shipment_id")
        ]
        if shipments:
            answer += f" Freight booking is complete for shipment(s): {', '.join(f'#{shipment}' for shipment in shipments)}."
        email_sent = [
            item.get("approval", {}).get("email_recipient")
            for item in completed
            if item.get("approval", {}).get("email_sent")
        ]
        email_errors = [
            item.get("approval", {}).get("email_error")
            for item in completed
            if item.get("approval", {}).get("email_error")
        ]
        if email_sent:
            answer += f" PO email sent to {', '.join(email_sent)}."
        elif email_errors:
            answer += f" The PO was approved, but the email was not sent: {email_errors[0]}"
    if failed:
        answer += f" {len(failed)} item(s) could not be processed and need manual review."

    result = {
        "agent": "Operations Agent",
        "task": "Purchase Order Approval",
        "delegated_to": "Supply Chain Agent",
        "intent": "approval_followup",
        "status": "success" if not failed else "partial_success",
        "workflow": ["Operations Agent", "Supply Chain Agent"],
        "answer": answer,
        "results": completed,
        "errors": failed,
    }
    record_agent_activity(f"Purchase order follow-up {verb}", result, session_id, "Medium")
    return result


def _supplier_options(requirements: dict) -> list[dict]:
    """Read current ERP suppliers for a verified material requirement."""
    import os
    import sys

    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "supply_chain", "sqlite_db"))
    if db_dir not in sys.path:
        sys.path.insert(0, db_dir)
    from db import ensure_erp_db_ready, get_erp_db_connection

    ensure_erp_db_ready()
    conn = get_erp_db_connection()
    try:
        rows = conn.execute(
            "SELECT supplier_id, name, country, category, lead_time_days, rating, "
            "COALESCE(email, '') AS email, price_per_unit "
            "FROM suppliers WHERE category = ? ORDER BY rating DESC",
            (requirements["material_type"],),
        ).fetchall()
    finally:
        conn.close()
    suppliers = []
    for row in rows:
        supplier = dict(row)
        price = supplier.get("price_per_unit")
        supplier["estimated_total"] = round(float(requirements["qty"]) * price, 2) if price is not None else None
        suppliers.append(supplier)
    priced = [item["price_per_unit"] for item in suppliers if item["price_per_unit"] is not None]
    leads = [item["lead_time_days"] for item in suppliers if item["lead_time_days"] is not None]
    for supplier in suppliers:
        supplier["badge_best_price"] = bool(priced and supplier["price_per_unit"] == min(priced))
        supplier["badge_fastest"] = bool(leads and supplier["lead_time_days"] == min(leads))
    return suppliers


def _start_contextual_procurement(session_id: str, materials: list[dict]) -> dict:
    """Seed existing supplier-selection flow; this never drafts or approves a PO."""
    if len(materials) != 1:
        choices = "\n".join(
            f"{index}. {item.get('material_name') or item['material_code']} — "
            f"{item['shortage']:,.0f} {item.get('unit') or 'units'}"
            for index, item in enumerate(materials, 1)
        )
        return {"agent": "Operations Agent", "intent": "procurement", "status": "needs_more_info",
                "answer": f"I found shortages for:\n{choices}\n\nWhich material should I source first?",
                "pending_material_selection": {"materials": [
                    {name: item.get(name) for name in
                     ("material_code", "material_name", "shortage", "unit")}
                    for item in materials
                ]},
                "workflow": ["Operations Agent"], "requires_approval": False}
    from agents.operations.operations_agent import _material_type_for_shortage

    item = materials[0]
    category_evidence = f"{item.get('material_code') or ''} {item.get('material_name') or ''}".lower()
    if not any(token in category_evidence for token in (
            "fab-", "fabric", "fleece", "cotton", "denim", "cloth", "dye", "btn-", "button",
            "zipper", "thr-", "thread", "lbl-", "label", "pkg-", "packaging")):
        return {"agent": "Operations Agent", "intent": "procurement", "status": "needs_more_info",
                "answer": "I found the shortage, but its supplier category needs verification before sourcing.",
                "workflow": ["Operations Agent"], "requires_approval": False}
    material_type, requirement_id, _ = _material_type_for_shortage(item["material_code"], item.get("material_name"))
    if material_type not in {"fabric_mill", "trim_vendor", "dye_house"}:
        return {"agent": "Operations Agent", "intent": "procurement", "status": "needs_more_info",
                "answer": "I found the shortage, but its supplier category needs verification before sourcing.",
                "workflow": ["Operations Agent"], "requires_approval": False}
    requirements = {"material_type": material_type, "requirement_id": requirement_id,
                    "material_name": item.get("material_name") or item["material_code"],
                    "material_code": item["material_code"], "qty": item["shortage"],
                    "unit": item.get("unit") or "units", "compliance_keywords": [],
                    "destination": "Colombo, Sri Lanka"}
    suppliers = [supplier for supplier in _supplier_options(requirements)
                 if supplier.get("estimated_total") is not None]
    if not suppliers:
        return {"agent": "Operations Agent", "intent": "procurement", "status": "partial",
                "answer": f"I found the {item['shortage']:,.0f} {requirements['unit']} shortage of {requirements['material_name']}, but no supplier is currently listed for this material category.",
                "workflow": ["Operations Agent", "Supply Chain Agent"], "requires_approval": False}
    procurement_sessions[session_id] = {"phase": "selecting", "history": [],
                                        "requirements": requirements, "suppliers": suppliers,
                                        "owner_id": (principal.get() or {}).get("user_id")}
    return {"agent": "Supply Chain Agent", "task": "Select Supplier", "intent": "procurement",
            "status": "selecting", "answer": f"The order is short of {item['shortage']:,.0f} {requirements['unit']} of {requirements['material_name']} ({item['material_code']}). Please select a supplier to draft a purchase order; manager approval will still be required.",
            "suppliers": suppliers, "workflow": ["Operations Agent", "Supply Chain Agent"],
            "requires_approval": False}


def handle_procurement_turn(session_id: str, request: AskRequest):
    from backend.supply_chain.supervisor import gather_requirements
    from backend.supply_chain.orchestrator import start_pipeline
    import asyncio
    
    if session_id not in procurement_sessions or isinstance(procurement_sessions.get(session_id), list):
        procurement_sessions[session_id] = {"phase": "gathering", "history": [], "requirements": {},
                                            "owner_id": (principal.get() or {}).get("user_id")}
        
    session = procurement_sessions[session_id]
    if session.get("owner_id") and session["owner_id"] != (principal.get() or {}).get("user_id"):
        raise HTTPException(status_code=403, detail="This procurement session belongs to another user.")
    
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
            # Only trigger the shade selection UI if we are actually asking for a shade and have shades generated
            if "shade of" in q_lower or ("shade" in q_lower and decision.get("shades")):
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
            session["suppliers"] = suppliers
            
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
            
        submitted = payload["supplier"]
        selected_supplier = next((item for item in session.get("suppliers", [])
            if isinstance(submitted, dict) and item.get("supplier_id") == submitted.get("supplier_id")
            and item.get("name") == submitted.get("name")), None)
        if selected_supplier is None or selected_supplier.get("estimated_total") is None:
            return {"agent": "Supply Chain Agent", "task": "Select Supplier",
                    "intent": "procurement", "status": "selecting",
                    "answer": "Please select a listed supplier with a verified price before drafting a purchase order."}
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
                "color_base": decision.get("color_base"),
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


@app.get("/readiness")
def readiness():
    from backend.readiness import system_readiness
    return system_readiness()


@app.get("/agent-activity")
def agent_activity(limit: int = 50):
    limit = max(1, min(limit, 200))

    try:
        from database.connection import db
        records = list(
            db["agent_activity"]
            .find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        if records:
            return records
    except Exception as error:
        print(f"Agent activity fallback: {error}")

    return list(reversed(agent_activity_log[-limit:]))


# ============================================================
# OPERATIONS AGENT
# ============================================================

import uuid

@app.post("/ask")
def ask_agent(request: AskRequest):
    from backend.agent_progress import progress_scope
    with progress_scope(request.request_id or str(uuid.uuid4())):
        return _process_ask(request)


@app.get("/ask/progress/{request_id}")
def ask_progress(request_id: str):
    from backend.agent_progress import get_progress
    return get_progress(request_id)


def _process_ask(request: AskRequest):

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        # Check active session
        session_id = request.session_id
        from agents.operations import process_request
        from agents.operations.conversation_context import (
            clear_pending_material_selection, compare_recent, contextual_shortages,
            get_context, remember_context, resolve_pending_material_selection,
        )
        user_id = (principal.get() or {}).get("user_id")

        # User text cannot impersonate a system/manager message to reach the
        # approval-followup path before the Operations security boundary.
        from agents.operations.operations_agent import _prompt_attack_kind
        if _prompt_attack_kind(request.message):
            return process_request(request.message)

        context = get_context(session_id, user_id)
        pending_selection = resolve_pending_material_selection(request.message, context)
        if pending_selection:
            if pending_selection["status"] == "cancelled":
                clear_pending_material_selection(session_id, user_id)
                return {"agent": "Operations Agent", "intent": "procurement",
                        "status": "cancelled",
                        "answer": "Okay. No procurement action was started.",
                        "workflow": ["Operations Agent"], "requires_approval": False}
            if pending_selection["status"] == "selected":
                clear_pending_material_selection(session_id, user_id)
                result = _start_contextual_procurement(
                    session_id, [pending_selection["material"]])
                remember_context(session_id, user_id, result)
                record_agent_activity("Selected verified shortage material", result, session_id, "Medium")
                return result
            choices = " or ".join(
                item.material_name for item in context.pending_material_selection.materials)
            return {"agent": "Operations Agent", "intent": "procurement",
                    "status": "needs_more_info",
                    "answer": f"I couldn't match that to one of the shortage materials. Please choose {choices}.",
                    "workflow": ["Operations Agent"], "requires_approval": False}

        shortages = contextual_shortages(request.message, context)
        if shortages and session_id and session_id not in procurement_sessions:
            result = _start_contextual_procurement(session_id, shortages)
            remember_context(session_id, user_id, result)
            record_agent_activity("Contextual production-shortage sourcing", result, session_id, "Medium")
            return result

        if is_approval_followup(request.message, session_id):
            return handle_approval_followup(session_id, request)

        if is_contextual_low_stock_order(request.message, session_id):
            if session_id and session_id in procurement_sessions:
                del procurement_sessions[session_id]

            result = process_request("order these low stock materials")
            result["workflow"] = compact_workflow(result.get("workflow"))
            remember_operations_context(session_id, result)
            remember_context(session_id, user_id, result)
            record_agent_activity("Contextual low-stock order", result, session_id, "Medium")
            return result

        msg_lower = request.message.lower()
        is_restart = session_id and session_id in procurement_sessions and procurement_sessions[session_id].get("phase") == "selecting" and any(w in msg_lower for w in ("buy ", "order ", "need ", "want ", "procure "))
        
        if session_id and session_id in procurement_sessions and (is_low_stock_supply_chain_request(request.message) or is_restart):
            del procurement_sessions[session_id]

        if session_id and session_id in procurement_sessions:
            result = handle_procurement_turn(session_id, request)
            result["workflow"] = compact_workflow(result.get("workflow"))
            remember_operations_context(session_id, result)
            remember_context(session_id, user_id, result)
            record_agent_activity("Procurement session turn", result, session_id, "Medium")
            return result

        if request.message.strip().lower() in {"would that be safer?", "would that be safer", "is that safer?", "is that safer"}:
            comparison = compare_recent(context)
            if comparison:
                result = {"agent": "Operations Agent", "intent": "scenario_comparison",
                          "status": "success", "answer": comparison,
                          "workflow": ["Operations Agent"], "graph": ["Operations Agent"],
                          "requires_approval": False, "evidence_sources": ["session_decisions"]}
                record_agent_activity("Compared verified scenarios", result, session_id)
                return result
            if context and context.current_goal.get("objective") == "evaluate_order_feasibility":
                return {"agent": "Operations Agent", "intent": "scenario_comparison",
                        "status": "needs_more_info",
                        "answer": "I need two verified scenarios to compare. What quantity or deadline should I check against the current plan?",
                        "workflow": ["Operations Agent"], "graph": ["Operations Agent"],
                        "requires_approval": False}

        result = process_request(request.message, context=context)
        result["workflow"] = compact_workflow(result.get("workflow"))
        remember_operations_context(session_id, result)
        remember_context(session_id, user_id, result)
        record_agent_activity("Ask Omni request processed", result, session_id)

        if result.get("status") == "init_session":
            # Start new session
            new_session = session_id or str(uuid.uuid4())
            result["session_id"] = new_session
            # Immediately take the first turn
            result = handle_procurement_turn(new_session, request)
            result["workflow"] = compact_workflow(result.get("workflow"))
            remember_context(new_session, user_id, result)
            record_agent_activity("Procurement session started", result, new_session, "Medium")
            return result

        return result

    except HTTPException:
        raise
    except Exception as error:
        print(f"Operations Agent error: {error}")
        raise HTTPException(status_code=500, detail="Operations Agent failed to process the request.")



# ============================================================
# DEMAND FORECAST AGENT
# ============================================================

@app.get("/forecast/data-quality/{sku}")
def demand_quality(sku: str):
    try:
        from backend.mcp.factory_operations.client import get_demand_quality
        return get_demand_quality(sku)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"message": str(error)})
    except Exception:
        raise HTTPException(status_code=503, detail={"message": "Unable to check demand data. Check MongoDB connectivity."})


@app.get("/forecast/products")
def forecast_products():
    try:
        from backend.mcp.factory_operations.client import get_forecast_products
        return {"products": get_forecast_products()}
    except Exception:
        raise HTTPException(status_code=503, detail={"message": "Unable to load products from MongoDB. Check database connectivity and MONGO_URI."})


@app.post("/forecast")
def demand_forecast(request: ForecastRequest):
    """Send a demand-forecast request through the Factory Operations MCP server."""
    from backend.mcp.factory_operations.client import forecast_demand

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
        from backend.mcp.factory_operations.client import check_inventory

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
# INVENTORY - ADD OR UPDATE MATERIAL
# ============================================================

@app.post("/inventory")
def add_inventory(request: InventoryCreateRequest):

    try:
        from backend.mcp.factory_operations.client import add_inventory_item

        return add_inventory_item(
            material_name=request.material_name,
            current_stock=request.current_stock,
            reorder_level=request.reorder_level,
            unit=request.unit,
            material_code=request.material_code,
            classification=request.classification,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        print(
            f"Add inventory error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to save inventory material."
        )


# ============================================================
# INVENTORY — LOW STOCK
# ============================================================

@app.get("/inventory/low-stock")
def low_stock():

    try:
        from backend.mcp.factory_operations.client import get_low_stock

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
        from backend.mcp.factory_operations.client import get_material

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
        from backend.mcp.factory_operations.client import get_total_stock

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
        from backend.mcp.factory_operations.client import get_all_lines

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
        from backend.mcp.factory_operations.client import get_line_utilization

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
        from backend.mcp.factory_operations.client import identify_bottlenecks

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
        from backend.mcp.factory_operations.client import get_production_orders

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
        from backend.mcp.factory_operations.client import get_production_progress

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
# PRODUCTION — FEASIBILITY THROUGH FACTORY OPERATIONS MCP
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
        from backend.mcp.factory_operations.client import check_production_feasibility

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
        from backend.mcp.factory_operations.client import get_production_kpis

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
        from backend.mcp.factory_operations.client import get_production_summary

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
        from backend.mcp.factory_operations.client import get_producible_products

        return get_producible_products()

    except Exception as error:

        print(
            f"Producible products error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve producible products."
        )
