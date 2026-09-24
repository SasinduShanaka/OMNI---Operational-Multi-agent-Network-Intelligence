"""Bounded, per-user short-term operational context; no prompts or credentials."""

import re
from datetime import date, datetime, timezone
from threading import Lock

from pydantic import BaseModel, Field


CONTEXT_TTL_SECONDS = 15 * 60
EVIDENCE_TTL_SECONDS = 5 * 60
MAX_CONTEXTS = 500


class ProcurementMaterialChoice(BaseModel):
    material_code: str
    material_name: str
    shortage: float
    unit: str = "units"


class PendingMaterialSelection(BaseModel):
    materials: list[ProcurementMaterialChoice] = Field(default_factory=list)


class ConversationContext(BaseModel):
    session_id: str | None = None
    active_topic: str | None = None
    active_goal: dict = Field(default_factory=dict)
    last_business_intent: str | None = None
    last_conversation_intent: str | None = None
    current_goal: dict = Field(default_factory=dict)
    entities: dict = Field(default_factory=dict)
    current_product: dict | None = None
    current_order: dict | None = None
    referenced_materials: list[dict] = Field(default_factory=list)
    blocking_materials: list[dict] = Field(default_factory=list)
    production_findings: dict = Field(default_factory=dict)
    inventory_findings: dict = Field(default_factory=dict)
    forecast_findings: dict = Field(default_factory=dict)
    supplier_options: list[dict] = Field(default_factory=list)
    selected_supplier: dict | None = None
    pending_approvals: list[dict] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    recent_turns: list[dict] = Field(default_factory=list)
    previous_decisions: list[dict] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    open_actions: list[dict] = Field(default_factory=list)
    pending_material_selection: PendingMaterialSelection | None = None
    agent_findings: dict = Field(default_factory=dict)
    unresolved_risks: list[str] = Field(default_factory=list)
    last_user_intent: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


ConversationState = ConversationContext


_contexts: dict[str, ConversationContext] = {}
_lock = Lock()


def _key(session_id: str, user_id: str) -> str:
    return f"{user_id}:{session_id}"


def get_context(session_id: str | None, user_id: str | None) -> ConversationContext | None:
    if not session_id or not user_id:
        return None
    with _lock:
        context = _contexts.get(_key(session_id, user_id))
        if context and (datetime.now(timezone.utc) - context.updated_at).total_seconds() <= CONTEXT_TTL_SECONDS:
            return context.model_copy(deep=True)
        if context:
            _contexts.pop(_key(session_id, user_id), None)
    return None


def remember_pending_approvals(session_id: str | None, user_id: str | None,
                               pending: list[dict]) -> None:
    """Store only server-returned pending PO identifiers for this principal."""
    if not session_id or not user_id:
        return
    key = _key(session_id, user_id)
    with _lock:
        context = _contexts.get(key) or ConversationContext(session_id=session_id)
        context.pending_approvals = [{name: item.get(name) for name in
            ("run_id", "po_id", "supplier", "material", "status")}
            for item in pending[:20] if item.get("run_id")]
        context.updated_at = datetime.now(timezone.utc)
        if len(_contexts) >= MAX_CONTEXTS and key not in _contexts:
            oldest = min(_contexts, key=lambda item: _contexts[item].updated_at)
            _contexts.pop(oldest, None)
        _contexts[key] = context


