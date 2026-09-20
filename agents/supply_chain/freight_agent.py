"""
freight_agent.py — Agent 3: Freight Booking Agent
Selects the most cost-effective carrier and books a shipment
via the TMS MCP server, triggered after PO approval.
"""

import asyncio
import os
import sys
import json
from datetime import date, timedelta
try:
    from langchain_groq import ChatGroq
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
except ImportError:
    ChatGroq = None

    def tool(func):
        return func

    HumanMessage = None

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")
TMS_SERVER = os.path.join(MCP_DIR, "tms_server.py")

# Urgency threshold: if lead_time_days is 10 or less, use air freight
AIR_THRESHOLD_DAYS = 10

# ------------------------------------------------------------------
# LangChain Tools wrapping MCP
# ------------------------------------------------------------------

@tool
async def get_carriers_tool(mode: str) -> str:
    """Fetch a list of available carriers for a given mode ('air' or 'sea')."""
    from fastmcp import Client
    async with Client(TMS_SERVER) as tms:
        result = await tms.call_tool("get_carriers", {"mode": mode})
    data = result.data if hasattr(result, "data") else result
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    return json.dumps(data)

@tool
async def book_shipment_tool(po_id: int, carrier_id: int, mode: str, origin: str, destination: str, eta: str) -> str:
    """Book a shipment using a carrier_id. Returns the shipment details."""
    from fastmcp import Client
    async with Client(TMS_SERVER) as tms:
        result = await tms.call_tool("book_shipment", {
            "po_id": po_id,
            "carrier_id": carrier_id,
            "mode": mode,
            "origin": origin,
            "destination": destination,
            "eta": eta
        })
    data = result.data if hasattr(result, "data") else result
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    return json.dumps(data)


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
    Select the cheapest carrier for the required mode and book the shipment using an LLM.
    """
    print(f"\n[Agent 3 — Freight] LLM determining freight mode based on lead time ({lead_time_days} days)...")
    
    eta = (date.today() + timedelta(days=lead_time_days)).isoformat()

    if ChatGroq is None:
        print("  [Agent 3] LangChain Groq unavailable; booking cheapest carrier deterministically.")
        from fastmcp import Client

        mode = "air" if lead_time_days <= AIR_THRESHOLD_DAYS else "sea"
        async with Client(TMS_SERVER) as tms:
            carriers_result = await tms.call_tool("get_carriers", {"mode": mode})
            carriers = carriers_result.data if hasattr(carriers_result, "data") else carriers_result
            if isinstance(carriers, dict) and "result" in carriers:
                carriers = carriers["result"]
            if not carriers:
                return None

            carrier = min(carriers, key=lambda item: item.get("rate_per_unit", 0))
            booking_result = await tms.call_tool("book_shipment", {
                "po_id": po_id,
                "carrier_id": carrier["carrier_id"],
                "mode": mode,
                "origin": origin,
                "destination": destination,
                "eta": eta,
            })

        booking = booking_result.data if hasattr(booking_result, "data") else booking_result
        if isinstance(booking, dict) and "result" in booking:
            booking = booking["result"]
        if not booking or "error" in booking:
            return None

        return {
            "shipment_id": booking["shipment_id"],
            "carrier_name": carrier["name"],
            "carrier_id": carrier["carrier_id"],
            "mode": mode,
            "origin": origin,
            "destination": destination,
            "eta": eta,
            "status": "booked",
        }

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    llm_with_tools = llm.bind_tools([get_carriers_tool, book_shipment_tool])

    prompt = f"""
You are a Freight Booking Agent. 
1. Determine the mode: If lead_time_days ({lead_time_days}) <= {AIR_THRESHOLD_DAYS}, use 'air', otherwise use 'sea'.
2. Call get_carriers_tool to find available carriers for that mode.
3. Call book_shipment_tool using the carrier_id of the CHEAPEST carrier from step 2, along with po_id={po_id}, origin="{origin}", destination="{destination}", and eta="{eta}".
"""

    messages = [HumanMessage(content=prompt)]
    
    # Step 1: LLM determines mode and asks for carriers
    msg = await llm_with_tools.ainvoke(messages)
    messages.append(msg)
    
    if msg.tool_calls and msg.tool_calls[0]['name'] == 'get_carriers_tool':
        tool_call = msg.tool_calls[0]
        print(f"  [Agent 3] LLM getting carriers: {tool_call['args']}")
        tool_result = await get_carriers_tool.ainvoke(tool_call['args'])
        
        # Add tool result
        from langchain_core.messages import ToolMessage
        messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call['id']))
        
        # Step 2: LLM picks cheapest and books
        msg2 = await llm_with_tools.ainvoke(messages)
        messages.append(msg2)
        
        if msg2.tool_calls and msg2.tool_calls[0]['name'] == 'book_shipment_tool':
            book_call = msg2.tool_calls[0]
            print(f"  [Agent 3] LLM booking shipment: {book_call['args']}")
            book_result = await book_shipment_tool.ainvoke(book_call['args'])
            booking = json.loads(book_result)
            
            if "error" in booking:
                print(f"  [Agent 3] Error booking shipment: {booking['error']}")
                return None
            
            shipment_id = booking["shipment_id"]
            mode = book_call['args']['mode']
            chosen_carrier_id = book_call['args']['carrier_id']

            # Look up the real carrier name from the carriers list returned earlier
            try:
                carriers_data = json.loads(tool_result)
                carrier_name = next(
                    (c["name"] for c in carriers_data if c.get("carrier_id") == chosen_carrier_id),
                    "Unknown Carrier"
                )
            except Exception:
                carrier_name = "Unknown Carrier"

            print(f"\n  [Agent 3] Shipment #{shipment_id} booked.")
            print(f"  Mode    : {mode}")
            print(f"  Carrier : {carrier_name}")
            print(f"  Route   : {origin} -> {destination}")
            print(f"  ETA     : {eta}")

            return {
                "shipment_id":   shipment_id,
                "carrier_name":  carrier_name,
                "carrier_id":    chosen_carrier_id,
                "mode":          mode,
                "origin":        origin,
                "destination":   destination,
                "eta":           eta,
                "status":        "booked",
            }

    print(f"  [Agent 3] LLM failed to complete booking sequence.")
    return None


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
