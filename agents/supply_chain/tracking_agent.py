"""
tracking_agent.py — Agent 4: Shipment Tracking Agent
Monitors active shipments via the TMS MCP server and detects
delays. Optionally checks weather at the origin port.
"""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")
TMS_SERVER = os.path.join(MCP_DIR, "tms_server.py")

load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")
STORM_THRESHOLD_WIND_KPH = 50.0

# ------------------------------------------------------------------
# LangChain Tools
# ------------------------------------------------------------------

@tool
def check_weather_tool(city: str) -> str:
    """Query current weather at a port city. Returns JSON with description and wind_kph."""
    if not OPENWEATHER_KEY:
        return json.dumps({"error": "No API key configured."})

    try:
        import urllib.request
        city_name = city.split(",")[0].strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_KEY}&units=metric"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())

        wind_kph    = data.get("wind", {}).get("speed", 0) * 3.6
        description = data["weather"][0]["description"]
        is_storm    = (
            wind_kph > STORM_THRESHOLD_WIND_KPH
            or "storm" in description.lower()
            or "thunderstorm" in description.lower()
        )
        return json.dumps({
            "city": city_name,
            "description": description,
            "wind_kph": round(wind_kph, 1),
            "is_storm": is_storm,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
async def get_shipment_status_tool(shipment_id: int) -> str:
    """Get the current status, origin, destination, and ETA of a shipment."""
    from fastmcp import Client
    async with Client(TMS_SERVER) as tms:
        result = await tms.call_tool("get_shipment_status", {"shipment_id": shipment_id})
    data = result.data if hasattr(result, "data") else result
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    return json.dumps(data)

@tool
async def update_shipment_status_tool(shipment_id: int, new_status: str) -> str:
    """Update the status of a shipment (e.g. to 'delayed')."""
    from fastmcp import Client
    async with Client(TMS_SERVER) as tms:
        result = await tms.call_tool("update_shipment_status", {"shipment_id": shipment_id, "new_status": new_status})
    data = result.data if hasattr(result, "data") else result
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    return json.dumps(data)

# ------------------------------------------------------------------
# Agent 4 — Main function
# ------------------------------------------------------------------

async def run_tracking_agent(
    shipment_id: int,
    check_weather: bool = True
) -> dict:
    """
    Track a shipment using an LLM. 
    It checks status, optionally checks weather at origin if in_transit, and sets delayed if storm detected.
    """
    print(f"\n[Agent 4 — Tracking] LLM investigating shipment #{shipment_id}...")

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    tools = [get_shipment_status_tool, update_shipment_status_tool]
    if check_weather:
        tools.append(check_weather_tool)
        
    llm_with_tools = llm.bind_tools(tools)

    prompt = f"""
You are a Shipment Tracking Agent for shipment_id {shipment_id}.
1. Call get_shipment_status_tool to get the current status, origin, and ETA.
2. If check_weather is {check_weather} AND the status is 'in_transit' AND the origin is known, call check_weather_tool for the origin city.
3. If the weather tool indicates 'is_storm' is true, call update_shipment_status_tool to set the status to 'delayed'.
4. Do not make any further tool calls once finished.
"""

    messages = [HumanMessage(content=prompt)]
    
    # Run loop
    max_steps = 4
    for _ in range(max_steps):
        msg = await llm_with_tools.ainvoke(messages)
        messages.append(msg)
        
        if not msg.tool_calls:
            break
            
        for tool_call in msg.tool_calls:
            print(f"  [Agent 4] LLM called: {tool_call['name']}({tool_call['args']})")
            
            if tool_call['name'] == 'get_shipment_status_tool':
                res = await get_shipment_status_tool.ainvoke(tool_call['args'])
            elif tool_call['name'] == 'check_weather_tool':
                res = check_weather_tool.invoke(tool_call['args'])
            elif tool_call['name'] == 'update_shipment_status_tool':
                res = await update_shipment_status_tool.ainvoke(tool_call['args'])
            else:
                res = "{}"
                
            messages.append(ToolMessage(content=res, tool_call_id=tool_call['id']))

    # Parse final state directly from the DB via MCP once more to be sure
    final_state_json = await get_shipment_status_tool.ainvoke({"shipment_id": shipment_id})
    final_state = json.loads(final_state_json)
    
    if "error" in final_state:
        return {"error": final_state["error"]}

    current_status = final_state.get("status", "unknown")
    eta            = final_state.get("eta", "N/A")
    origin         = final_state.get("origin", "")
    destination    = final_state.get("destination", "")
    carrier        = final_state.get("carrier_name", "")

    print(f"\n  Final Status  : {current_status.upper()}")
    print(f"  Carrier : {carrier}")
    print(f"  Route   : {origin} → {destination}")
    print(f"  ETA     : {eta}")

    # Generate plain-English summary
    status_messages = {
        "booked":     f"Your shipment #{shipment_id} is booked with {carrier}. Departure pending. ETA: {eta}.",
        "in_transit": f"Your shipment #{shipment_id} is in transit via {carrier}. ETA: {eta}. Route: {origin} → {destination}.",
        "delayed":    f"⚠️  Your shipment #{shipment_id} is DELAYED. Original ETA was {eta}. Please contact {carrier} for updates.",
        "delivered":  f"✅ Your shipment #{shipment_id} has been delivered. Route: {origin} → {destination}.",
    }
    summary = status_messages.get(current_status, f"Shipment #{shipment_id} status: {current_status}.")

    # Try to extract weather alert from the tool messages
    weather_alert = None
    for m in messages:
        if isinstance(m, ToolMessage) and "is_storm" in m.content:
            w_data = json.loads(m.content)
            if w_data.get("is_storm"):
                weather_alert = w_data
                break

    return {
        "shipment_id":   shipment_id,
        "status":        current_status,
        "eta":           eta,
        "carrier":       carrier,
        "origin":        origin,
        "destination":   destination,
        "weather_alert": weather_alert,
        "summary":       summary,
    }


if __name__ == "__main__":
    result = asyncio.run(
        run_tracking_agent(
            shipment_id=1,
            check_weather=False  # set True if OPENWEATHER_KEY is in .env
        )
    )
    print("\n[Agent 4 Result]:", result)
