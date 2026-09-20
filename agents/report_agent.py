"""Read-only reporting specialist: collect evidence, analyze it, and compose a brief.

Summaries are deterministic and grounded in the collected agent results. No LLM
credentials are required and reporting never triggers procurement or production.
"""
from datetime import datetime, timezone
from pathlib import Path
import logging
import sqlite3

logger = logging.getLogger(__name__)
DOMAINS = ("inventory", "forecast", "production", "supply_chain")


def utcnow():
    return datetime.now(timezone.utc)


def table(title, columns, rows):
    return {"title": title, "columns": [{"key": key, "label": label} for key, label in columns], "rows": rows}


def collect_inventory(_scope):
    from agents.inventory_agent import get_all_inventory
    return get_all_inventory()


def collect_forecast(scope):
    from agents.forecast_agent import forecast_demand, get_forecast_products
    skus = scope.get("skus") or [item["sku"] for item in get_forecast_products()]
    # Do not use forecast_all_demand: it omits unsuccessful forecasts.
    return [forecast_demand(sku, scope.get("periods", 3), save_audit=False) for sku in skus]


def collect_production(_scope):
    from agents.production_agent import get_all_lines, get_production_orders
    return {"lines": get_all_lines(), "orders": get_production_orders()}


def collect_supply_chain(_scope):
    directory = Path(__file__).resolve().parents[1] / "database/supply_chain/sqlite_db"
    result = {}
    for name, filename, query in (
        ("orders", "mock-erp.db", "SELECT po_id, qty, status, expected_delivery_date FROM purchase_orders"),
        ("shipments", "mock-tms.db", "SELECT shipment_id, reference_id, status, eta, destination FROM shipments"),
    ):
        # mode=ro prevents reporting from creating or seeding missing databases.
        connection = sqlite3.connect((directory / filename).as_uri() + "?mode=ro", uri=True, timeout=5)
        try:
            connection.row_factory = sqlite3.Row
            result[name] = [dict(row) for row in connection.execute(query).fetchall()]
        finally:
            connection.close()
    return result


COLLECTORS = {"inventory": collect_inventory, "forecast": collect_forecast,
              "production": collect_production, "supply_chain": collect_supply_chain}


