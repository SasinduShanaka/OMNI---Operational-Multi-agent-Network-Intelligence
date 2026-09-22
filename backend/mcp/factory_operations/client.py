"""Synchronous client facade for the Factory Operations MCP server.

OMNI's FastAPI routes and LangGraph nodes are synchronous. These wrappers keep
their existing call signatures while ensuring every operation crosses the MCP
tool boundary. FastMCP's in-memory transport avoids spawning a subprocess for
each local tool call; ``server.py`` can still run as a standalone stdio server.
"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastmcp import Client

from backend.mcp.factory_operations.server import mcp


async def _call_factory_tool_async(name: str, arguments: dict[str, Any] | None = None):
    async with Client(mcp) as client:
        result = await client.call_tool(name, arguments or {})
    if hasattr(result, "data"):
        return result.data
    raise RuntimeError(f"Factory Operations MCP tool '{name}' returned no structured data.")


def call_factory_tool(name: str, arguments: dict[str, Any] | None = None):
    """Call one Factory Operations tool from synchronous application code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call_factory_tool_async(name, arguments))

    # A synchronous LangGraph node can occasionally be invoked by an async host.
    # Run its short-lived MCP session on a separate thread in that case.
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="factory-mcp") as pool:
        return pool.submit(
            asyncio.run, _call_factory_tool_async(name, arguments)
        ).result()


# Inventory facade

def get_all_inventory():
    return call_factory_tool("inventory_get_all")


def check_inventory():
    return call_factory_tool("inventory_check")


def add_inventory_item(
    material_name,
    current_stock,
    reorder_level,
    unit="units",
    material_code=None,
    classification="B",
):
    # Preserve the validation contract used by the HTTP endpoint. FastMCP
    # otherwise converts a server-side ValueError into a generic ToolError.
    if not str(material_name or "").strip():
        raise ValueError("Material name is required.")
    try:
        current_stock = float(current_stock)
        reorder_level = float(reorder_level)
    except (TypeError, ValueError):
        raise ValueError("Current stock and reorder level must be valid numbers.")
    if current_stock < 0 or reorder_level < 0:
        raise ValueError("Current stock and reorder level cannot be negative.")

    return call_factory_tool("inventory_add_item", {
        "material_name": material_name,
        "current_stock": current_stock,
        "reorder_level": reorder_level,
        "unit": unit,
        "material_code": material_code,
        "classification": classification,
    })


def get_low_stock():
    return call_factory_tool("inventory_get_low_stock")


def get_out_of_stock():
    return call_factory_tool("inventory_get_out_of_stock")


def get_healthy_stock():
    return call_factory_tool("inventory_get_healthy_stock")


def get_material(material_name=None, material_code=None):
    return call_factory_tool("inventory_get_material", {
        "material_name": material_name,
        "material_code": material_code,
    })


def check_inventory_requirement(
    material_name=None,
    material_code=None,
    required_quantity=0,
):
    return call_factory_tool("inventory_check_requirement", {
        "material_name": material_name,
        "material_code": material_code,
        "required_quantity": required_quantity,
    })


def get_reorder_requirements():
    return call_factory_tool("inventory_get_reorder_requirements")


def get_total_stock():
    return call_factory_tool("inventory_get_total_stock")


def get_inventory_summary():
    return call_factory_tool("inventory_get_summary")


def get_largest_shortages(limit=5):
    return call_factory_tool("inventory_get_largest_shortages", {"limit": limit})


def get_inventory_kpis():
    return call_factory_tool("inventory_get_kpis")


# Forecast facade

def get_forecast_products():
    return call_factory_tool("forecast_get_products")


def get_demand_quality(sku):
    if not re.fullmatch(r"GAR-\d{3}", str(sku or "").strip(), re.IGNORECASE):
        raise ValueError("Provide a valid SKU such as GAR-003.")
    return call_factory_tool("forecast_get_data_quality", {"sku": sku})


def forecast_demand(sku, periods=1, save_audit=True):
    return call_factory_tool("forecast_demand", {
        "sku": sku,
        "periods": periods,
        "save_audit": save_audit,
    })


def forecast_all_demand(periods=1, save_audit=True):
    return call_factory_tool("forecast_all", {
        "periods": periods,
        "save_audit": save_audit,
    })


# Production facade

def get_all_lines():
    return call_factory_tool("production_get_lines")


def get_producible_products():
    return call_factory_tool("production_get_products")


def get_line_utilization():
    return call_factory_tool("production_get_utilization")


def identify_bottlenecks(threshold=85):
    return call_factory_tool("production_identify_bottlenecks", {"threshold": threshold})


def get_production_orders():
    return call_factory_tool("production_get_orders")


def get_production_progress(order_id=None, production_order_id=None):
    return call_factory_tool("production_get_order_progress", {
        "order_id": order_id,
        "production_order_id": production_order_id,
    })


def get_product_materials(sku=None, product_name=None, quantity=1):
    return call_factory_tool("production_get_product_materials", {
        "sku": sku,
        "product_name": product_name,
        "quantity": quantity,
    })


def check_production_feasibility(
    sku=None,
    product_name=None,
    quantity=0,
    required_date=None,
):
    return call_factory_tool("production_check_feasibility", {
        "sku": sku,
        "product_name": product_name,
        "quantity": quantity,
        "required_date": required_date,
    })


def check_capacity_after_material_arrival(
    sku=None, product_name=None, quantity=0, required_date=None, lead_time_days=0
):
    return call_factory_tool("production_check_capacity_after_arrival", {
        "sku": sku, "product_name": product_name, "quantity": quantity,
        "required_date": required_date, "lead_time_days": lead_time_days,
    })


def get_production_kpis():
    return call_factory_tool("production_get_kpis")


def get_production_summary():
    return call_factory_tool("production_get_summary")


# Report facade

def generate_management_report(scope):
    return call_factory_tool("report_generate", {"scope": scope})
