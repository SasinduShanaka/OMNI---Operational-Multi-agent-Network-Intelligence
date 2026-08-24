import os
from pymongo import MongoClient
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")


# ============================================================
# MONGODB
# ============================================================

client = MongoClient(MONGO_URI)

db = client["OMNI_DB"]

inventory_collection = db["inventory"]


# ============================================================
# HELPER
# ============================================================

def format_inventory_item(item):
    """
    Convert a MongoDB inventory document into a clean
    dictionary used by the agents.
    """

    current_stock = item.get("current_stock", 0)
    reorder_level = item.get("reorder_level", 0)

    if current_stock <= 0:
        status = "OUT_OF_STOCK"
        shortage = reorder_level

    elif current_stock < reorder_level:
        status = "LOW_STOCK"
        shortage = reorder_level - current_stock

    else:
        status = "STOCK_OK"
        shortage = 0

    return {
        "material_code": item.get("material_code"),
        "material_name": item.get("material_name"),
        "status": status,
        "current_stock": current_stock,
        "reorder_level": reorder_level,
        "shortage": shortage,
        "unit": item.get("unit", "units"),
        "recommendation": (
            "Immediate replenishment required"
            if status == "OUT_OF_STOCK"
            else "Consider replenishment"
            if status == "LOW_STOCK"
            else "No immediate action required"
        )
    }


# ============================================================
# 1. GET COMPLETE INVENTORY
# ============================================================

def get_all_inventory():
    """
    Return every material currently stored in inventory.
    """

    items = inventory_collection.find()

    return [
        format_inventory_item(item)
        for item in items
    ]


# ============================================================
# 2. CHECK INVENTORY
# ============================================================

def check_inventory():
    """
    Analyze the status of every inventory item.
    """

    return get_all_inventory()


# ============================================================
# 3. GET LOW-STOCK MATERIALS
# ============================================================

def get_low_stock():
    """
    Return materials whose stock is below the reorder level.
    """

    return [
        item
        for item in get_all_inventory()
        if item["status"] == "LOW_STOCK"
    ]


# ============================================================
# 4. GET OUT-OF-STOCK MATERIALS
# ============================================================

def get_out_of_stock():
    """
    Return materials that currently have zero stock.
    """

    return [
        item
        for item in get_all_inventory()
        if item["status"] == "OUT_OF_STOCK"
    ]


# ============================================================
# 5. GET HEALTHY-STOCK MATERIALS
# ============================================================

def get_healthy_stock():
    """
    Return materials that are at or above their reorder level.
    """

    return [
        item
        for item in get_all_inventory()
        if item["status"] == "STOCK_OK"
    ]


# ============================================================
# 6. GET SPECIFIC MATERIAL
# ============================================================

def get_material(material_name=None, material_code=None):
    """
    Find a specific material using either its name or code.
    """

    query = {}

    if material_code:

        query["material_code"] = material_code

    elif material_name:

        query["material_name"] = {
            "$regex": material_name,
            "$options": "i"
        }

    else:

        return None

    item = inventory_collection.find_one(query)

    if not item:
        return None

    return format_inventory_item(item)


# ============================================================
# 7. CHECK WHETHER MATERIAL REQUIREMENT CAN BE SATISFIED
# ============================================================

def check_inventory_requirement(
    material_name=None,
    material_code=None,
    required_quantity=0
):
    """
    Determine whether the available inventory can satisfy
    a required quantity.
    """

    item = get_material(
        material_name=material_name,
        material_code=material_code
    )

    if item is None:

        return {
            "status": "NOT_FOUND",
            "material_name": material_name,
            "material_code": material_code,
            "required_quantity": required_quantity,
            "message": "Material was not found in inventory."
        }

    available_quantity = item["current_stock"]

    shortage = max(
        required_quantity - available_quantity,
        0
    )

    if available_quantity >= required_quantity:

        return {
            "status": "SUFFICIENT",
            "material_code": item["material_code"],
            "material_name": item["material_name"],
            "available_quantity": available_quantity,
            "required_quantity": required_quantity,
            "shortage": 0,
            "unit": item["unit"],
            "message": "There is enough stock to satisfy the requirement."
        }

    return {
        "status": "SHORTAGE",
        "material_code": item["material_code"],
        "material_name": item["material_name"],
        "available_quantity": available_quantity,
        "required_quantity": required_quantity,
        "shortage": shortage,
        "unit": item["unit"],
        "message": "Additional material is required."
    }