def analyze(domain, evidence):
    """Return a section, grounded findings, and actions from one source snapshot."""
    section = {"key": domain, "title": domain.replace("_", " ").title(),
               "status": "success", "captured_at": utcnow().isoformat(), "tables": [], "metrics": []}
    findings, actions = [], []
    if domain == "inventory":
        low = sum(row.get("status") == "LOW_STOCK" for row in evidence)
        out = sum(row.get("status") == "OUT_OF_STOCK" for row in evidence)
        section["metrics"] = [{"label": "Materials", "value": len(evidence)}, {"label": "Low stock", "value": low}, {"label": "Out of stock", "value": out}]
        section["summary"] = f"Inventory covers {len(evidence)} materials: {low} low stock and {out} out of stock."
        section["tables"] = [table("Stock register", [("material_name", "Material"), ("material_code", "Code"), ("current_stock", "On hand"), ("reorder_level", "Reorder"), ("unit", "Unit"), ("status", "Status")], evidence)]
        if low or out:
            findings.append({"priority": "high" if out else "medium", "source": domain, "text": f"{out} materials are out of stock and {low} are below reorder level."})
            actions.append({"source": domain, "text": "Review replenishment for flagged materials; prioritize out-of-stock items before production commitments."})
    elif domain == "forecast":
        valid = [row for row in evidence if row.get("status") == "success"]
        failed = len(evidence) - len(valid)
        section["status"] = "partial" if failed and valid else "error" if failed else "success"
        section["metrics"] = [{"label": "Products analyzed", "value": len(valid)}, {"label": "Blocked forecasts", "value": failed}]
        section["summary"] = f"Demand analysis produced {len(valid)} forecasts; {failed} products could not be forecast. Forecast periods follow each product's latest recorded month."
        rows = [{"sku": row.get("sku"), "forecast": row.get("forecast"), "period": row.get("forecast_period"), "trend": row.get("trend"), "status": row.get("status"), "note": " ".join(filter(None, [row.get("message") or row.get("recommendation"), *[issue.get("message") for issue in row.get("data_quality", {}).get("issues", [])]]))} for row in evidence]
        section["tables"] = [table("Demand outlook", [("sku", "Product"), ("forecast", "Units"), ("period", "Period"), ("trend", "Trend"), ("status", "Status"), ("note", "Planning note")], rows)]
        projections = [{"sku": row["sku"], "date": point["date"], "quantity": point["quantity"]} for row in valid for point in row.get("predictions", [])]
        if projections:
            section["tables"].append(table("Monthly projections", [("sku", "Product"), ("date", "Month"), ("quantity", "Projected units")], projections))
        if failed:
            findings.append({"priority": "high", "source": domain, "text": f"{failed} forecasts are unavailable. Missing demand has not been treated as zero."})
            actions.append({"source": domain, "text": "Correct the forecast data issues listed in the demand outlook and regenerate the report."})
        rising = [row["sku"] for row in valid if row.get("trend") == "Increasing"]
        if rising:
            findings.append({"priority": "medium", "source": domain, "text": f"Increasing demand is projected for {', '.join(rising)}."})
            actions.append({"source": domain, "text": "Review capacity and bill-of-material requirements for products with increasing demand."})
    elif domain == "production":
        lines, orders = evidence["lines"], evidence["orders"]
        bottlenecks = sum(row.get("status") == "BOTTLENECK" for row in lines)
        flagged = sum(row.get("status") == "BEHIND_SCHEDULE" for row in orders)
        section["metrics"] = [{"label": "Production lines", "value": len(lines)}, {"label": "Bottlenecks", "value": bottlenecks}, {"label": "Orders flagged", "value": flagged}]
        section["summary"] = f"Production includes {len(lines)} lines and {len(orders)} orders, with {bottlenecks} bottlenecks. Order flags use the Production Agent's completion-based rule, not a delivery-date comparison."
        section["tables"] = [table("Line capacity", [("name", "Line"), ("current_utilization", "Use (%)"), ("spare_capacity_per_day", "Spare/day"), ("status", "Status")], lines), table("Order progress", [("production_order_id", "Order"), ("sku", "Product"), ("planned_quantity", "Planned"), ("completed_quantity", "Completed"), ("status", "Agent status")], orders)]
        if bottlenecks or flagged:
            findings.append({"priority": "high", "source": domain, "text": f"Production flags {bottlenecks} bottlenecks and {flagged} orders for review."})
            actions.append({"source": domain, "text": "Review flagged orders against actual due dates and assess capacity reallocation for congested lines."})
    else:
        orders, shipments = evidence["orders"], evidence["shipments"]
        delayed = sum(str(row.get("status", "")).lower() == "delayed" for row in shipments)
        section["metrics"] = [{"label": "Purchase orders", "value": len(orders)}, {"label": "Shipments", "value": len(shipments)}, {"label": "Marked delayed", "value": delayed}]
        section["summary"] = f"Supply chain records contain {len(orders)} purchase orders and {len(shipments)} shipments; {delayed} shipments are marked delayed. Source: the project's local ERP/TMS databases."
        section["tables"] = [table("Purchase orders", [("po_id", "Order"), ("qty", "Quantity"), ("status", "Status"), ("expected_delivery_date", "Expected delivery")], orders), table("Shipments", [("shipment_id", "Shipment"), ("reference_id", "Reference"), ("status", "Status"), ("eta", "ETA"), ("destination", "Destination")], shipments)]
        if delayed:
            findings.append({"priority": "high", "source": domain, "text": f"{delayed} shipments are marked delayed by the tracking source."})
            actions.append({"source": domain, "text": "Confirm revised delivery dates and check the affected purchase orders before changing production commitments."})
    if not evidence or (domain == "production" and not evidence["lines"] and not evidence["orders"]) or (domain == "supply_chain" and not evidence["orders"] and not evidence["shipments"]):
        section["status"] = "empty"
        section["summary"] = "No records were returned for this scope; this is not evidence of healthy operations."
        findings.append({"priority": "medium", "source": domain, "text": "No records available for this report section."})
    return section, findings, actions


def build_report(scope, collectors=None):
    collectors = collectors or COLLECTORS
    sections, findings, recommendations, evidence = [], [], [], {}
    started = utcnow().isoformat()
    for domain in scope["domains"]:
        try:
            raw = collectors[domain](scope)
            section, issues, actions = analyze(domain, raw)
            evidence[domain] = raw
            findings.extend(issues)
            recommendations.extend(actions)
        except Exception:
            logger.exception("Report source failed: %s", domain)
            section = {"key": domain, "title": domain.replace("_", " ").title(), "status": "error", "captured_at": utcnow().isoformat(), "summary": "Source unavailable. Check its connection and data before regenerating.", "metrics": [], "tables": []}
            findings.append({"priority": "high", "source": domain, "text": "Source could not be read; this report has incomplete coverage."})
            recommendations.append({"source": domain, "text": "Restore the source connection or correct its data and regenerate the report."})
        sections.append(section)
    healthy = sum(section["status"] == "success" for section in sections)
    status = "success" if healthy == len(sections) else "error" if all(s["status"] == "error" for s in sections) else "partial"
    findings.sort(key=lambda item: {"high": 0, "medium": 1}.get(item["priority"], 2))
    summary = f"{healthy} of {len(sections)} selected areas returned complete results. " + " ".join(section["summary"] for section in sections)
    if {"inventory", "production"}.issubset(scope["domains"]) and any(f["source"] == "inventory" for f in findings) and any(f["source"] == "production" for f in findings):
        recommendations.append({"source": "inventory + production", "text": "Review material shortages alongside production constraints. This report does not establish a causal link without order-level bill-of-material matching."})
    return {"title": scope.get("title", "Factory management report"), "intent": "management_report", "agent": "Report Agent", "delegated_to": "Report Agent", "status": status, "scope": scope, "started_at": started, "generated_at": utcnow().isoformat(), "summary_method": "Evidence-based rules", "answer": summary, "sections": sections, "findings": findings, "recommendations": recommendations, "evidence": evidence,
            "notes": "Current-state snapshot, not historical daily/monthly totals. Sources are captured sequentially. Forecasts are estimates. Scheduled reports capture the state when executed."}
