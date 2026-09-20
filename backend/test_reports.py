from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import report_service as service
from backend.report_router import router


class ScheduleTests(unittest.TestCase):
    def test_daily_rolls_at_local_time(self):
        schedule = {"frequency": "daily", "time": "08:00"}
        before = datetime(2026, 9, 20, 2, 29, tzinfo=timezone.utc)
        expected = datetime(2026, 9, 20, 2, 30, tzinfo=timezone.utc)
        self.assertEqual(service.next_occurrence(schedule, before), expected)
        self.assertEqual(service.next_occurrence(schedule, expected).day, 21)

    def test_monthly_handles_year_boundary_and_february(self):
        config = {"frequency": "monthly", "time": "08:00", "day_of_month": 28}
        self.assertEqual(service.next_occurrence(config, datetime(2026, 12, 29, tzinfo=timezone.utc)), datetime(2027, 1, 28, 2, 30, tzinfo=timezone.utc))
        self.assertEqual(service.next_occurrence(config, datetime(2027, 1, 29, tzinfo=timezone.utc)), datetime(2027, 2, 28, 2, 30, tzinfo=timezone.utc))

    @patch.object(service, "get_db")
    @patch.object(service, "generate_report")
    def test_claim_is_atomic_and_occurrence_id_is_stable(self, generate, get_db):
        due = datetime(2026, 9, 1, 2, 30, tzinfo=timezone.utc)
        now = datetime(2026, 9, 20, 10, tzinfo=timezone.utc)
        collection = get_db.return_value.report_schedules
        collection.find_one_and_update.return_value = {"_id": "schedule-1", "next_run": due, "frequency": "daily", "time": "08:00", "scope": {"domains": ["inventory"]}}
        generate.return_value = {"status": "partial"}
        with patch.object(service, "utcnow", return_value=now):
            self.assertTrue(service.run_due_schedule())
        self.assertEqual(generate.call_args.args[1], f"schedule-1--{due.isoformat()}")
        query = collection.find_one_and_update.call_args.args[0]
        self.assertTrue(query["enabled"])
        self.assertIn("$or", query)
        update = collection.update_one.call_args.args[1]
        self.assertEqual(update["$set"]["last_status"], "partial")
        self.assertGreater(update["$set"]["next_run"], now)
        self.assertIn("lease_until", update["$unset"])

    @patch.object(service, "get_db")
    @patch.object(service, "generate_report", side_effect=RuntimeError("offline"))
    def test_save_failure_preserves_due_occurrence_for_retry(self, generate, get_db):
        collection = get_db.return_value.report_schedules
        collection.find_one_and_update.return_value = {"_id": "s", "next_run": datetime.now(timezone.utc), "scope": {}}
        with self.assertLogs("backend.report_service", level="ERROR"):
            service.run_due_schedule()
        update = collection.update_one.call_args.args[1]
        self.assertEqual(update["$set"]["last_status"], "retrying")
        self.assertNotIn("next_run", update["$set"])
        self.assertNotIn("$unset", update)

    @patch.object(service, "get_db")
    @patch.object(service, "build_report")
    def test_retry_reuses_saved_snapshot(self, build, get_db):
        get_db.return_value.reports.find_one.return_value = {"_id": "existing", "answer": "Original report"}
        report = service.generate_report({}, report_id="existing")
        self.assertEqual(report["answer"], "Original report")
        build.assert_not_called()

    @patch.object(service, "get_db")
    @patch.object(service, "build_report", return_value={"status": "success", "answer": "Saved", "evidence": {}})
    def test_new_report_persists_without_overwriting(self, build, get_db):
        collection = get_db.return_value.reports
        collection.find_one.side_effect = [None, {"_id": "new", "answer": "Saved"}]
        report = service.generate_report({"domains": ["inventory"]}, report_id="new")
        self.assertEqual(report["_id"], "new")
        update = collection.update_one.call_args
        self.assertIn("$setOnInsert", update.args[1])
        self.assertTrue(update.kwargs["upsert"])

    @patch.object(service, "get_db")
    def test_resume_recomputes_next_run(self, get_db):
        collection = get_db.return_value.report_schedules
        collection.find_one.return_value = {"_id": "s", "enabled": False, "frequency": "daily", "time": "08:00"}
        service.set_schedule_enabled("s", True)
        self.assertIn("next_run", collection.update_one.call_args.args[1]["$set"])


class ReportApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_schedule_validation(self):
        for body in ({"time": "25:00"}, {"day_of_month": 31}, {"frequency": "weekly"}, {"scope": {"domains": []}}, {"scope": {"skus": ["bad"]}}):
            self.assertEqual(self.client.post("/reports/schedules", json=body).status_code, 422)

    @patch.object(service, "generate_report")
    def test_generate_normalizes_scope_and_hides_raw_evidence(self, generate):
        generate.return_value = {"_id": "test", "status": "success", "evidence": {"private": []}}
        response = self.client.post("/reports/generate", json={"domains": ["forecast", "forecast"], "skus": ["gar-003"]})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("evidence", response.json())
        self.assertEqual(generate.call_args.args[0]["domains"], ["forecast"])
        self.assertEqual(generate.call_args.args[0]["skus"], ["GAR-003"])

    @patch.object(service, "list_reports", side_effect=RuntimeError("secret"))
    def test_storage_failure_has_safe_error(self, listing):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)

    @patch.object(service, "get_report", return_value=None)
    def test_missing_report_and_bounded_pagination(self, get_report):
        self.assertEqual(self.client.get("/reports/missing").status_code, 404)
        self.assertEqual(self.client.get("/reports?limit=1000").status_code, 422)

    @patch.object(service, "list_schedules", return_value=[])
    def test_schedule_route_precedes_report_id_route(self, schedules):
        self.assertEqual(self.client.get("/reports/schedules").json(), {"schedules": []})


if __name__ == "__main__":
    unittest.main()
