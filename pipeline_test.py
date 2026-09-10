"""
pipeline_test.py
End-to-end manual test of the 4-agent supply chain pipeline.
Run from the project root:
    python pipeline_test.py
"""

import asyncio
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from agents.supply_chain.sourcing_agent   import run_sourcing_agent
from agents.supply_chain.purchasing_agent import run_purchasing_agent
from agents.supply_chain.freight_agent    import run_freight_agent
from agents.supply_chain.tracking_agent   import run_tracking_agent


async def run_pipeline(user_request: str = "We need 300 meters of organic cotton fabric."):

    print("=" * 60)
    print("  OMNI — Supply Chain Pipeline")
    print(f"  Request: \"{user_request}\"")
    print("=" * 60)

    # ----------------------------------------------------------------
    # Phase 1: Agent 1 — Sourcing & Compliance
    # ----------------------------------------------------------------
    supplier = await run_sourcing_agent(
        material_type="fabric_mill",
        requirement_id=2,
        compliance_keywords=["Organic Cotton", "Child-Labor Free"]
    )

    if not supplier:
        print("\n[Pipeline] ❌ Stopped: No compliant supplier found.")
        return

    # ----------------------------------------------------------------
    # Phase 2: Agent 2 — Purchasing (Human-in-the-Loop)
    # ----------------------------------------------------------------
    po = await run_purchasing_agent(
        supplier_id=supplier["supplier_id"],
        supplier_name=supplier["supplier_name"],
        requirement_id=supplier["requirement_id"],
        qty=300.0,
        total_value=78000.0,
        auto_approve=False      # Change to True for fully automated testing
    )

    if not po:
        print("\n[Pipeline] ❌ Stopped: PO rejected by Human Manager.")
        return

    # ----------------------------------------------------------------
    # Phase 3: Agent 3 — Freight Booking
    # ----------------------------------------------------------------
    shipment = await run_freight_agent(
        po_id=po["po_id"],
        lead_time_days=supplier["lead_time_days"],
        origin=f"{supplier['country']}",
        destination="Colombo, LK"
    )

    if not shipment:
        print("\n[Pipeline] ❌ Stopped: Freight booking failed.")
        return

    # ----------------------------------------------------------------
    # Phase 4: Agent 4 — Tracking
    # ----------------------------------------------------------------
    tracking = await run_tracking_agent(
        shipment_id=shipment["shipment_id"],
        check_weather=False
    )

    # ----------------------------------------------------------------
    # Final summary
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE ✅")
    print("=" * 60)
    print(f"  Supplier  : {supplier['supplier_name']}")
    print(f"  PO ID     : #{po['po_id']}")
    print(f"  Shipment  : #{shipment['shipment_id']} via {shipment['carrier_name']}")
    print(f"  ETA       : {shipment['eta']}")
    print(f"  Status    : {tracking['status'].upper()}")
    print(f"\n  Manager Summary:")
    print(f"  {tracking['summary']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