def remember_context(session_id: str | None, user_id: str | None, response: dict) -> None:
    """Keep only structured business state; never store prompts or secrets."""
    if not session_id or not user_id or response.get("status") == "blocked":
        return
    goal = response.get("goal") or {}
    if goal.get("objective") != "evaluate_order_feasibility":
        key = _key(session_id, user_id)
        with _lock:
            context = _contexts.get(key) or ConversationContext()
            context.session_id = session_id
            context.last_business_intent = response.get("intent")
            context.last_conversation_intent = "procurement" if response.get("intent") == "procurement" else "other"
            context.recent_turns = [*context.recent_turns[-4:], {"intent": response.get("intent"),
                "status": response.get("status")}]
            if response.get("intent") not in {"procurement", "approval_followup"}:
                context.active_topic = response.get("intent")
                context.active_goal = {}
                context.current_goal = {}
                context.current_order = None
                context.current_product = None
                context.blocking_materials = []
                context.referenced_materials = []
                context.production_findings = {}
                context.pending_material_selection = None
            if response.get("intent") == "procurement":
                context.supplier_options = [{name: item.get(name) for name in
                    ("supplier_id", "name", "category", "lead_time_days", "rating", "estimated_total")}
                    for item in (response.get("suppliers") or [])[:20] if isinstance(item, dict)]
                if response.get("pending_material_selection"):
                    context.pending_material_selection = PendingMaterialSelection.model_validate(
                        response["pending_material_selection"])
            if response.get("intent") == "low_stock_procurement" and response.get("status") == "success":
                context.inventory_findings = {"low_stock": [{name: item.get(name) for name in
                    ("material_code", "material_name", "current_stock", "reorder_level", "unit")}
                    for item in (response.get("results") or [])[:20] if isinstance(item, dict)]}
            context.updated_at = datetime.now(timezone.utc)
            if len(_contexts) >= MAX_CONTEXTS and key not in _contexts:
                oldest = min(_contexts, key=lambda item: _contexts[item].updated_at)
                _contexts.pop(oldest, None)
            _contexts[key] = context
        return
    key = _key(session_id, user_id)
    with _lock:
        context = _contexts.get(key) or ConversationContext()
        context.session_id = session_id
        context.active_topic = "production_order"
        context.active_goal = {name: goal.get(name) for name in
                               ("objective", "product_name", "sku", "quantity", "deadline")}
        context.last_business_intent = response.get("intent")
        context.last_conversation_intent = "assessment"
        context.pending_material_selection = None
        context.current_goal = {name: goal.get(name) for name in
                                ("objective", "product_name", "sku", "quantity", "deadline")}
        context.entities = {name: goal.get(name) for name in ("product_name", "sku", "quantity", "deadline")}
        context.current_product = {name: goal.get(name) for name in ("product_name", "sku")}
        context.current_order = {name: goal.get(name) for name in ("product_name", "sku", "quantity", "deadline")}
        context.last_user_intent = response.get("intent")
        context.pending_questions = [response.get("answer", "")[:160]] if response.get("status") == "needs_more_info" else []
        context.unresolved_questions = context.pending_questions.copy()
        result = response.get("result") or {}
        production = result.get("production") or {}
        verified_shortages = []
        review = response.get("review") or {}
        if (response.get("status") in {"success", "partial"} and
                production.get("status") in {"AT_RISK", "INFEASIBLE"} and
                not response.get("contradictions") and review.get("valid", True)):
            for item in production.get("blocking_materials", [])[:20]:
                if (item.get("status") == "SHORTAGE" and item.get("material_code") and
                        isinstance(item.get("shortage"), (int, float)) and item["shortage"] > 0):
                    verified_shortages.append({name: item.get(name) for name in
                        ("material_code", "material_name", "required", "available", "shortage", "unit", "status")})
        context.blocking_materials = verified_shortages
        context.referenced_materials = verified_shortages
        context.production_findings = {"status": production.get("status"),
                                       "blocking_materials": verified_shortages}
        context.recent_turns = [*context.recent_turns[-4:], {"intent": response.get("intent"),
            "status": response.get("status"), "goal": context.current_goal.copy()}]
        conditional = result.get("conditional_capacity") or {}
        context.previous_decisions = [*context.previous_decisions[-3:], {
            "quantity": goal.get("quantity"), "deadline": goal.get("deadline"),
            "status": response.get("status"), "production_status": production.get("status"),
            "conditional_status": conditional.get("status"),
            "producible_quantity": conditional.get("producible_quantity"),
        }]
        context.unresolved_risks = [str(risk)[:200] for risk in response.get("risks", [])[:10]]
        sourcing = result.get("sourcing") or {}
        if sourcing.get("status") == "success" and sourcing.get("options") and not sourcing.get("errors"):
            context.agent_findings["sourcing"] = {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "lead_time_days": sourcing.get("lead_time_days"),
                "options": [{"material_code": option.get("material_code"),
                             "material_name": option.get("material_name"),
                             "lead_time_days": option.get("lead_time_days"),
                             "supplier": {key: (option.get("supplier") or {}).get(key)
                                          for key in ("supplier_id", "supplier_name", "rating")}}
                            for option in sourcing["options"][:10]],
            }
        context.updated_at = datetime.now(timezone.utc)
        if len(_contexts) >= MAX_CONTEXTS:
            oldest = min(_contexts, key=lambda item: _contexts[item].updated_at)
            _contexts.pop(oldest, None)
        _contexts[key] = context


