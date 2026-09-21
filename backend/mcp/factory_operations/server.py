"""MCP tools for OMNI's inventory, forecast, production, and report domains.

The specialist modules remain responsible for their business rules. This server
provides the stable, controlled protocol boundary used by LangGraph, FastAPI,
and the report scheduler. It can be used in-process by the local application or
started as a standalone stdio MCP server.
"""

from typing import Any

from fastmcp import FastMCP

from agents import forecast_agent, inventory_agent, production_agent


mcp = FastMCP("OMNI Factory Operations Server")


# Inventory tools

@mcp.tool()
def inventory_get_all() -> list[dict]:
    """Return every material in factory inventory."""
    return inventory_agent.get_all_inventory()


@mcp.tool()
def inventory_check() -> list[dict]:
    """Return the inventory dashboard payload and stock classifications."""
    return inventory_agent.check_inventory()


@mcp.tool()
def inventory_add_item(
    material_name: str,
    current_stock: float,
    reorder_level: float,
    unit: str = "units",
    material_code: str | None = None,
    classification: str | None = "B",
) -> dict:
    """Create or update a validated inventory material."""
    return inventory_agent.add_inventory_item(
        material_name=material_name,
        current_stock=current_stock,
        reorder_level=reorder_level,
        unit=unit,
        material_code=material_code,
        classification=classification,
    )


@mcp.tool()
def inventory_get_low_stock() -> list[dict]:
    """Return materials below their reorder levels."""
    return inventory_agent.get_low_stock()


@mcp.tool()
def inventory_get_out_of_stock() -> list[dict]:
    """Return materials with no available stock."""
    return inventory_agent.get_out_of_stock()


@mcp.tool()
def inventory_get_healthy_stock() -> list[dict]:
    """Return materials at or above their reorder levels."""
    return inventory_agent.get_healthy_stock()


@mcp.tool()
def inventory_get_material(
    material_name: str | None = None,
    material_code: str | None = None,
) -> dict | None:
    """Find one material by its name or code."""
    return inventory_agent.get_material(material_name, material_code)


@mcp.tool()
def inventory_check_requirement(
    material_name: str | None = None,
    material_code: str | None = None,
    required_quantity: float = 0,
) -> dict:
    """Compare a material requirement with current stock."""
    return inventory_agent.check_inventory_requirement(
        material_name=material_name,
        material_code=material_code,
        required_quantity=required_quantity,
    )


@mcp.tool()
def inventory_get_reorder_requirements() -> list[dict]:
    """Return replenishment quantities for materials below reorder level."""
    return inventory_agent.get_reorder_requirements()


@mcp.tool()
def inventory_get_total_stock() -> dict:
    """Return total stock quantities and value-independent totals."""
    return inventory_agent.get_total_stock()


@mcp.tool()
def inventory_get_summary() -> dict:
    """Return a high-level inventory health summary."""
    return inventory_agent.get_inventory_summary()


@mcp.tool()
def inventory_get_largest_shortages(limit: int = 5) -> list[dict]:
    """Return the largest inventory shortages, bounded by limit."""
    return inventory_agent.get_largest_shortages(limit)


@mcp.tool()
def inventory_get_kpis() -> dict:
    """Return inventory key performance indicators."""
    return inventory_agent.get_inventory_kpis()


# Forecast tools

@mcp.tool()
def forecast_get_products() -> list[dict]:
    """Return products with recorded demand history."""
    return forecast_agent.get_forecast_products()


@mcp.tool()
def forecast_get_data_quality(sku: str) -> dict:
    """Validate the demand history available for a product."""
    return forecast_agent.get_demand_quality(sku)


@mcp.tool()
def forecast_demand(
    sku: str,
    periods: int = 1,
    save_audit: bool = True,
) -> dict:
    """Forecast one to twelve monthly periods for a product."""
    return forecast_agent.forecast_demand(sku, periods, save_audit)


@mcp.tool()
def forecast_all(periods: int = 1, save_audit: bool = True) -> list[dict]:
    """Forecast all products with usable demand history."""
    return forecast_agent.forecast_all_demand(periods, save_audit)


# Production tools

@mcp.tool()
def production_get_lines() -> list[dict]:
    """Return all production lines and their capacity status."""
    return production_agent.get_all_lines()


@mcp.tool()
def production_get_products() -> list[dict]:
    """Return products that have production data."""
    return production_agent.get_producible_products()


@mcp.tool()
def production_get_utilization() -> list[dict]:
    """Return utilization information for production lines."""
    return production_agent.get_line_utilization()


@mcp.tool()
def production_identify_bottlenecks(threshold: float = 85) -> list[dict]:
    """Return lines at or above the supplied utilization threshold."""
    return production_agent.identify_bottlenecks(threshold)


@mcp.tool()
def production_get_orders() -> list[dict]:
    """Return current production orders and progress."""
    return production_agent.get_production_orders()


@mcp.tool()
def production_get_order_progress(
    order_id: str | None = None,
    production_order_id: str | None = None,
) -> dict | None:
    """Return progress for one production order."""
    return production_agent.get_production_progress(order_id, production_order_id)


@mcp.tool()
def production_get_product_materials(
    sku: str | None = None,
    product_name: str | None = None,
    quantity: float = 1,
) -> dict:
    """Return bill-of-material requirements for a product quantity."""
    return production_agent.get_product_materials(sku, product_name, quantity)


@mcp.tool()
def production_check_feasibility(
    sku: str | None = None,
    product_name: str | None = None,
    quantity: float = 0,
    required_date: str | None = None,
) -> dict:
    """Assess product capacity, deadline, and inventory feasibility."""
    return production_agent.check_production_feasibility(
        sku=sku,
        product_name=product_name,
        quantity=quantity,
        required_date=required_date,
    )


@mcp.tool()
def production_get_kpis() -> dict:
    """Return production key performance indicators."""
    return production_agent.get_production_kpis()


@mcp.tool()
def production_get_summary() -> dict:
    """Return a high-level production summary."""
    return production_agent.get_production_summary()


# Report tool

@mcp.tool()
def report_generate(scope: dict[str, Any]) -> dict:
    """Build a read-only, evidence-grounded factory management report."""
    # Lazy import avoids loading reporting code for requests that do not use it.
    from agents.report_agent import build_report

    return build_report(scope)


if __name__ == "__main__":
    mcp.run(transport="stdio")
