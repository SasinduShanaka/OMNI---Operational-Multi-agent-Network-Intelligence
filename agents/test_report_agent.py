import unittest
from unittest.mock import Mock

from agents.report_agent import build_report


class ReportAgentTests(unittest.TestCase):
    def test_combines_sources_and_keeps_failed_forecasts(self):
        scope = {"domains": ["inventory", "forecast", "production"], "periods": 3}
        report = build_report(scope, {
            "inventory": lambda _: [{"material_code": "FAB-001", "status": "LOW_STOCK", "current_stock": 2, "unit": "meters"}],
            "forecast": lambda _: [{"sku": "GAR-001", "status": "success", "trend": "Increasing", "forecast": 20, "predictions": [{"date": "2026-10-01", "quantity": 20}]}, {"sku": "GAR-002", "status": "error", "message": "Missing months"}],
            "production": lambda _: {"lines": [{"status": "BOTTLENECK"}], "orders": []},
        })
        self.assertEqual(report["status"], "partial")
        self.assertEqual(len(report["sections"]), 3)
        forecast = report["sections"][1]
        self.assertEqual(forecast["tables"][0]["rows"][1]["note"], "Missing months")
        self.assertEqual(forecast["tables"][1]["rows"][0]["quantity"], 20)
        self.assertTrue(any("inventory + production" == item["source"] for item in report["recommendations"]))
        self.assertEqual(len(report["evidence"]["forecast"]), 2)

    def test_unavailable_source_does_not_abort_other_sections_or_leak_errors(self):
        with self.assertLogs("agents.report_agent", level="ERROR"):
            report = build_report({"domains": ["inventory", "forecast"]}, {
                "inventory": Mock(side_effect=RuntimeError("private database password")),
                "forecast": lambda _: [],
            })
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["sections"][0]["status"], "error")
        self.assertEqual(report["sections"][1]["status"], "empty")
        self.assertNotIn("private database password", str(report))

    def test_all_failed_is_error_and_empty_is_not_healthy(self):
        with self.assertLogs("agents.report_agent", level="ERROR"):
            report = build_report({"domains": ["inventory"]}, {"inventory": Mock(side_effect=ValueError("bad data"))})
        self.assertEqual(report["status"], "error")
        empty = build_report({"domains": ["inventory"]}, {"inventory": lambda _: []})
        self.assertEqual(empty["status"], "partial")
        self.assertIn("not evidence of healthy", empty["answer"])


if __name__ == "__main__":
    unittest.main()
