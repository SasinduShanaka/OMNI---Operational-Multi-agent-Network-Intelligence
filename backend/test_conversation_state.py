"""Regression tests for verified production-to-procurement follow-ups."""

import unittest
from unittest.mock import patch


class ConversationStateTests(unittest.TestCase):
    @staticmethod
    def _black_polo_shortage_response():
        return {
            "intent": "operational_plan", "status": "success",
            "goal": {"objective": "evaluate_order_feasibility",
                     "product_name": "Classic Black Polo", "quantity": 10000,
                     "deadline": "2026-12-01"},
            "result": {"production": {"status": "INFEASIBLE", "blocking_materials": [
                {"material_name": "Black Cotton Fabric", "material_code": "FAB-001",
                 "required": 12000, "available": 3200, "shortage": 8800,
                 "unit": "meters", "status": "SHORTAGE"},
                {"material_name": "Polo Buttons", "material_code": "BTN-001",
                 "required": 30000, "available": 25000, "shortage": 5000,
                 "unit": "pieces", "status": "SHORTAGE"},
            ]}},
        }

    def test_multiple_shortages_create_pending_material_selection(self):
        from agents.operations.conversation_context import get_context, remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask

        remember_context("multi-shortage-session", "multi-shortage-user",
                         self._black_polo_shortage_response())
        token = principal.set({"user_id": "multi-shortage-user", "role": "operator"})
        self.addCleanup(principal.reset, token)
        with patch("backend.main.record_agent_activity"):
            result = _process_ask(AskRequest(
                message="Place order for above shortage materials",
                session_id="multi-shortage-session"))

        state = get_context("multi-shortage-session", "multi-shortage-user")
        pending = getattr(state, "pending_material_selection", None)
        self.assertEqual(result["status"], "needs_more_info")
        self.assertIsNotNone(pending)
        self.assertEqual([item.material_code for item in pending.materials],
                         ["FAB-001", "BTN-001"])
        self.assertEqual(pending.materials[0].shortage, 8800)

    def test_material_name_selection_uses_verified_production_shortage(self):
        from agents.operations.conversation_context import get_context, remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask, procurement_sessions

        session_id = "material-name-session"
        user_id = "material-name-user"
        remember_context(session_id, user_id, self._black_polo_shortage_response())
        token = principal.set({"user_id": user_id, "role": "operator"})
        self.addCleanup(principal.reset, token)
        self.addCleanup(procurement_sessions.pop, session_id, None)
        with patch("backend.main.record_agent_activity"), \
             patch("backend.main._supplier_options", return_value=[
                 {"supplier_id": 1, "name": "Verified Mill", "estimated_total": 100.0}
             ]), \
             patch("agents.operations.process_request", return_value={
                 "intent": "material_status", "status": "success", "answer": "Reorder gap: 300"
             }):
            _process_ask(AskRequest(
                message="Place order for above shortage materials", session_id=session_id))
            result = _process_ask(AskRequest(
                message="Black cotton fabric", session_id=session_id))

        state = get_context(session_id, user_id)
        self.assertEqual(result["intent"], "procurement")
        self.assertEqual(result["status"], "selecting")
        self.assertEqual(procurement_sessions[session_id]["requirements"]["material_code"], "FAB-001")
        self.assertEqual(procurement_sessions[session_id]["requirements"]["qty"], 8800)
        self.assertNotEqual(procurement_sessions[session_id]["requirements"]["qty"], 300)
        self.assertIsNone(state.pending_material_selection)
        self.assertEqual(len(state.blocking_materials), 2)

    def test_pending_material_selection_supports_codes_names_and_ordinals(self):
        from agents.operations.conversation_context import (
            ConversationContext, PendingMaterialSelection,
            resolve_pending_material_selection,
        )
        context = ConversationContext(pending_material_selection=PendingMaterialSelection(
            materials=[
                {"material_code": "FAB-001", "material_name": "Black Cotton Fabric",
                 "shortage": 8800, "unit": "meters"},
                {"material_code": "BTN-001", "material_name": "Polo Buttons",
                 "shortage": 5000, "unit": "pieces"},
            ]))
        cases = {
            "FAB-001": "FAB-001",
            "cotton fabric": "FAB-001",
            "the fabric": "FAB-001",
            "first one": "FAB-001",
            "1": "FAB-001",
            "Polo buttons": "BTN-001",
            "buttons": "BTN-001",
            "BTN-001": "BTN-001",
            "second one": "BTN-001",
            "2": "BTN-001",
        }
        for message, expected_code in cases.items():
            with self.subTest(message=message):
                result = resolve_pending_material_selection(message, context)
                self.assertEqual(result["status"], "selected")
                self.assertEqual(result["material"]["material_code"], expected_code)

    def test_invalid_pending_material_selection_does_not_start_procurement(self):
        from agents.operations.conversation_context import get_context, remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask, procurement_sessions

        session_id = "invalid-selection-session"
        user_id = "invalid-selection-user"
        remember_context(session_id, user_id, self._black_polo_shortage_response())
        token = principal.set({"user_id": user_id, "role": "operator"})
        self.addCleanup(principal.reset, token)
        with patch("backend.main.record_agent_activity"):
            _process_ask(AskRequest(
                message="Place order for above shortage materials", session_id=session_id))
            result = _process_ask(AskRequest(message="fabric thing", session_id=session_id))

        self.assertEqual(result["status"], "needs_more_info")
        self.assertNotIn(session_id, procurement_sessions)
        self.assertIsNotNone(get_context(session_id, user_id).pending_material_selection)

    def test_cancel_clears_pending_selection_without_starting_procurement(self):
        from agents.operations.conversation_context import get_context, remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask, procurement_sessions

        session_id = "cancel-selection-session"
        user_id = "cancel-selection-user"
        remember_context(session_id, user_id, self._black_polo_shortage_response())
        token = principal.set({"user_id": user_id, "role": "operator"})
        self.addCleanup(principal.reset, token)
        with patch("backend.main.record_agent_activity"):
            _process_ask(AskRequest(
                message="Place order for above shortage materials", session_id=session_id))
            result = _process_ask(AskRequest(
                message="don't order anything", session_id=session_id))

        self.assertEqual(result["status"], "cancelled")
        self.assertNotIn(session_id, procurement_sessions)
        self.assertIsNone(get_context(session_id, user_id).pending_material_selection)

    def test_pending_material_selection_does_not_leak_between_users(self):
        from agents.operations.conversation_context import remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask, procurement_sessions

        session_id = "shared-session-id"
        remember_context(session_id, "user-a", self._black_polo_shortage_response())
        token_a = principal.set({"user_id": "user-a", "role": "operator"})
        with patch("backend.main.record_agent_activity"):
            _process_ask(AskRequest(
                message="Place order for above shortage materials", session_id=session_id))
        principal.reset(token_a)

        token_b = principal.set({"user_id": "user-b", "role": "operator"})
        self.addCleanup(principal.reset, token_b)
        with patch("backend.main.record_agent_activity"), \
             patch("agents.operations.process_request", return_value={
                 "intent": "material_status", "status": "success", "answer": "Inventory result"
             }):
            result = _process_ask(AskRequest(
                message="Black cotton fabric", session_id=session_id))

        self.assertEqual(result["intent"], "material_status")
        self.assertNotIn(session_id, procurement_sessions)

    def test_new_production_assessment_clears_old_pending_selection(self):
        from agents.operations.conversation_context import get_context, remember_context
        from backend.auth import principal
        from backend.main import AskRequest, _process_ask

        session_id = "new-production-topic-session"
        user_id = "new-production-topic-user"
        remember_context(session_id, user_id, self._black_polo_shortage_response())
        token = principal.set({"user_id": user_id, "role": "operator"})
        self.addCleanup(principal.reset, token)
        with patch("backend.main.record_agent_activity"):
            _process_ask(AskRequest(
                message="Place order for above shortage materials", session_id=session_id))
        self.assertIsNotNone(get_context(session_id, user_id).pending_material_selection)

        replacement = self._black_polo_shortage_response()
        replacement["goal"] = {
            "objective": "evaluate_order_feasibility", "product_name": "Blue Denim Jacket",
            "quantity": 2000, "deadline": "2026-12-15",
        }
        replacement["result"]["production"]["blocking_materials"] = [{
            "material_name": "Blue Denim", "material_code": "FAB-003",
            "required": 4000, "available": 1000, "shortage": 3000,
            "unit": "meters", "status": "SHORTAGE",
        }]
        remember_context(session_id, user_id, replacement)

        self.assertIsNone(get_context(session_id, user_id).pending_material_selection)

    def test_remaining_verified_shortage_can_be_requested_by_name(self):
        from agents.operations.conversation_context import contextual_shortages, get_context, remember_context

        session_id = "remaining-shortage-session"
        user_id = "remaining-shortage-user"
        remember_context(session_id, user_id, self._black_polo_shortage_response())
        state = get_context(session_id, user_id)

        shortages = contextual_shortages("now do the buttons", state)

        self.assertEqual(len(shortages), 1)
        self.assertEqual(shortages[0]["material_code"], "BTN-001")
        self.assertEqual(shortages[0]["shortage"], 5000)

    def test_verified_shortage_is_available_for_contextual_procurement(self):
        from agents.operations.conversation_context import get_context, remember_context
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
        from agents.operations.conversation_context import get_context, remember_context
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

    def test_new_topic_clears_old_order_shortages(self):
        from agents.operations.conversation_context import contextual_shortages, get_context, remember_context
        remember_context("topic-switch", "topic-user", {
            "intent": "operational_plan", "status": "success",
            "goal": {"objective": "evaluate_order_feasibility", "product_name": "Grey Hoodie", "quantity": 5000},
            "result": {"production": {"status": "AT_RISK", "blocking_materials": [{
                "status": "SHORTAGE", "material_code": "FAB-004", "shortage": 8200}]}}})
        remember_context("topic-switch", "topic-user", {
            "intent": "inventory_status", "status": "success", "result": {"items": []}})
        state = get_context("topic-switch", "topic-user")
        self.assertEqual(contextual_shortages("Order the insufficient materials for this order", state), [])


if __name__ == "__main__":
    unittest.main()
