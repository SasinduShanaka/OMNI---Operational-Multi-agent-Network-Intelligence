from datetime import datetime, date, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from agents.forecast.forecast_comparison import compare_product


class ComparisonTests(TestCase):
    def run_history(self, months, issues=None, invalid=0, sku='GAR-006'):
        history = [{'date': date(2026, month, 1), 'quantity': month * 10, 'product_name': sku} for month in months]
        fit = Mock(return_value=(70, 10, .5, .5))
        fake = SimpleNamespace(analyze_demand_records=Mock(return_value=(history, {'issues': issues or [], 'invalid_records': invalid})), _fit_holt=fit)
        storage = Mock()
        storage.find.return_value.sort.return_value = []
        with patch.dict('sys.modules', {'agents.forecast.forecast_agent': fake}):
            result = compare_product(sku, Mock(find=Mock(return_value=[])), storage, datetime(2026, 9, 20, tzinfo=timezone.utc))
        return result, fit

    def test_last_three_products_use_recent_history_despite_older_gap(self):
        for sku in ['GAR-006', 'GAR-007', 'GAR-008']:
            result, fit = self.run_history([1, 2, 5, 6, 7, 8, 9], sku=sku)
            self.assertEqual(result['status'], 'success')
            fit.assert_called_once_with([50, 60, 70])

    def test_unrelated_invalid_record_warns_but_does_not_block(self):
        result, fit = self.run_history([5, 6, 7, 8], [{'code': 'invalid_quantity', 'month': '2026-02', 'message': 'Invalid February quantity'}], invalid=1)
        self.assertEqual(result['status'], 'success')
        self.assertIn('review data quality', result['note'])
        fit.assert_called_once_with([50, 60, 70])

    def test_bad_recent_month_and_missing_month_report_exact_boundary(self):
        result, fit = self.run_history([5, 6, 7, 8], [{'code': 'multiple_records_per_month', 'month': '2026-06', 'message': 'Duplicate June'}])
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('2026-06: invalid or duplicate', result['note'])
        fit.assert_not_called()
        result, fit = self.run_history([5, 6, 8])
        self.assertIn('2026-07: missing demand', result['note'])
        fit.assert_not_called()

    def test_invalid_target_month_still_blocks_comparison(self):
        result, fit = self.run_history([5, 6, 7, 8], [{'code': 'invalid_quantity', 'month': '2026-08', 'message': 'Invalid August'}], invalid=1)
        self.assertIsNone(result['actual'])
        fit.assert_not_called()

    def test_backtest_uses_only_earlier_months(self):
        history = [{'date': date(2026, month, 1), 'quantity': quantity, 'product_name': 'Polo'}
                   for month, quantity in [(5, 100), (6, 110), (7, 120), (8, 1303), (9, 9999)]]
        fit = Mock(return_value=(120, 10, 0.5, 0.5))
        fake = SimpleNamespace(analyze_demand_records=Mock(return_value=(history, {'issues': [], 'invalid_records': 0})), _fit_holt=fit)
        audits = Mock()
        audits.find.return_value.sort.return_value = []
        with patch.dict('sys.modules', {'agents.forecast.forecast_agent': fake}):
            result = compare_product('GAR-001', Mock(find=Mock(return_value=[])), audits, datetime(2026, 9, 20, tzinfo=timezone.utc))
        fit.assert_called_once_with([100, 110, 120])
        self.assertEqual(result['prediction_source'], 'Historical backtest estimate')
        self.assertEqual(result['predicted'], 130)
        self.assertEqual(result['error'], -1173)

    def compare(self, actual, audits):
        analyze = Mock(return_value=([{'date': date(2026, 8, 1), 'quantity': actual, 'product_name': 'Classic Black Polo'}], {'issues': [], 'invalid_records': 0}))
        storage = Mock()
        storage.find.return_value.sort.return_value = audits
        with patch.dict('sys.modules', {'agents.forecast.forecast_agent': SimpleNamespace(analyze_demand_records=analyze)}):
            result = compare_product('GAR-001', Mock(find=Mock(return_value=[])), storage, datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.assertEqual(storage.find.call_args.args[0]['timestamp']['$lt'], datetime(2026, 8, 1, tzinfo=timezone.utc))
        return result

    def test_saved_forecast_error(self):
        result = self.compare(100, [{'forecast_period': '2026-08-01', 'forecast': 120}])
        self.assertEqual(result['error'], 20)
        self.assertEqual(result['percentage_error'], 20)

    def test_missing_forecast_is_not_zero(self):
        result = self.compare(100, [])
        self.assertIsNone(result['predicted'])
        self.assertEqual(result['status'], 'unavailable')

    def test_multimonth_audit_and_zero_actual(self):
        result = self.compare(0, [{'predictions': [{'date': '2026-08-01', 'quantity': 40}]}])
        self.assertEqual(result['absolute_error'], 40)
        self.assertIsNone(result['percentage_error'])
