"""Product selection and specialist routing tests without live databases or LLMs."""
import ast
from pathlib import Path
import re
import unittest
from unittest.mock import Mock

from agents.forecast_product import resolve_forecast_product

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

    def test_shared_garment_name_does_not_choose_arbitrarily(self):
        result = resolve_forecast_product('forecast t-shirt demand', PRODUCTS)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertIn('GAR-002', result['message'])
        self.assertIn('GAR-007', result['message'])

    def test_name_variants_resolve_same_product(self):
        for question in ["predict next month black polo shirts demand", "Forecast demand for Classic Black Polo", "black polos demand", "Black Polo shirt's demand next month"]:
            with self.subTest(question=question):
                self.assertEqual(resolve_forecast_product(question, PRODUCTS), {"status": "matched", "sku": "GAR-001"})

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
        tree = ast.parse(Path(__file__).with_name('operations_agent.py').read_text(encoding='utf-8'))
        node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == '_execute_specialist_request')
        forecast = Mock(return_value={"status": "error", "message": "Missing history"})
        all_products = Mock()
        namespace = {"re": re, "resolve_forecast_product": resolve_forecast_product,
                     "get_forecast_products": Mock(return_value=PRODUCTS),
                     "forecast_demand": forecast, "forecast_all_demand": all_products}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<specialist>', 'exec'), namespace)
        result = namespace['_execute_specialist_request']('can you say next month black polo shirt demand forecast')
        forecast.assert_called_once_with('GAR-001')
        all_products.assert_not_called()
        self.assertEqual(result['result']['message'], 'Missing history')
        forecast.reset_mock()
        result = namespace['_execute_specialist_request']('predict red polo shirts demand')
        self.assertEqual(result['status'], 'needs_information')
        forecast.assert_not_called()
        all_products.assert_not_called()


if __name__ == '__main__':
    unittest.main()
