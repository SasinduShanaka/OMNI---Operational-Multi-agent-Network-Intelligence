from agents.inventory_agent import check_inventory


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

        inventory_result = check_inventory()

        low_stock_items = [
            item
            for item in inventory_result
            if item["status"] == "LOW_STOCK"
        ]

        return {
            "agent": "Operations Agent",
            "task": "Inventory Analysis",
            "delegated_to": "Inventory Agent",
            "status": "success",
            "low_stock_count": len(low_stock_items),
            "results": low_stock_items
        }

    # ----------------------------------------
    # Unknown request
    # ----------------------------------------

    return {
        "agent": "Operations Agent",
        "status": "unable_to_route",
        "message": "I don't know which specialized agent should handle thi request yet."
    }