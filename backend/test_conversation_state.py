"""Regression tests for verified production-to-procurement follow-ups."""

import unittest
from unittest.mock import patch


class ConversationStateTests(unittest.TestCase):
    def test_verified_shortage_is_available_for_contextual_procurement(self):
        from agents.conversation_context import get_context, remember_context
        response = {
            "intent": "operational_plan", "status": "success",
            "goal": {"objective": "evaluate_order_feasibility", "product_name": "Grey Hoodie",
                     "quantity": 5000, "deadline": "2026-12-01"},
            "result": {"production": {"status": "AT_RISK", "blocking_materials": [
                {"material_name": "Grey Fleece Fabric", "material_code": "FAB-004",
                 "required": 10000, "available": 1800, "shortage": 8200,
                 "unit": "meters", "status": "SHORTAGE"}]}}}
        remember_context("hoodie-session", "hoodie-user", response)
        state = get_context("hoodie-session", "hoodie-user")
        self.assertEqual(state.current_order["quantity"], 5000)
        self.assertEqual(state.blocking_materials[0]["material_code"], "FAB-004")
        self.assertEqual(state.blocking_materials[0]["shortage"], 8200)

    def test_contextual_order_uses_shortage_without_asking_material_again(self):
        from agents.conversation_context import get_context, remember_context
        from backend.main import AskRequest, _process_ask, procurement_sessions
        from backend.auth import principal
        response = {
            "intent": "operational_plan", "status": "success",
            "goal": {"objective": "evaluate_order_feasibility", "product_name": "Grey Hoodie",
                     "quantity": 5000, "deadline": "2026-12-01"},
            "result": {"production": {"status": "AT_RISK", "blocking_materials": [
                {"material_name": "Grey Fleece Fabric", "material_code": "FAB-004",
                 "shortage": 8200, "unit": "meters", "status": "SHORTAGE"}]}}}
        remember_context("hoodie-order-session", "hoodie-order-user", response)
        self.assertIsNotNone(get_context("hoodie-order-session", "hoodie-order-user"))
        token = principal.set({"user_id": "hoodie-order-user", "role": "operator"})
        self.addCleanup(principal.reset, token)
        self.addCleanup(procurement_sessions.pop, "hoodie-order-session", None)
        with patch("backend.main.record_agent_activity"), \
             patch("backend.main._supplier_options", return_value=[{"name": "Fleece Pro Pakistan", "estimated_total": 100.0}]):
            result = _process_ask(AskRequest(
                message="Can you order the insufficient materials to fulfill this order?",
                session_id="hoodie-order-session"))
        self.assertEqual(result["status"], "selecting")
        self.assertEqual(procurement_sessions["hoodie-order-session"]["requirements"]["qty"], 8200)
        self.assertEqual(procurement_sessions["hoodie-order-session"]["requirements"]["material_type"], "fabric_mill")
        self.assertFalse(result.get("requires_approval", False))

    def test_supplier_selection_rejects_unlisted_payload(self):
        from backend.main import AskRequest, handle_procurement_turn, procurement_sessions
        procurement_sessions["supplier-boundary"] = {
            "phase": "selecting", "history": [],
            "requirements": {"material_type": "fabric_mill", "requirement_id": 2,
                             "qty": 8200, "material_name": "Grey Fleece Fabric"},
            "suppliers": [{"supplier_id": 9, "name": "Verified Mill", "estimated_total": 82000.0}],
        }
        self.addCleanup(procurement_sessions.pop, "supplier-boundary", None)
        with patch("backend.supply_chain.orchestrator.start_pipeline") as pipeline:
            result = handle_procurement_turn("supplier-boundary", AskRequest(
                message="Select supplier", payload={"supplier": {"supplier_id": 10,
                    "name": "Injected Mill", "estimated_total": 1.0}}))
        self.assertEqual(result["status"], "selecting")
        pipeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()
