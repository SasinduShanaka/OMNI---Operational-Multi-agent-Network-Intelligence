"""Evaluation regressions using isolated records, with no external messages or database writes."""

import asyncio
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from backend.supply_chain import run_store
from backend.agent_progress import get_progress, progress_scope, report_progress

ROOT = Path(__file__).resolve().parent.parent


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connection = types.ModuleType("database.connection")
        connection.db = MagicMock()
        inventory = types.ModuleType("agents.inventory.inventory_agent")
        inventory.check_inventory_requirement = Mock()
        with patch.dict(sys.modules, {"database.connection": connection, "agents.inventory.inventory_agent": inventory}):
            cls.agent = load_module("evaluation_production", "agents/production/production_agent.py")

    def setUp(self):
        self.original_capacity = self.agent.check_capacity
        self.patches = patch.multiple(self.agent,
            resolve_sku=Mock(return_value="GAR-001"),
            products_collection=MagicMock(),
            check_capacity=Mock(return_value={"status": "FEASIBLE", "factors": [], "required_date": "2026-10-21"}),
            get_material_requirements=Mock(return_value=[]),
            check_inventory_requirement=Mock(),
            log_agent_activity=Mock(),
            _sop_notes_for_order=Mock(return_value=([], None)))
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.agent.products_collection.find_one.return_value = {"name": "Classic Black Polo"}

    def test_missing_bom_does_not_pass_feasibility(self):
        result = self.agent.check_production_feasibility(sku="GAR-001", quantity=100)
        self.assertEqual(result["status"], "NO_BOM")
        self.assertNotIn("All required materials are in stock", result["factors"])
        self.agent.check_inventory_requirement.assert_not_called()

    def test_shortage_changes_verdict_and_preserves_bom_evidence(self):
        self.agent.get_material_requirements.return_value = [
            {"material_code": "FAB-001", "qty_per_unit": 1.2, "required_quantity": 120, "unit": "meters"}]
        self.agent.check_inventory_requirement.return_value = {
            "status": "SHORTAGE", "material_code": "FAB-001", "material_name": "Cotton",
            "required_quantity": 120, "available_quantity": 20, "shortage": 100, "unit": "meters"}
        result = self.agent.check_production_feasibility(sku="GAR-001", quantity=100)
        self.assertEqual(result["status"], "AT_RISK")
        self.assertEqual(result["materials"][0]["request"]["qty_per_unit"], 1.2)
        self.assertEqual(result["blocking_materials"][0]["shortage"], 100)
        self.assertEqual(result["data_source"], "MongoDB")
        self.assertIsNotNone(datetime.fromisoformat(result["checked_at"]).tzinfo)

    def test_stock_and_capacity_pass_together(self):
        self.agent.get_material_requirements.return_value = [
            {"material_code": "FAB-001", "qty_per_unit": 1, "required_quantity": 100, "unit": "meters"}]
        self.agent.check_inventory_requirement.return_value = {"status": "SUFFICIENT"}
        result = self.agent.check_production_feasibility(sku="GAR-001", quantity=100)
        self.assertEqual(result["status"], "FEASIBLE")

    def test_tomorrow_is_not_reported_as_the_past(self):
        # Call the original capacity function, which setUp replaced for the other cases.
        with patch.object(self.agent, "get_line_for_sku", return_value={
            "line_id": "L1", "name": "Line 1", "working_days_per_week": 7,
            "spare_capacity_per_day": 200, "capacity_per_day": 500,
            "current_utilization": 60, "status": "AVAILABLE"}):
            result = self.original_capacity(
                sku="GAR-001", quantity=100, required_date=(date.today() + timedelta(days=1)).isoformat())
        self.assertEqual(result["days_available"], 1)
        self.assertEqual(result["status"], "FEASIBLE")


class ProcurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "erp.db"

        def connect():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

        self.connect = connect
        self.connection_patch = patch.object(run_store, "get_erp_db_connection", side_effect=connect)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        conn = connect()
        conn.execute("CREATE TABLE purchase_orders (po_id INTEGER PRIMARY KEY, status TEXT)")
        conn.execute("INSERT INTO purchase_orders VALUES (7, 'draft')")
        conn.commit()
        conn.close()
        self.state = {"status": "awaiting_approval", "po": {"po_id": 7, "status": "pending_approval"}}
        run_store.save_run("test-run", self.state)

    def test_rejection_is_persisted_and_cannot_be_approved(self):
        result = run_store.reject_run("test-run")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(run_store.load_run("test-run")["po"]["status"], "rejected")
        self.assertEqual(run_store.load_run(po_id=7)["run_id"], "test-run")
        self.assertFalse(run_store.claim_approval("test-run"))
        conn = self.connect()
        self.assertEqual(conn.execute("SELECT status FROM purchase_orders WHERE po_id=7").fetchone()[0], "rejected")
        conn.close()

    def test_only_one_approval_can_claim_the_order(self):
        self.assertTrue(run_store.claim_approval("test-run"))
        self.assertFalse(run_store.claim_approval("test-run"))
        self.assertIn("error", run_store.reject_run("test-run"))
        self.assertEqual(run_store.load_run("test-run")["status"], "approving")

    def test_repeated_approval_does_not_ship_or_email_twice(self):
        stubs = {}
        for name in ("sourcing", "purchasing", "freight", "tracking"):
            module = types.ModuleType(f"agents.supply_chain.{name}_agent")
            setattr(module, f"run_{name}_agent", AsyncMock())
            stubs[module.__name__] = module
        with patch.dict(sys.modules, stubs):
            orchestrator = load_module("evaluation_orchestrator", "backend/supply_chain/orchestrator.py")
        final = {"status": "completed", "po": {"po_id": 7, "status": "approved"}, "shipment": {"shipment_id": 9}}
        with patch.object(orchestrator.run2_graph, "ainvoke", new=AsyncMock(return_value=final)) as run, \
             patch("backend.supply_chain.po_email.send_approved_po_email", return_value={"sent": False, "error": "SMTP unavailable"}) as email:
            first = asyncio.run(orchestrator.approve_pipeline("test-run"))
            second = asyncio.run(orchestrator.approve_pipeline("test-run"))
        self.assertEqual(first, second)
        self.assertFalse(first["email_sent"])
        self.assertEqual(first["email_error"], "SMTP unavailable")
        run.assert_awaited_once()
        email.assert_called_once()


class ProgressTests(unittest.TestCase):
    def test_request_progress_does_not_leak_between_chats(self):
        with progress_scope("first"):
            report_progress("Inventory Agent", "Checking stock")
            with progress_scope("second"):
                report_progress("Forecast Agent", "Checking history")
            self.assertEqual(get_progress("first")["agent"], "Inventory Agent")
            self.assertEqual(get_progress("second")["agent"], "Forecast Agent")
        self.assertEqual(get_progress("first")["status"], "finished")
        self.assertEqual(get_progress("unknown")["status"], "waiting")

    def test_langgraph_nodes_report_actual_progress(self):
        from langgraph.graph import StateGraph, END
        graph = StateGraph(dict)
        def inventory(state):
            report_progress("Inventory Agent", "Checking stock")
            return state
        graph.add_node("inventory", inventory)
        graph.set_entry_point("inventory")
        graph.add_edge("inventory", END)
        with progress_scope("graph-test"):
            graph.compile().invoke({})
            self.assertEqual(get_progress("graph-test")["agent"], "Inventory Agent")


class PlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Match the repository's function-isolation approach without importing live providers.
        import ast
        source = ast.parse((ROOT / "agents/operations/operations_agent.py").read_text(encoding="utf-8"))
        names = {"_node_procurement_evidence", "_node_synthesize_plan", "_material_type_for_shortage", "_extract_date", "_extract_color"}
        tree = ast.Module(body=[node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
        import re
        cls.namespace = {"OperationsState": dict, "datetime": datetime, "re": re,
                         "report_progress": Mock(), "client": None,
                         "_friendly_status": lambda status: status,
                         "_friendly_date": lambda value: value,
                         "_format_count": lambda value: str(value)}
        exec(compile(tree, "agents/operations/operations_agent.py", "exec"), cls.namespace)

    def test_two_shortages_in_same_category_both_get_drafts(self):
        materials = [{"material_code": code, "material_name": code, "shortage": qty, "status": "SHORTAGE", "unit": "meters"}
                     for code, qty in [("FAB-001", 300), ("FAB-004", 200)]]
        pipeline = types.ModuleType("backend.supply_chain.orchestrator")
        pipeline.start_pipeline = AsyncMock(return_value={"status": "awaiting_approval", "po": {"po_id": 7}})
        with patch.dict(sys.modules, {pipeline.__name__: pipeline}):
            result = self.namespace["_node_procurement_evidence"]({"production": {"blocking_materials": materials}})
        self.assertEqual(len(result["procurement"]), 2)
        self.assertEqual(pipeline.start_pipeline.await_count, 2)
        self.assertEqual([call.kwargs["qty"] for call in pipeline.start_pipeline.await_args_list], [300, 200])
        self.assertEqual(pipeline.start_pipeline.await_args_list[1].kwargs["po_details"]["material_code"], "FAB-004")

    def test_missing_inventory_does_not_create_arbitrary_order(self):
        pipeline = types.ModuleType("backend.supply_chain.orchestrator")
        pipeline.start_pipeline = AsyncMock()
        with patch.dict(sys.modules, {pipeline.__name__: pipeline}):
            result = self.namespace["_node_procurement_evidence"]({"production": {"blocking_materials": [
                {"material_code": "MISSING", "status": "NOT_FOUND"}]}})
        pipeline.start_pipeline.assert_not_awaited()
        self.assertIn("error", result["procurement"][0])

    def test_partial_drafts_are_not_described_as_complete(self):
        result = self.namespace["_node_synthesize_plan"]({
            "production": {"status": "AT_RISK", "blocking_materials": [
                {"material_code": "FAB-001", "status": "SHORTAGE", "shortage": 300},
                {"material_code": "FAB-004", "status": "SHORTAGE", "shortage": 200}]},
            "procurement": [{"run": {"status": "awaiting_approval", "po": {"po_id": 7}}}, {"error": "Supplier unavailable"}],
        })["response"]
        self.assertIn("drafted 1 purchase order", result["answer"])
        self.assertIn("not drafted for all", result["answer"])
        self.assertTrue(result["requires_approval"])

    def test_relative_demo_dates_keep_working(self):
        expected = (date.today() + timedelta(days=30)).isoformat()
        self.assertEqual(self.namespace["_extract_date"]("Can we fulfill this in 30 days?"), expected)

    def test_missing_bom_requests_more_information(self):
        result = self.namespace["_node_synthesize_plan"]({"production": {"status": "NO_BOM", "message": "Add a BOM first."}})["response"]
        self.assertEqual(result["status"], "needs_more_info")
        self.assertIn("Add a BOM first.", result["answer"])


class EmailConfigurationTests(unittest.TestCase):
    def test_missing_password_and_invalid_port_do_not_attempt_smtp(self):
        from backend.supply_chain.email_service import send_po_email
        with patch.dict(os.environ, {"BREVO_SMTP_USER": "test", "BREVO_SMTP_PASS": "", "BREVO_SMTP_PORT": "invalid"}), \
             patch("smtplib.SMTP") as smtp:
            result = send_po_email({"po_id": 7}, "example@example.com")
        self.assertFalse(result["sent"])
        smtp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
