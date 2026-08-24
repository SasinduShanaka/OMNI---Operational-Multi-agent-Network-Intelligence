import requests


# --------------------------------------------------
# Inventory Agent API
# --------------------------------------------------

INVENTORY_AGENT_URL = "http://127.0.0.1:8000"


# --------------------------------------------------
# Operations Agent
# --------------------------------------------------

def process_request(user_request: str):

    request = user_request.lower()

    # ----------------------------------------
    # Inventory-related requests
    # ----------------------------------------

    inventory_keywords = [
        "inventory",
        "stock",
        "material",
        "materials",
        "fabric",
        "shortage"
    ]

    if any(keyword in request for keyword in inventory_keywords):

        try:

            # Operations Agent communicates
            # with Inventory Agent through HTTP
            response = requests.get(
                f"{INVENTORY_AGENT_URL}/inventory/status",
                timeout=5
            )

            response.raise_for_status()

            inventory_data = response.json()

            low_stock_items = inventory_data.get(
                "low_stock_items",
                []
            )

            return {
                "agent": "Operations Agent",
                "task": "Inventory Analysis",
                "delegated_to": "Inventory Agent",
                "communication": "HTTP REST",
                "status": "success",
                "low_stock_count": len(low_stock_items),
                "results": low_stock_items
            }

        except requests.exceptions.RequestException as error:

            return {
                "agent": "Operations Agent",
                "task": "Inventory Analysis",
                "delegated_to": "Inventory Agent",
                "status": "error",
                "message": "Unable to communicate with Inventory Agent.",
                "error": str(error)
            }

    # ----------------------------------------
    # Unknown request
    # ----------------------------------------

    return {
        "agent": "Operations Agent",
        "status": "unable_to_route",
        "message": "I don't know which specialized agent should handle this request yet."
    }