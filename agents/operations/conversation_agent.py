"""Tool-free presentation of verified operational conclusions."""


def _amount(value) -> str:
    return f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)


def compose_answer(response: dict, context=None) -> str:
    """Explain cause, impact and next step using only values in verified results."""
    if response.get("status") in {"blocked", "needs_more_info", "init_session"}:
        return response.get("answer", "")
    if response.get("intent") != "operational_plan":
        return response.get("answer", "")
    result = response.get("result") or {}
    goal = result.get("goal") or response.get("goal") or {}
    production = result.get("production") or {}
    conditional = result.get("conditional_capacity") or {}
    sourcing = result.get("sourcing") or {}
    quantity = goal.get("quantity") or goal.get("required_quantity")
    deadline = goal.get("deadline") or goal.get("required_date")
    if response.get("status") == "partial" and production.get("status") not in {"FEASIBLE", "AT_RISK", "INFEASIBLE"}:
        return response.get("answer", "")
    if not production:
        return response.get("answer", "")
    name = goal.get("product_name") or goal.get("sku") or "this product"
    subject = f"the {_amount(quantity)}-unit {name} order" if quantity else f"the {name} order"
    if deadline:
        subject += f" by {deadline}"
    verdict = conditional.get("status") or production.get("status")
    if verdict == "FEASIBLE" and response.get("status") == "success":
        opening = f"Based on the current records, {subject} fits the available production window."
    elif verdict == "INFEASIBLE":
        opening = f"I wouldn't commit to {subject} yet. The current production window does not fit the full quantity."
    else:
        opening = f"We may be able to take {subject}, but I wouldn't commit to the deadline yet."
    parts = [opening]
    shortages = [item for item in production.get("blocking_materials", []) if item.get("status") == "SHORTAGE"]
    if shortages:
        parts.append("The material constraint is " + "; ".join(
            f"{item.get('material_name') or item.get('material_code')} (short by {_amount(item.get('shortage'))} {item.get('unit', 'units')})"
            for item in shortages) + ".")
    if conditional.get("conditional_on_material_arrival") or conditional.get("lead_time_days") is not None:
        parts.append(f"With the estimated {conditional.get('lead_time_days')}-day material lead time, "
                     f"Production can fit about {_amount(conditional.get('producible_quantity'))} units at spare capacity. "
                     "That estimate assumes current utilization stays the same.")
    if sourcing.get("errors"):
        parts.append("Some supplier checks remain unresolved and need review.")
    forecast = (response.get("evidence") or {}).get("forecast") or []
    if forecast and forecast[-1].get("status") == "error":
        parts.append("Demand forecasting was unavailable; this assessment uses current production evidence.")
    if response.get("contradictions"):
        parts.append("The evidence conflicts, so I need a verified recheck before treating this as a commitment.")
    if response.get("status") == "partial" and not response.get("contradictions"):
        parts.append("This is a partial assessment because some required evidence could not be verified.")
    if shortages and not goal.get("draft_authorized"):
        parts.append("No purchase order was created for this feasibility check.")
    return " ".join(parts)