# ============================================================
# 8. GET REORDER REQUIREMENTS
# ============================================================

def get_reorder_requirements():
    """
    Determine which materials need replenishment and
    how much is required to reach the reorder level.
    """

    low_stock = get_low_stock()

    return [
        {
            "material_code": item["material_code"],
            "material_name": item["material_name"],
            "current_stock": item["current_stock"],
            "reorder_level": item["reorder_level"],
            "reorder_quantity": item["shortage"],
            "unit": item["unit"],
            "status": item["status"]
        }
        for item in low_stock
    ]


# ============================================================
# 9. GET TOTAL STOCK
# ============================================================

def get_total_stock():
    """
    Calculate the total quantity across inventory.
    """

    items = get_all_inventory()

    total_stock = 0

    units = set()

    for item in items:

        total_stock += item["current_stock"]

        if item["unit"]:
            units.add(item["unit"])

    return {
        "total_stock": total_stock,
        "units": list(units),
        "material_count": len(items)
    }


# ============================================================
# 10. INVENTORY SUMMARY
# ============================================================

def get_inventory_summary():
    """
    Provide a high-level inventory health summary.
    """

    inventory = get_all_inventory()

    total_materials = len(inventory)

    low_stock = [
        item
        for item in inventory
        if item["status"] == "LOW_STOCK"
    ]

    out_of_stock = [
        item
        for item in inventory
        if item["status"] == "OUT_OF_STOCK"
    ]

    healthy = [
        item
        for item in inventory
        if item["status"] == "STOCK_OK"
    ]

    return {
        "total_materials": total_materials,
        "healthy_materials": len(healthy),
        "low_stock_materials": len(low_stock),
        "out_of_stock_materials": len(out_of_stock),
        "inventory_health": (
            "CRITICAL"
            if out_of_stock
            else "NEEDS_ATTENTION"
            if low_stock
            else "HEALTHY"
        )
    }


# ============================================================
# 11. GET LARGEST SHORTAGES
# ============================================================

def get_largest_shortages(limit=5):
    """
    Return materials with the largest shortages.
    """

    low_stock = get_low_stock()

    sorted_items = sorted(
        low_stock,
        key=lambda item: item["shortage"],
        reverse=True
    )

    return sorted_items[:limit]


# ============================================================
# 12. GET INVENTORY BY STATUS
# ============================================================

def get_inventory_by_status(status):
    """
    Filter inventory by status.

    Supported statuses:
        LOW_STOCK
        OUT_OF_STOCK
        STOCK_OK
    """

    status = status.upper()

    return [
        item
        for item in get_all_inventory()
        if item["status"] == status
    ]


# ============================================================
# 13. INVENTORY KPIs
# ============================================================

def get_inventory_kpis():
    """
    Calculate basic inventory KPIs.
    """

    inventory = get_all_inventory()

    total_materials = len(inventory)

    if total_materials == 0:

        return {
            "total_materials": 0,
            "healthy_percentage": 0,
            "low_stock_percentage": 0,
            "out_of_stock_percentage": 0
        }

    healthy = sum(
        1
        for item in inventory
        if item["status"] == "STOCK_OK"
    )

    low_stock = sum(
        1
        for item in inventory
        if item["status"] == "LOW_STOCK"
    )

    out_of_stock = sum(
        1
        for item in inventory
        if item["status"] == "OUT_OF_STOCK"
    )

    return {
        "total_materials": total_materials,

        "healthy_percentage": round(
            healthy / total_materials * 100,
            2
        ),

        "low_stock_percentage": round(
            low_stock / total_materials * 100,
            2
        ),

        "out_of_stock_percentage": round(
            out_of_stock / total_materials * 100,
            2
        )
    }