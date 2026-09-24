"""Read-only evidence critic; never calls operational or purchasing tools."""

from agents.schemas import AgentRequest, ReviewResult

MAX_REVIEW_ROUNDS = 2


def review_evidence(goal: dict, evidence: dict,
                    proposed_conclusion: dict | None = None) -> ReviewResult:
    """Check required evidence and cross-domain consistency once per review round."""
    issues, missing, contradictions, actions = [], [], [], []
    if goal.get("objective") == "evaluate_order_feasibility":
        production = (evidence.get("production") or [{}])[-1].get("facts") or {}
        if production.get("status") not in {"FEASIBLE", "AT_RISK", "INFEASIBLE"}:
            missing.append("Verified production feasibility")
            issues.append("The production commitment has no verified feasibility verdict.")
        blocking = [item for item in production.get("blocking_materials", [])
                    if item.get("status") in {"SHORTAGE", "MISSING_RECORD"}]
        if production.get("status") == "FEASIBLE" and blocking:
            contradictions.append("Production reports FEASIBLE while materials are blocking.")
        if proposed_conclusion:
            for key in ("status", "producible_quantity", "shortfall"):
                proposed = proposed_conclusion.get(key)
                verified = production.get(key)
                if proposed is not None and (verified is None or proposed != verified):
                    issues.append(f"Unsupported {key} claim in the proposed conclusion.")
        inventory = (evidence.get("inventory") or [{}])[-1].get("facts") or {}
        if isinstance(inventory, dict) and inventory.get("shortage", 0) > 0 and production.get("status") == "FEASIBLE":
            contradictions.append("Inventory shortage conflicts with the Production feasible verdict.")
        if contradictions:
            actions.append(AgentRequest(target_agent="production",
                task="Reassess feasibility against the conflicting material evidence.",
                reason="Production and material availability disagree.",
                required_facts=["revised_feasibility", "blocking_materials"]))
    return ReviewResult(valid=not (issues or missing or contradictions), issues=issues,
                        missing_checks=missing, contradictions=contradictions,
                        recommended_actions=actions)
