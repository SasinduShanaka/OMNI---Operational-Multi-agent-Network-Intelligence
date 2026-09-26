"""Product selection and specialist routing tests without live databases or LLMs."""
import ast
from pathlib import Path
import re
import unittest
from unittest.mock import Mock

from agents.forecast.forecast_product import resolve_forecast_product

PRODUCTS = [
    {"sku": "GAR-001", "product_name": "Classic Black Polo"},
    {"sku": "GAR-002", "product_name": "White Cotton T-Shirt"},
    {"sku": "GAR-003", "product_name": "Navy Formal Shirt"},
    {"sku": "GAR-004", "product_name": "Grey Hoodie"},
    {"sku": "GAR-005", "product_name": "Women's Casual Top"},
    {"sku": "GAR-006", "product_name": "Blue Denim Shirt"},
    {"sku": "GAR-007", "product_name": "Green Sports T-Shirt"},
    {"sku": "GAR-008", "product_name": "Beige Cargo Pants"},
]


class ProductSelectionTests(unittest.TestCase):
    def test_last_month_comparison_keeps_mode_and_product_choices(self):
        result = resolve_forecast_product('Compare predicted demand with actual demand last month', PRODUCTS)
        self.assertEqual(result['mode'], 'comparison')
        self.assertEqual(result['status'], 'needs_information')
        self.assertEqual(len(result['products']), 8)
        result = resolve_forecast_product('Compare predicted demand with actual demand last month for black polo', PRODUCTS)
        self.assertEqual(result['sku'], 'GAR-001')
        self.assertEqual(result['mode'], 'comparison')
        result = resolve_forecast_product('Compare predicted demand with actual demand last month for all products. Which forecasts were least accurate and why?', PRODUCTS)
        self.assertEqual(result, {'status': 'all', 'mode': 'comparison'})

    def test_month_horizons_and_invalid_ranges(self):
        for duration in ['three months', '3 months', '3-month']:
            result = resolve_forecast_product(f'Forecast black polo demand for the next {duration}', PRODUCTS)
            self.assertEqual(result, {'status': 'matched', 'sku': 'GAR-001', 'periods': 3})
        for duration in ['0 months', '13 months', '-3 months', '1.5 months', 'thirteen months']:
            self.assertEqual(resolve_forecast_product(f'Forecast GAR-001 for {duration}', PRODUCTS)['status'], 'invalid_horizon')
        result = resolve_forecast_product('Forecast t-shirt demand for six months', PRODUCTS)
        self.assertEqual(result['periods'], 6)
        self.assertEqual(result['status'], 'ambiguous')

    def test_growth_ranking_question_uses_all_products_and_quarter_horizon(self):
        result = resolve_forecast_product('Which products have the highest forecasted demand growth next quarter?', PRODUCTS)
        self.assertEqual(result, {'status': 'all', 'mode': 'growth_ranking', 'periods': 3})

    def test_demand_ranking_supports_highest_lowest_and_custom_horizon(self):
        result = resolve_forecast_product('What are the highest and lowest demand products for the next 6 months?', PRODUCTS)
        self.assertEqual(result, {'status': 'all', 'mode': 'demand_ranking', 'ranking': 'both', 'periods': 6})
        self.assertEqual(
            resolve_forecast_product('Which product has the lowest forecast demand next month?', PRODUCTS),
            {'status': 'all', 'mode': 'demand_ranking', 'ranking': 'lowest'},
        )

    def test_shirt_category_includes_polos_and_tshirts(self):
        for question in ['Forecast Shirt demand.', 'Forecast shirts demand']:
            result = resolve_forecast_product(question, PRODUCTS)
            self.assertEqual(result['status'], 'ambiguous')
            self.assertEqual({p['sku'] for p in result['products']},
                             {'GAR-001', 'GAR-002', 'GAR-003', 'GAR-006', 'GAR-007'})
        self.assertEqual(resolve_forecast_product('forecast black shirt demand', PRODUCTS)['sku'], 'GAR-001')
        self.assertEqual(resolve_forecast_product('forecast polo demand', PRODUCTS)['sku'], 'GAR-001')
        self.assertEqual(resolve_forecast_product('forecast black t-shirt demand', PRODUCTS)['status'], 'not_found')

    def test_conversational_questions_preserve_product_constraints(self):
        for question in [
            'can you say next month black polo shirt demand forecast',
            'could you please provide next month demand for black polo shirts',
            'I want to know the demand forecast for black polo shirts',
            'kindly share the black polo demand forecast thanks',
        ]:
            with self.subTest(question=question):
                self.assertEqual(resolve_forecast_product(question, PRODUCTS), {'status': 'matched', 'sku': 'GAR-001'})
        self.assertEqual(resolve_forecast_product('can you say red polo shirt demand forecast', PRODUCTS)['status'], 'not_found')

    def test_all_eight_catalog_names_and_common_variants(self):
        variants = [
            ('GAR-001', 'black polo shirts'), ('GAR-002', 'white cotton tees'),
            ('GAR-003', 'navy formal shirts'), ('GAR-004', 'gray hoodies'),
            ('GAR-005', 'womens casual tops'), ('GAR-005', 'women’s casual top'),
            ('GAR-006', 'blue denim shirts'), ('GAR-007', 'green sport t shirts'),
            ('GAR-008', 'beige cargo pants'),
        ]
        for sku, name in [(p['sku'], p['product_name']) for p in PRODUCTS] + variants:
            question = f'Please predict next month demand for {name}'
            with self.subTest(question=question):
                self.assertEqual(resolve_forecast_product(question, PRODUCTS), {'status': 'matched', 'sku': sku})

    def test_every_catalog_name_accepts_case_and_camel_case(self):
        for product in PRODUCTS:
            name = product['product_name']
            camel_case = re.sub(r"[^A-Za-z0-9]+", " ", name).title().replace(" ", "")
            for variant in (name.lower(), name.upper(), camel_case):
                with self.subTest(sku=product['sku'], variant=variant):
                    self.assertEqual(
                        resolve_forecast_product(f'Predict demand for {variant}', PRODUCTS)['sku'],
                        product['sku'],
                    )

    def test_product_codes_accept_common_input_formats(self):
        for product in PRODUCTS:
            number = product['sku'].split('-')[1]
            for variant in (product['sku'].lower(), f'GAR{number}', f'GAR {number}', f'gar_{number}'):
                with self.subTest(sku=product['sku'], variant=variant):
                    self.assertEqual(resolve_forecast_product(f'Forecast demand for {variant}', PRODUCTS),
                                     {'status': 'matched', 'sku': product['sku']})

    def test_shared_garment_name_does_not_choose_arbitrarily(self):
        result = resolve_forecast_product('forecast t-shirt demand', PRODUCTS)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertIn('GAR-002', result['message'])
        self.assertIn('GAR-007', result['message'])
        self.assertEqual({item['sku'] for item in result['products']}, {'GAR-002', 'GAR-007'})

    def test_name_variants_resolve_same_product(self):
        for question in ["predict next month black polo shirts demand", "Forecast demand for Classic Black Polo", "black polos demand", "Black Polo shirt's demand next month"]:
            with self.subTest(question=question):
                self.assertEqual(resolve_forecast_product(question, PRODUCTS), {"status": "matched", "sku": "GAR-001"})

    def test_explanatory_forecast_request_keeps_product_name(self):
        question = ('Forecast demand for Classic Black Polo for the next 6 months '
                    'and explain the trend, confidence, and key drivers.')
        self.assertEqual(
            resolve_forecast_product(question, PRODUCTS),
            {"status": "matched", "sku": "GAR-001", "periods": 6},
        )

    def test_other_names_and_codes(self):
        self.assertEqual(resolve_forecast_product("white cotton t shirts demand", PRODUCTS)["sku"], "GAR-002")
        self.assertEqual(resolve_forecast_product("gray hoodies demand", PRODUCTS)["sku"], "GAR-004")
        self.assertEqual(resolve_forecast_product("forecast gar-004", [])['sku'], "GAR-004")

    def test_no_silent_all_products_fallback(self):
        for question in ["forecast red polo demand", "forecast demand", "demand for this product"]:
            self.assertNotIn(resolve_forecast_product(question, PRODUCTS)["status"], {"matched", "all"})
        self.assertEqual(resolve_forecast_product("forecast demand for all products", PRODUCTS)["status"], "all")

    def test_ambiguous_color_or_style_requires_clarification(self):
        products = PRODUCTS + [{"sku": "GAR-009", "product_name": "Premium Black Polo"}]
        result = resolve_forecast_product("black polo shirts demand", products)
        self.assertEqual(result["status"], "ambiguous")
        self.assertIn("GAR-001", result["message"])
        self.assertIn("GAR-009", result["message"])

    def test_specialist_forecasts_only_resolved_sku(self):
        # Load the real dispatch function in isolation: the module otherwise
        # initializes unrelated database/LLM clients at import time.
        tree = ast.parse((Path(__file__).resolve().parents[2] / 'agents' / 'operations' / 'operations_agent.py').read_text(encoding='utf-8'))
        node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == '_execute_specialist_request')
        forecast = Mock(return_value={"status": "error", "message": "Missing history"})
        all_products = Mock()
        namespace = {"re": re, "resolve_forecast_product": resolve_forecast_product,
                     "get_forecast_products": Mock(return_value=PRODUCTS),
                     "forecast_demand": forecast, "forecast_all_demand": all_products}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<specialist>', 'exec'), namespace)
        result = namespace['_execute_specialist_request']('can you say next month black polo shirt demand forecast')
        forecast.assert_called_once_with('GAR-001', periods=1)
        all_products.assert_not_called()
        self.assertEqual(result['result']['message'], 'Missing history')
        forecast.reset_mock()
        result = namespace['_execute_specialist_request']('Forecast T-shirt demand')
        self.assertEqual({item['sku'] for item in result['suggested_products']}, {'GAR-002', 'GAR-007'})
        forecast.assert_not_called()
        selected = result['suggested_products'][0]
        namespace['_execute_specialist_request'](f"Forecast demand for {selected['product_name']} ({selected['sku']})")
        forecast.assert_called_once_with(selected['sku'], periods=1)
        forecast.reset_mock()
        namespace['_execute_specialist_request']('Forecast black polo demand for the next three months')
        forecast.assert_called_once_with('GAR-001', periods=3)
        forecast.reset_mock()
        forecast.return_value = {
            "status": "success", "forecast": 1200, "product_name": "Classic Black Polo", "sku": "GAR-001",
            "forecast_period": "2026-10-01", "trend": "Increasing", "trend_per_period": 25,
            "history_points": 7, "accuracy": {"accuracy_percent": 90, "test_points": 5},
            "recommendation": "Plan capacity.", "model_components": {"level": 1175}, "predictions": [],
        }
        explained = namespace['_execute_specialist_request'](
            'Forecast demand for Classic Black Polo and explain the trend, confidence, and key drivers')
        self.assertIn('Explanation', explained['answer'])
        self.assertIn('Confidence: moderate', explained['answer'])
        self.assertIn('Key drivers:', explained['answer'])
        forecast.reset_mock()
        result = namespace['_execute_specialist_request']('predict red polo shirts demand')
        self.assertEqual(result['status'], 'needs_information')
        forecast.assert_not_called()
        all_products.assert_not_called()


if __name__ == '__main__':
    unittest.main()
