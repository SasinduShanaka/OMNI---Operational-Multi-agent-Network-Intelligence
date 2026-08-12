from fastapi import FastAPI
from pydantic import BaseModel

from agents.inventory_agent import check_inventory
from agents.operations_agent import process_request


app = FastAPI(
    title="OMNI API",
    description="Operational Multi-agent Network Intelligence",
    version="1.0.0"
)


# --------------------------------------------------
# Request model
# --------------------------------------------------

class UserRequest(BaseModel):
    message: str


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "system": "OMNI",
        "message": "OMNI backend is running!",
        "status": "online"
    }


# --------------------------------------------------
# Inventory Agent endpoint
# --------------------------------------------------

@app.get("/inventory/status")
def inventory_status():

    results = check_inventory()

    low_stock_items = [
        item
        for item in results
        if item["status"] == "LOW_STOCK"
    ]

    return {
        "agent": "Inventory Agent",
        "status": "success",
        "total_items_checked": len(results),
        "low_stock_count": len(low_stock_items),
        "low_stock_items": low_stock_items
    }


# --------------------------------------------------
# Operations Agent endpoint
# --------------------------------------------------

@app.post("/ask")
def ask_operations_agent(request: UserRequest):

    result = process_request(request.message)

    return result