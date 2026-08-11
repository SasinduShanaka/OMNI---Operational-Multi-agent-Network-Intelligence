from fastapi import FastAPI
from agents.inventory_agent import check_inventory

app = FastAPI(
    title="OMNI API",
    description="Operational Multi-agent Network Intelligence",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "system": "OMNI",
        "message": "OMNI backend is running!",
        "status": "online"
    }


@app.get("/inventory/status")
def inventory_status():

    results = check_inventory()

    low_stock_items = [
        item for item in results
        if item["status"] == "LOW_STOCK"
    ]

    return {
        "agent": "Inventory Agent",
        "status": "success",
        "total_items_checked": len(results),
        "low_stock_count": len(low_stock_items),
        "low_stock_items": low_stock_items
    }