from datetime import datetime
import unittest

from agents import forecast_agent


class FakeDemandCollection:
    def __init__(self, records):
        self.records = records

    def find(self, query, projection):
        if not query:
            return self.records
        return [record for record in self.records if record["sku"] == query["sku"]]

    def distinct(self, field):
        return list({record[field] for record in self.records if field in record})


class FakeActivityCollection:
    def __init__(self):
        self.saved = []

    def insert_one(self, record):
        self.saved.append(record)


class DemandForecastAgentTests(unittest.TestCase):
    def setUp(self):
        self.original_collection = forecast_agent.demand_collection
        self.original_activity_collection = forecast_agent.activity_collection
        forecast_agent.activity_collection = None
        forecast_agent.demand_collection = FakeDemandCollection([
            {"sku": "GAR-003", "product_name": "Navy Formal Shirt", "date": datetime(2026, 1, 1), "quantity": 500},
            {"sku": "GAR-003", "product_name": "Navy Formal Shirt", "date": datetime(2026, 2, 1), "quantity": 600},
            {"sku": "GAR-003", "product_name": "Navy Formal Shirt", "date": datetime(2026, 3, 1), "quantity": 700},
        ])

    def tearDown(self):
        forecast_agent.demand_collection = self.original_collection
        forecast_agent.activity_collection = self.original_activity_collection

    def test_forecasts_next_period_from_increasing_history(self):
        result = forecast_agent.forecast_demand("gar-003")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["forecast"], 800.0)
        self.assertEqual(result["trend"], "Increasing")
        self.assertEqual(result["model"], "Holt's Linear Trend")
        self.assertIn("alpha", result["smoothing_parameters"])
        self.assertIn("beta", result["smoothing_parameters"])
        self.assertEqual(result["model_components"]["level"], 700.0)
        self.assertEqual(result["model_components"]["trend"], 100.0)
        self.assertEqual(result["history_points"], 3)
        self.assertEqual(result["forecast_period"], "2026-04-01")
        self.assertEqual(result["accuracy"]["mape_percent"], 0.0)
        self.assertEqual([point["quantity"] for point in result["history"]], [500.0, 600.0, 700.0])

    def test_returns_multiple_upcoming_periods(self):
        result = forecast_agent.forecast_demand("GAR-003", periods=3, save_audit=False)

        self.assertEqual(len(result["predictions"]), 3)
        self.assertEqual(result["predictions"][-1], {"date": "2026-06-01", "quantity": 1000.0})

    def test_holt_model_reacts_to_recent_demand(self):
        forecast_agent.demand_collection.records.extend([
            {"sku": "GAR-003", "product_name": "Navy Formal Shirt", "date": datetime(2026, 4, 1), "quantity": 900},
            {"sku": "GAR-003", "product_name": "Navy Formal Shirt", "date": datetime(2026, 5, 1), "quantity": 1100},
        ])

        result = forecast_agent.forecast_demand("GAR-003", save_audit=False)

        self.assertGreater(result["forecast"], 1100)
        self.assertEqual(result["trend"], "Increasing")

    def test_cleans_invalid_rows_and_aggregates_duplicate_months(self):
        forecast_agent.demand_collection.records.extend([
            {"sku": "GAR-003", "date": "bad-date", "quantity": 10},
            {"sku": "GAR-003", "date": datetime(2026, 3, 20), "quantity": 50},
            {"sku": "GAR-003", "date": datetime(2026, 4, 1), "quantity": -5},
        ])

        history = forecast_agent.get_demand_history("GAR-003")

        self.assertEqual(len(history), 3)
        self.assertEqual(history[-1]["quantity"], 750.0)

    def test_rejects_invalid_sku(self):
        result = forecast_agent.forecast_demand("shirt-1")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "invalid_sku")

    def test_forecasts_manually_pasted_extended_json_dates(self):
        for row in forecast_agent.demand_collection.records:
            row["date"] = {"$date": row["date"].isoformat() + "Z"}
        result = forecast_agent.forecast_demand("GAR-003", save_audit=False)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["history_points"], 3)
        self.assertEqual(result["forecast"], 800.0)

    def test_reports_missing_history(self):
        result = forecast_agent.forecast_demand("GAR-999")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_code"], "not_found")

    def test_forecasts_every_sku_with_history(self):
        results = forecast_agent.forecast_all_demand()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sku"], "GAR-003")

    def test_optionally_saves_an_audit_event(self):
        activity = FakeActivityCollection()
        forecast_agent.activity_collection = activity

        result = forecast_agent.forecast_demand("GAR-003", save_audit=True)

        self.assertTrue(result["audit_saved"])
        self.assertEqual(activity.saved[0]["message_type"], "PREDICTION")
        self.assertEqual(activity.saved[0]["sku"], "GAR-003")
        self.assertIn("smoothing_parameters", activity.saved[0])


if __name__ == "__main__":
    unittest.main()
