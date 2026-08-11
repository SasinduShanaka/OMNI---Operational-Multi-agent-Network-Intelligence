import os
from pymongo import MongoClient
from dotenv import load_dotenv


# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")


# Connect to MongoDB
client = MongoClient(MONGO_URI)

db = client["OMNI_DB"]

inventory_collection = db["inventory"]


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