"""
freight_agent.py — Agent 3: Freight Booking Agent
Selects the most cost-effective carrier and books a shipment
via the TMS MCP server, triggered after PO approval.
"""

import asyncio
import os
import sys
from datetime import date, timedelta

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")

TMS_SERVER = os.path.join(MCP_DIR, "tms_server.py")

# Urgency threshold: if lead_time_days is 10 or less, use air freight
AIR_THRESHOLD_DAYS = 10


# ------------------------------------------------------------------
# Agent 3 — Main function
# ------------------------------------------------------------------

async def run_freight_agent(
    po_id: int,
    lead_time_days: int,
    origin: str,
    destination: str
) -> dict | None:
    """
    Select the cheapest carrier for the required mode and book the shipment.

    Args:
        po_id:           The approved Purchase Order ID.
        lead_time_days:  Supplier lead time in days (drives mode selection).
        origin:          Origin location (e.g. 'Dhaka, BD').
        destination:     Destination location (e.g. 'Colombo, LK').

    Returns:
        dict with shipment_id, carrier_name, mode, eta — or None on failure.
    """
    from fastmcp import Client

    # ------------------------------------------------------------------
    # Step 1: Determine transport mode
    # ------------------------------------------------------------------
    mode = "air" if lead_time_days <= AIR_THRESHOLD_DAYS else "sea"
    print(f"\n[Agent 3 — Freight] Lead time: {lead_time_days} days → Mode: {mode.upper()}")

    # ------------------------------------------------------------------
    # Step 2: Get available carriers for that mode
    # ------------------------------------------------------------------
    async with Client(TMS_SERVER) as tms:
        carriers_result = await tms.call_tool(
            "get_carriers",
            {"mode": mode}
        )

    carriers = carriers_result.data if hasattr(carriers_result, "data") else carriers_result
    if isinstance(carriers, dict) and "result" in carriers:
        carriers = carriers["result"]

    if not carriers:
        print(f"  [Agent 3] No {mode} carriers available.")
        return None

    print(f"  Available {mode} carriers:")
    for c in carriers:
        print(f"    - {c['name']} @ {c['rate_per_unit']}/unit")

    # ------------------------------------------------------------------
    # Step 3: Select cheapest carrier
    # ------------------------------------------------------------------
    best_carrier = min(carriers, key=lambda c: c["rate_per_unit"])
    print(f"  Selected: {best_carrier['name']} (cheapest at {best_carrier['rate_per_unit']}/unit)")

    # ------------------------------------------------------------------
    # Step 4: Calculate ETA
    # ------------------------------------------------------------------
    eta = (date.today() + timedelta(days=lead_time_days)).isoformat()

    # ------------------------------------------------------------------
    # Step 5: Book the shipment via TMS MCP server
    # ------------------------------------------------------------------
    async with Client(TMS_SERVER) as tms:
        booking_result = await tms.call_tool(
            "book_shipment",
            {
                "po_id":       po_id,
                "carrier_id":  best_carrier["carrier_id"],
                "mode":        mode,
                "origin":      origin,
                "destination": destination,
                "eta":         eta,
            }
        )

    booking = booking_result.data if hasattr(booking_result, "data") else booking_result
    if isinstance(booking, dict) and "result" in booking:
        booking = booking["result"]

    if "error" in booking:
        print(f"  [Agent 3] Error booking shipment: {booking['error']}")
        return None

    shipment_id = booking["shipment_id"]
    print(f"\n  [Agent 3] ✅ Shipment #{shipment_id} booked.")
    print(f"  Carrier : {best_carrier['name']} ({mode})")
    print(f"  Route   : {origin} → {destination}")
    print(f"  ETA     : {eta}")

    return {
        "shipment_id":   shipment_id,
        "carrier_name":  best_carrier["name"],
        "carrier_id":    best_carrier["carrier_id"],
        "mode":          mode,
        "origin":        origin,
        "destination":   destination,
        "eta":           eta,
        "status":        "booked",
    }


if __name__ == "__main__":
    result = asyncio.run(
        run_freight_agent(
            po_id=1,
            lead_time_days=18,
            origin="Dhaka, BD",
            destination="Colombo, LK"
        )
    )
    print("\n[Agent 3 Result]:", result)