def clear_pending_material_selection(session_id: str | None, user_id: str | None) -> None:
    """Clear only the pending material question, preserving verified shortages."""
    if not session_id or not user_id:
        return
    key = _key(session_id, user_id)
    with _lock:
        context = _contexts.get(key)
        if context:
            context.pending_material_selection = None
            context.pending_questions = []
            context.unresolved_questions = []
            context.updated_at = datetime.now(timezone.utc)


def resolve_pending_material_selection(message: str, context: ConversationContext | None) -> dict | None:
    """Resolve a reply only against the verified materials in the active question."""
    pending = context.pending_material_selection if context else None
    if not pending or not pending.materials:
        return None

    normalized = " ".join(re.findall(r"[a-z0-9]+", message.lower()))
    if normalized in {"cancel", "never mind", "nevermind", "stop", "dont order anything",
                      "don t order anything", "do not order anything"}:
        return {"status": "cancelled"}

    ordinal_words = {"first": 0, "first one": 0, "1": 0, "one": 0,
                     "second": 1, "second one": 1, "2": 1, "two": 1,
                     "third": 2, "third one": 2, "3": 2, "three": 2,
                     "fourth": 3, "fourth one": 3, "4": 3, "four": 3}
    if normalized in ordinal_words:
        index = ordinal_words[normalized]
        if index < len(pending.materials):
            return {"status": "selected", "material": pending.materials[index].model_dump()}

    query_tokens = set(normalized.split()) - {"the", "material"}
    matches = []
    for material in pending.materials:
        code = " ".join(re.findall(r"[a-z0-9]+", material.material_code.lower()))
        name = " ".join(re.findall(r"[a-z0-9]+", material.material_name.lower()))
        name_tokens = set(name.split())
        if normalized == code or normalized == name or (query_tokens and query_tokens <= name_tokens):
            matches.append(material)

    if len(matches) == 1:
        return {"status": "selected", "material": matches[0].model_dump()}
    return {"status": "ambiguous" if len(matches) > 1 else "no_match"}


def resolve_followup(message: str, context: ConversationContext | None) -> str:
    """Resolve only analytical follow-ups; never inherit purchase authority."""
    if not context or context.current_goal.get("objective") != "evaluate_order_feasibility":
        return message
    text = message.strip()
    lowered = text.lower()
    if re.search(r"\b(?:order|buy|purchase|approve|authorize|draft|place|submit|procure)\b", lowered):
        return message
    if not (context.pending_questions or re.search(r"\b(?:what if|what about|only take|instead|would that|safer|by|october|november|december|january|february|march|april|may|june|july|august|september)\b", lowered)):
        return message
    goal = context.current_goal
    product = goal.get("product_name") or goal.get("sku")
    if not product:
        return message
    quantity = goal.get("quantity")
    number = re.search(r"\b(?:what if|what about|only take|instead|make|produce)\s+(\d[\d,]*)\b", lowered)
    if number:
        quantity = int(number.group(1).replace(",", ""))
    deadline = goal.get("deadline")
    from agents.operations.operations_agent import _extract_date
    parsed_date = _extract_date(message)
    if parsed_date:
        deadline = parsed_date
    if not quantity or not deadline:
        return message
    return f"Can we produce {quantity:g} {product} by {deadline}?"


