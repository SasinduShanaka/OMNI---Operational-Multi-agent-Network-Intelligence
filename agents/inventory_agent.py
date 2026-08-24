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
# MONGODB CONNECTION
# ============================================================

client = MongoClient(MONGO_URI)

db = client["OMNI_DB"]

inventory_collection = db["inventory"]


# ============================================================
# 1. CHECK ALL INVENTORY
# ============================================================

def check_inventory():

    inventory_items = inventory_collection.find()

    results = []

    for item in inventory_items:

        current_stock = item["current_stock"]
        reorder_level = item["reorder_level"]

        if current_stock < reorder_level:

            shortage = reorder_level - current_stock

            results.append({
                "material_code": item["material_code"],
                "material_name": item["material_name"],
                "status": "LOW_STOCK",
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "shortage": shortage,
                "unit": item["unit"],
                "recommendation": "Consider replenishment"
            })

        else:

            results.append({
                "material_code": item["material_code"],
                "material_name": item["material_name"],
                "status": "STOCK_OK",
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "shortage": 0,
                "unit": item["unit"],
                "recommendation": "No immediate action required"
            })

    return results


# ============================================================
# 2. GET LOW-STOCK MATERIALS
# ============================================================

def get_low_stock():

    results = check_inventory()

    return [
        item
        for item in results
        if item["status"] == "LOW_STOCK"
    ]


# ============================================================
# 3. GET A SPECIFIC MATERIAL
# ============================================================

def get_material(material_name=None, material_code=None):

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

    current_stock = item["current_stock"]
    reorder_level = item["reorder_level"]

    if current_stock < reorder_level:

        status = "LOW_STOCK"
        shortage = reorder_level - current_stock
        recommendation = "Consider replenishment"

    else:

        status = "STOCK_OK"
        shortage = 0
        recommendation = "No immediate action required"

    return {
        "material_code": item["material_code"],
        "material_name": item["material_name"],
        "status": status,
        "current_stock": current_stock,
        "reorder_level": reorder_level,
        "shortage": shortage,
        "unit": item["unit"],
        "recommendation": recommendation
    }


# ============================================================
# 4. CALCULATE TOTAL STOCK
# ============================================================

def get_total_stock():

    inventory_items = inventory_collection.find()

    total = 0
    unit = None

    for item in inventory_items:

        total += item["current_stock"]

        if unit is None:
            unit = item["unit"]

    return {
        "total_stock": total,
        "unit": unit
    }


# ============================================================
# 5. CHECK INVENTORY REQUIREMENT
# ============================================================

def check_inventory_requirement(
    material_name=None,
    material_code=None,
    required_quantity=0
):

    # --------------------------------------------------------
    # Find the material
    # --------------------------------------------------------

    material = None

    if material_code:

        material = inventory_collection.find_one({
            "material_code": material_code
        })

    elif material_name:

        material = inventory_collection.find_one({
            "material_name": {
                "$regex": material_name,
                "$options": "i"
            }
        })

    # --------------------------------------------------------
    # Material not found
    # --------------------------------------------------------

    if not material:

        return {
            "status": "NOT_FOUND",
            "material_name": material_name,
            "material_code": material_code,
            "required_quantity": required_quantity,
            "message": "Material not found in inventory."
        }

    # --------------------------------------------------------
    # Get current stock
    # --------------------------------------------------------

    current_stock = material["current_stock"]

    unit = material["unit"]

    # --------------------------------------------------------
    # Check whether stock is sufficient
    # --------------------------------------------------------

    if current_stock >= required_quantity:

        return {
            "status": "SUFFICIENT",
            "material_code": material["material_code"],
            "material_name": material["material_name"],
            "available_quantity": current_stock,
            "required_quantity": required_quantity,
            "shortage": 0,
            "unit": unit,
            "message": "There is enough stock to satisfy the requirement."
        }

    # --------------------------------------------------------
    # Calculate shortage
    # --------------------------------------------------------

    shortage = required_quantity - current_stock

    return {
        "status": "SHORTAGE",
        "material_code": material["material_code"],
        "material_name": material["material_name"],
        "available_quantity": current_stock,
        "required_quantity": required_quantity,
        "shortage": shortage,
        "unit": unit,
        "message": "Additional material is required."
    }