"""
tracking_agent.py — Agent 4: Shipment Tracking Agent
Monitors active shipments via the TMS MCP server and detects
delays. Optionally checks weather at the origin port.
"""

import asyncio
import os
import sys

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")

TMS_SERVER = os.path.join(MCP_DIR, "tms_server.py")

# OpenWeatherMap free API key — set in backend/.env as OPENWEATHER_KEY
# If not set, weather check is silently skipped.
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")
STORM_THRESHOLD_WIND_KPH = 50.0


# ------------------------------------------------------------------
# Weather check (optional bonus)
# ------------------------------------------------------------------

def check_weather_at_port(city: str) -> dict | None:
    """
    Query OpenWeatherMap free API for current weather at a port city.
    Returns None if no API key is configured.
    """
    if not OPENWEATHER_KEY:
        return None

    try:
        import urllib.request, json
        city_name = city.split(",")[0].strip()
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city_name}&appid={OPENWEATHER_KEY}&units=metric"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())

        wind_kph    = data.get("wind", {}).get("speed", 0) * 3.6
        description = data["weather"][0]["description"]
        is_storm    = (
            wind_kph > STORM_THRESHOLD_WIND_KPH
            or "storm" in description.lower()
            or "thunderstorm" in description.lower()
        )
        return {
            "city":        city_name,
            "description": description,
            "wind_kph":    round(wind_kph, 1),
            "is_storm":    is_storm,
        }
    except Exception as e:
        print(f"  [Agent 4] Weather API error: {e}")
        return None


# ------------------------------------------------------------------
# Agent 4 — Main function
# ------------------------------------------------------------------

async def run_tracking_agent(
    shipment_id: int,
    check_weather: bool = True
) -> dict:
    """
    Get the current status of a shipment and handle exceptions.

    Args:
        shipment_id:   ID of the shipment to track.
        check_weather: Whether to call the weather API for the origin city.

    Returns:
        dict with status, eta, carrier, and a human-readable summary.
    """
    from fastmcp import Client

    print(f"\n[Agent 4 — Tracking] Checking shipment #{shipment_id}...")

    # ------------------------------------------------------------------
    # Step 1: Get current shipment status via TMS MCP
    # ------------------------------------------------------------------
    async with Client(TMS_SERVER) as tms:
        status_result = await tms.call_tool(
            "get_shipment_status",
            {"shipment_id": shipment_id}
        )

    status_data = status_result.data if hasattr(status_result, "data") else status_result
    if isinstance(status_data, dict) and "result" in status_data:
        status_data = status_data["result"]

    if "error" in status_data:
        return {"error": status_data["error"]}

    current_status = status_data.get("status", "unknown")
    eta            = status_data.get("eta", "N/A")
    origin         = status_data.get("origin", "")
    destination    = status_data.get("destination", "")
    carrier        = status_data.get("carrier_name", "")

    print(f"  Status  : {current_status.upper()}")
    print(f"  Carrier : {carrier}")
    print(f"  Route   : {origin} → {destination}")
    print(f"  ETA     : {eta}")

    # ------------------------------------------------------------------
    # Step 2 (Optional): Weather check at origin port
    # ------------------------------------------------------------------
    weather_alert = None
    if check_weather and current_status == "in_transit" and origin:
        weather = check_weather_at_port(origin)
        if weather and weather["is_storm"]:
            weather_alert = weather
            print(f"\n  ⚠️  STORM DETECTED at {weather['city']}!")
            print(f"     Conditions: {weather['description']}, Wind: {weather['wind_kph']} km/h")

            # Update shipment status to delayed
            async with Client(TMS_SERVER) as tms:
                await tms.call_tool(
                    "update_shipment_status",
                    {"shipment_id": shipment_id, "new_status": "delayed"}
                )

            current_status = "delayed"
            print(f"  Shipment #{shipment_id} marked as DELAYED. Human Manager alerted.")

    # ------------------------------------------------------------------
    # Step 3: Generate plain-English summary
    # ------------------------------------------------------------------
    status_messages = {
        "booked":     f"Your shipment #{shipment_id} is booked with {carrier}. Departure pending. ETA: {eta}.",
        "in_transit": f"Your shipment #{shipment_id} is in transit via {carrier}. ETA: {eta}. Route: {origin} → {destination}.",
        "delayed":    f"⚠️  Your shipment #{shipment_id} is DELAYED. Original ETA was {eta}. Please contact {carrier} for updates.",
        "delivered":  f"✅ Your shipment #{shipment_id} has been delivered. Route: {origin} → {destination}.",
    }
    summary = status_messages.get(current_status, f"Shipment #{shipment_id} status: {current_status}.")

    print(f"\n  Summary: {summary}")

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
