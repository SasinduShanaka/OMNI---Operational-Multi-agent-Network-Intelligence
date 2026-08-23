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
# Request models
# --------------------------------------------------

class UserRequest(BaseModel):
    message: str


class InventoryRequest(BaseModel):
    material_code: str
    required_quantity: float


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
# Inventory Agent - Requirement Check
# --------------------------------------------------

@app.post("/agents/inventory/check")
def check_inventory_requirement(request: InventoryRequest):

    results = check_inventory()

    material = next(
        (
            item
            for item in results
            if item["material_code"] == request.material_code
        ),
        None
    )

    if material is None:

        return {
            "sender": "inventory_agent",
            "receiver": "operations_agent",
            "message_type": "INVENTORY_RESULT",
            "status": "NOT_FOUND",
            "material_code": request.material_code
        }

    current_stock = material["current_stock"]

    if current_stock >= request.required_quantity:

        return {
            "sender": "inventory_agent",
            "receiver": "operations_agent",
            "message_type": "INVENTORY_RESULT",
            "status": "SUFFICIENT",
            "material_code": material["material_code"],
            "material_name": material["material_name"],
            "available_quantity": current_stock,
            "required_quantity": request.required_quantity,
            "shortage": 0,
            "unit": material["unit"]
        }

    shortage = request.required_quantity - current_stock

    return {
        "sender": "inventory_agent",
        "receiver": "operations_agent",
        "message_type": "INVENTORY_RESULT",
        "status": "SHORTAGE",
        "material_code": material["material_code"],
        "material_name": material["material_name"],
        "available_quantity": current_stock,
        "required_quantity": request.required_quantity,
        "shortage": shortage,
        "unit": material["unit"]
    }


# --------------------------------------------------
# Operations Agent endpoint
# --------------------------------------------------

@app.post("/ask")
def ask_operations_agent(request: UserRequest):

    result = process_request(request.message)

    return result