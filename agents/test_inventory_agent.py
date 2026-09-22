"""Inventory behavior with isolated collection data."""

import unittest
from unittest.mock import patch

from agents import inventory_agent


class InventoryAgentTests(unittest.TestCase):
    def test_low_stock_shortage_uses_reorder_level(self):
        rows = [{"material_name": "Cotton", "material_code": "FAB-001",
                 "current_stock": 20, "reorder_level": 50, "unit": "meters"}]
        with patch.object(inventory_agent.inventory_collection, "find", return_value=rows):
            result = inventory_agent.check_inventory()
        self.assertEqual(result[0]["status"], "LOW_STOCK")
        self.assertEqual(result[0]["shortage"], 30)


if __name__ == "__main__":
    unittest.main()
