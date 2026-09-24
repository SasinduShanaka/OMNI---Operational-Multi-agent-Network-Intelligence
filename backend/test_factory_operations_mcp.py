import asyncio
import unittest
from unittest.mock import patch

from fastmcp import Client

from backend.mcp.factory_operations import client as factory_client
from backend.mcp.factory_operations import server


class FactoryOperationsMcpTests(unittest.TestCase):
    def test_expected_specialist_tools_are_published(self):
        async def list_names():
            async with Client(server.mcp) as client:
                return {tool.name for tool in await client.list_tools()}

        names = asyncio.run(list_names())
        self.assertTrue({
            "inventory_get_low_stock",
            "forecast_demand",
            "production_check_feasibility",
            "report_generate",
        }.issubset(names))

    @patch.object(
        server.inventory_agent,
        "get_low_stock",
        return_value=[{"material_code": "FAB-001", "status": "LOW_STOCK"}],
    )
    def test_inventory_facade_calls_the_mcp_tool(self, get_low_stock):
        result = factory_client.get_low_stock()
        self.assertEqual(result[0]["material_code"], "FAB-001")
        get_low_stock.assert_called_once_with()

    @patch.object(server.inventory_agent, "add_inventory_item")
    def test_inventory_validation_is_preserved_before_mcp_call(self, add_item):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            factory_client.add_inventory_item("Cotton", -1, 100)
        add_item.assert_not_called()

    @patch.object(
        server.forecast_agent,
        "forecast_demand",
        return_value={"status": "success", "sku": "GAR-001"},
    )
    def test_forecast_arguments_cross_the_mcp_boundary(self, forecast):
        result = factory_client.forecast_demand("GAR-001", periods=3, save_audit=False)
        self.assertEqual(result["status"], "success")
        forecast.assert_called_once_with("GAR-001", 3, False)

    @patch.object(server.forecast_agent, "get_demand_quality")
    def test_forecast_sku_validation_is_preserved_before_mcp_call(self, quality):
        with self.assertRaisesRegex(ValueError, "valid SKU"):
            factory_client.get_demand_quality("invalid")
        quality.assert_not_called()

    @patch.object(
        server.production_agent,
        "check_production_feasibility",
        return_value={"status": "FEASIBLE"},
    )
    def test_production_arguments_cross_the_mcp_boundary(self, feasibility):
        result = factory_client.check_production_feasibility(
            sku="GAR-001",
            quantity=1250,
            required_date="2026-10-21",
        )
        self.assertEqual(result["status"], "FEASIBLE")
        feasibility.assert_called_once_with(
            sku="GAR-001",
            product_name=None,
            quantity=1250,
            required_date="2026-10-21",
        )

    @patch(
        "agents.reports.report_agent.build_report",
        return_value={"status": "success", "scope": {"domains": ["inventory"]}},
    )
    def test_report_generation_crosses_the_mcp_boundary(self, build_report):
        scope = {"domains": ["inventory"]}
        result = factory_client.generate_management_report(scope)
        self.assertEqual(result["status"], "success")
        build_report.assert_called_once_with(scope)


if __name__ == "__main__":
    unittest.main()
