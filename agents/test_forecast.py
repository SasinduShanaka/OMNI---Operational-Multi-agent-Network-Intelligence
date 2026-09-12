from datetime import datetime
import unittest
from unittest.mock import patch

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

    def test_accuracy_uses_weighted_error_and_prior_history_only(self):
        with patch.object(forecast_agent, '_fit_holt', return_value=(100, 0, 0.5, 0.5)) as fit:
            accuracy = forecast_agent._backtest_accuracy([50, 75, 80, 120])
        self.assertEqual([call.args[0] for call in fit.call_args_list], [[50, 75], [50, 75, 80]])
        self.assertEqual(accuracy['wape_percent'], 20)
        self.assertEqual(accuracy['accuracy_percent'], 80)
        self.assertEqual(accuracy['mae'], 20)

    def test_accuracy_handles_zero_demand_and_insufficient_history(self):
        accuracy = forecast_agent._backtest_accuracy([100, 100, 0])
        self.assertIsNone(accuracy['wape_percent'])
        self.assertIsNone(accuracy['accuracy_percent'])
        self.assertIsNone(accuracy['mape_percent'])
        self.assertEqual(accuracy['mae'], 100)
        empty = forecast_agent._backtest_accuracy([100, 100])
        self.assertEqual(empty['test_points'], 0)
        self.assertIsNone(empty['mae'])

    def test_accuracy_excludes_current_and_future_months(self):
        with patch.object(forecast_agent, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 3, 15)
            clock.side_effect = datetime
            # Use date values so parsing does not depend on the mocked datetime type.
            with patch.object(forecast_agent, '_read_demand_snapshot', return_value=(
                [{'date': datetime(2026, m, 1).date(), 'quantity': 100} for m in range(1, 5)],
                {'can_forecast': True},
            )):
                result = forecast_agent.forecast_demand('GAR-003', save_audit=False)
        self.assertEqual(result['accuracy']['test_points'], 0)
        self.assertEqual(result['accuracy']['comparisons'], [])

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

    def test_quality_detects_invalid_records_without_mutating(self):
        records = [
            {"_id": "bad", "date": "invalid", "quantity": -1},
            {"_id": "zero", "date": "2026-01-01", "quantity": 0, "product_name": "Shirt"},
            {"_id": "bool", "date": "2026-02-01", "quantity": True},
        ]
        history, quality = forecast_agent.analyze_demand_records("GAR-003", records)
        self.assertEqual(quality["invalid_records"], 2)
        self.assertEqual(history[0]["quantity"], 0)
        self.assertFalse(quality["can_forecast"])
        self.assertEqual(records[0]["quantity"], -1)

    def test_quality_flags_duplicate_months_and_name_changes(self):
        forecast_agent.demand_collection.records.append({"_id": "duplicate", "sku": "GAR-003", "product_name": "Other name", "date": "2026-03-01", "quantity": 700})
        quality = forecast_agent.get_demand_quality("GAR-003")
        codes = {issue["code"] for issue in quality["issues"]}
        self.assertIn("multiple_records_per_month", codes)
        self.assertIn("inconsistent_product_names", codes)
        self.assertTrue(quality["can_forecast"])

    def test_missing_month_blocks_forecast(self):
        forecast_agent.demand_collection.records[-1]["date"] = datetime(2026, 4, 1)
        result = forecast_agent.forecast_demand("GAR-003", save_audit=False)
        self.assertEqual(result["error_code"], "missing_months")
        self.assertEqual(result["data_quality"]["missing_months"], ["2026-03"])

    def test_clean_eight_months_pass_quality(self):
        records = [{"date": datetime(2026, month, 1), "quantity": 100, "product_name": "Shirt"} for month in range(1, 9)]
        _, quality = forecast_agent.analyze_demand_records("GAR-003", records)
        self.assertEqual(quality["status"], "passed")
        self.assertEqual(quality["issues"], [])

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