def contextual_shortages(message: str, context: ConversationContext | None) -> list[dict]:
    """Resolve an explicit procurement request against verified current-order shortages."""
    if not context or context.active_topic != "production_order" or context.pending_approvals:
        return []
    text = message.lower()
    if re.search(r"\b(?:do|order|buy|purchase|procure|source|draft)\b", text):
        ignored = {"now", "do", "order", "buy", "purchase", "procure", "source", "draft",
                   "the", "a", "an", "material", "materials", "shortage", "shortages", "next"}
        query_tokens = {token[:-1] if token.endswith("s") and len(token) > 3 else token
                        for token in re.findall(r"[a-z0-9]+", text)} - ignored
        named_matches = []
        for item in context.blocking_materials:
            code = " ".join(re.findall(r"[a-z0-9]+", str(item.get("material_code", "")).lower()))
            name_tokens = {token[:-1] if token.endswith("s") and len(token) > 3 else token
                           for token in re.findall(r"[a-z0-9]+", str(item.get("material_name", "")).lower())}
            if code and code in " ".join(re.findall(r"[a-z0-9]+", text)):
                named_matches.append(item)
            elif query_tokens & name_tokens:
                named_matches.append(item)
        if len(named_matches) == 1:
            return [named_matches[0].copy()]
    if not re.search(r"\b(?:order|buy|purchase|procure|source|replenish|draft)\b", text):
        return []
    if not re.search(r"\b(?:insufficient|short|shortage|missing|blocking|needed|required)\b", text):
        return []
    if not re.search(r"\b(?:this order|the order|materials?|them|these|those)\b", text):
        return []
    if re.search(r"\b(?:ignore|bypass|skip)\b.*\b(?:approval|rules?|policy)\b", text):
        return []
    return [item.copy() for item in context.blocking_materials if item.get("shortage", 0) > 0]


def compare_recent(context: ConversationContext | None) -> str | None:
    """Answer a same-goal referent using saved verified verdicts, without a new tool call."""
    if not context or len(context.previous_decisions) < 2:
        return None
    before, after = context.previous_decisions[-2:]
    if before.get("status") != "success" or after.get("status") != "success":
        return None
    if before.get("quantity") == after.get("quantity") or not after.get("quantity"):
        return None
    if after["quantity"] < before["quantity"]:
        direction = "reduces the quantity that Production needs to fit into the schedule"
    else:
        direction = "increases the quantity that Production needs to fit into the schedule"
    verdict = after.get("conditional_status") or after.get("production_status") or "unverified"
    return (f"The revised {after['quantity']:,.0f}-unit order {direction}. "
            f"The latest verified assessment is {verdict}. I would use that result before making a commitment.")


def reusable_sourcing(context: dict | None, materials: list[dict]) -> dict | None:
    """Reuse recent read-only supplier evidence only for the same material set."""
    cached = ((context or {}).get("agent_findings") or {}).get("sourcing") or {}
    try:
        captured = datetime.fromisoformat(cached["captured_at"])
        if captured.tzinfo is None or (datetime.now(timezone.utc) - captured).total_seconds() > EVIDENCE_TTL_SECONDS:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    by_code = {item.get("material_code"): item for item in cached.get("options", [])}
    required_codes = {item.get("material_code") for item in materials}
    if not required_codes or None in required_codes or required_codes != set(by_code):
        return None
    options = [{**by_code[item["material_code"]],
                "shortage": item.get("shortage"), "unit": item.get("unit"),
                "estimated_cost": None, "price_basis": "not_recomputed"}
               for item in materials]
    return {"status": "success", "options": options, "errors": [],
            "lead_time_days": cached.get("lead_time_days"),
            "requires_approval": False, "purchase_orders_created": 0,
            "reused_from_session": True}
