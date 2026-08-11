import os
import random
from datetime import datetime, timedelta

from pymongo import MongoClient
from dotenv import load_dotenv


# --------------------------------------------------
# 1. Load MongoDB connection string
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI not found in backend/.env")


# --------------------------------------------------
# 2. Connect to MongoDB
# --------------------------------------------------

client = MongoClient(MONGO_URI)

db = client["OMNI_DB"]

print("Connected to MongoDB successfully!")


# --------------------------------------------------
# 3. Clear existing synthetic data
# --------------------------------------------------

collections = [
    "products",
    "materials",
    "inventory",
    "suppliers",
    "demand_history",
    "customer_orders",
    "production_lines",
    "production_orders",
    "shipments",
    "agent_activity"
]

for collection in collections:
    db[collection].delete_many({})

print("Old synthetic data cleared.")


# --------------------------------------------------
# 4. PRODUCTS
# --------------------------------------------------

products = [
    {
        "sku": "GAR-001",
        "name": "Classic Black Polo",
        "category": "Polo Shirt",
        "fabric": "Cotton",
        "color": "Black",
        "unit_price": 2500,
        "target_quantity": 10000
    },
    {
        "sku": "GAR-002",
        "name": "White Cotton T-Shirt",
        "category": "T-Shirt",
        "fabric": "Cotton",
        "color": "White",
        "unit_price": 1800,
        "target_quantity": 8000
    },
    {
        "sku": "GAR-003",
        "name": "Navy Formal Shirt",
        "category": "Formal Shirt",
        "fabric": "Cotton",
        "color": "Navy",
        "unit_price": 3200,
        "target_quantity": 5000
    },
    {
        "sku": "GAR-004",
        "name": "Grey Hoodie",
        "category": "Hoodie",
        "fabric": "Fleece",
        "color": "Grey",
        "unit_price": 4500,
        "target_quantity": 4000
    },
    {
        "sku": "GAR-005",
        "name": "Women's Casual Top",
        "category": "Casual Wear",
        "fabric": "Rayon",
        "color": "Pink",
        "unit_price": 2200,
        "target_quantity": 6000
    },
    {
        "sku": "GAR-006",
        "name": "Blue Denim Shirt",
        "category": "Denim",
        "fabric": "Denim",
        "color": "Blue",
        "unit_price": 3800,
        "target_quantity": 3500
    },
    {
        "sku": "GAR-007",
        "name": "Green Sports T-Shirt",
        "category": "Sportswear",
        "fabric": "Polyester",
        "color": "Green",
        "unit_price": 2100,
        "target_quantity": 7000
    },
    {
        "sku": "GAR-008",
        "name": "Beige Cargo Pants",
        "category": "Trousers",
        "fabric": "Cotton",
        "color": "Beige",
        "unit_price": 4200,
        "target_quantity": 4500
    }
]

db.products.insert_many(products)

print(f"Inserted {len(products)} products.")


# --------------------------------------------------
# 5. MATERIALS
# --------------------------------------------------

materials = [
    {
        "material_code": "FAB-001",
        "name": "Black Cotton Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-002",
        "name": "White Cotton Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-003",
        "name": "Navy Cotton Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-004",
        "name": "Grey Fleece Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-005",
        "name": "Pink Rayon Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-006",
        "name": "Blue Denim Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "FAB-007",
        "name": "Polyester Fabric",
        "category": "Fabric",
        "unit": "meters"
    },
    {
        "material_code": "THR-001",
        "name": "Black Sewing Thread",
        "category": "Thread",
        "unit": "spools"
    },
    {
        "material_code": "THR-002",
        "name": "White Sewing Thread",
        "category": "Thread",
        "unit": "spools"
    },
    {
        "material_code": "BTN-001",
        "name": "Polo Buttons",
        "category": "Buttons",
        "unit": "pieces"
    },
    {
        "material_code": "LBL-001",
        "name": "Garment Labels",
        "category": "Labels",
        "unit": "pieces"
    },
    {
        "material_code": "PKG-001",
        "name": "Garment Packaging",
        "category": "Packaging",
        "unit": "pieces"
    }
]

db.materials.insert_many(materials)

print(f"Inserted {len(materials)} materials.")


# --------------------------------------------------
# 6. INVENTORY
# --------------------------------------------------

inventory = [
    {
        "material_code": "FAB-001",
        "material_name": "Black Cotton Fabric",
        "current_stock": 3200,
        "reserved_stock": 500,
        "reorder_level": 3500,
        "safety_stock": 1000,
        "unit": "meters"
    },
    {
        "material_code": "FAB-002",
        "material_name": "White Cotton Fabric",
        "current_stock": 5000,
        "reserved_stock": 800,
        "reorder_level": 3000,
        "safety_stock": 1000,
        "unit": "meters"
    },
    {
        "material_code": "FAB-003",
        "material_name": "Navy Cotton Fabric",
        "current_stock": 2500,
        "reserved_stock": 400,
        "reorder_level": 2500,
        "safety_stock": 800,
        "unit": "meters"
    },
    {
        "material_code": "FAB-004",
        "material_name": "Grey Fleece Fabric",
        "current_stock": 1800,
        "reserved_stock": 300,
        "reorder_level": 2000,
        "safety_stock": 500,
        "unit": "meters"
    },
    {
        "material_code": "FAB-005",
        "material_name": "Pink Rayon Fabric",
        "current_stock": 3500,
        "reserved_stock": 500,
        "reorder_level": 2000,
        "safety_stock": 600,
        "unit": "meters"
    },
    {
        "material_code": "FAB-006",
        "material_name": "Blue Denim Fabric",
        "current_stock": 2200,
        "reserved_stock": 300,
        "reorder_level": 1800,
        "safety_stock": 500,
        "unit": "meters"
    },
    {
        "material_code": "FAB-007",
        "material_name": "Polyester Fabric",
        "current_stock": 4500,
        "reserved_stock": 500,
        "reorder_level": 3000,
        "safety_stock": 800,
        "unit": "meters"
    },
    {
        "material_code": "THR-001",
        "material_name": "Black Sewing Thread",
        "current_stock": 850,
        "reserved_stock": 100,
        "reorder_level": 500,
        "safety_stock": 150,
        "unit": "spools"
    },
    {
        "material_code": "THR-002",
        "material_name": "White Sewing Thread",
        "current_stock": 1000,
        "reserved_stock": 150,
        "reorder_level": 500,
        "safety_stock": 150,
        "unit": "spools"
    },
    {
        "material_code": "BTN-001",
        "material_name": "Polo Buttons",
        "current_stock": 25000,
        "reserved_stock": 3000,
        "reorder_level": 10000,
        "safety_stock": 3000,
        "unit": "pieces"
    },
    {
        "material_code": "LBL-001",
        "material_name": "Garment Labels",
        "current_stock": 18000,
        "reserved_stock": 2000,
        "reorder_level": 8000,
        "safety_stock": 2000,
        "unit": "pieces"
    },
    {
        "material_code": "PKG-001",
        "material_name": "Garment Packaging",
        "current_stock": 20000,
        "reserved_stock": 3000,
        "reorder_level": 8000,
        "safety_stock": 2000,
        "unit": "pieces"
    }
]

db.inventory.insert_many(inventory)

print(f"Inserted {len(inventory)} inventory records.")


# --------------------------------------------------
# 7. SUPPLIERS
# --------------------------------------------------

suppliers = [
    {
        "supplier_id": "SUP-001",
        "name": "Ceylon Textiles",
        "materials": ["FAB-001", "FAB-002", "FAB-003"],
        "price_score": 4.5,
        "quality_score": 4.8,
        "lead_time_days": 7,
        "service_score": 4.6
    },
    {
        "supplier_id": "SUP-002",
        "name": "Lanka Fabrics",
        "materials": ["FAB-001", "FAB-004"],
        "price_score": 4.2,
        "quality_score": 4.5,
        "lead_time_days": 10,
        "service_score": 4.2
    },
    {
        "supplier_id": "SUP-003",
        "name": "Prime Materials",
        "materials": ["FAB-002", "FAB-005"],
        "price_score": 4.7,
        "quality_score": 4.4,
        "lead_time_days": 6,
        "service_score": 4.5
    },
    {
        "supplier_id": "SUP-004",
        "name": "Asian Textile Suppliers",
        "materials": ["FAB-006", "FAB-007"],
        "price_score": 4.8,
        "quality_score": 4.3,
        "lead_time_days": 12,
        "service_score": 4.0
    }
]

db.suppliers.insert_many(suppliers)

print(f"Inserted {len(suppliers)} suppliers.")


# --------------------------------------------------
# 8. DEMAND HISTORY
# --------------------------------------------------

demand_history = []

products_for_demand = [
    ("GAR-001", "Classic Black Polo", 1200),
    ("GAR-002", "White Cotton T-Shirt", 1000),
    ("GAR-003", "Navy Formal Shirt", 650),
    ("GAR-004", "Grey Hoodie", 500),
    ("GAR-005", "Women's Casual Top", 800)
]

start_date = datetime.now() - timedelta(days=180)

for product_id, product_name, base_demand in products_for_demand:

    for month in range(6):

        demand_date = start_date + timedelta(days=month * 30)

        variation = random.randint(-150, 200)

        quantity = max(100, base_demand + variation)

        demand_history.append({
            "sku": product_id,
            "product_name": product_name,
            "date": demand_date,
            "quantity": quantity
        })

db.demand_history.insert_many(demand_history)

print(f"Inserted {len(demand_history)} demand records.")


# --------------------------------------------------
# 9. CUSTOMER ORDERS
# --------------------------------------------------

customer_orders = [
    {
        "order_id": "ORD-001",
        "sku": "GAR-001",
        "quantity": 10000,
        "required_date": datetime.now() + timedelta(days=30),
        "status": "Pending"
    },
    {
        "order_id": "ORD-002",
        "sku": "GAR-002",
        "quantity": 6000,
        "required_date": datetime.now() + timedelta(days=25),
        "status": "Confirmed"
    },
    {
        "order_id": "ORD-003",
        "sku": "GAR-003",
        "quantity": 4000,
        "required_date": datetime.now() + timedelta(days=40),
        "status": "Pending"
    },
    {
        "order_id": "ORD-004",
        "sku": "GAR-004",
        "quantity": 3000,
        "required_date": datetime.now() + timedelta(days=45),
        "status": "Confirmed"
    }
]

db.customer_orders.insert_many(customer_orders)

print(f"Inserted {len(customer_orders)} customer orders.")


# --------------------------------------------------
# 10. PRODUCTION LINES
# --------------------------------------------------

production_lines = [
    {
        "line_id": "LINE-001",
        "name": "Polo Production Line",
        "capacity_per_day": 500,
        "current_utilization": 85,
        "status": "Active"
    },
    {
        "line_id": "LINE-002",
        "name": "T-Shirt Production Line",
        "capacity_per_day": 700,
        "current_utilization": 70,
        "status": "Active"
    },
    {
        "line_id": "LINE-003",
        "name": "Formal Shirt Line",
        "capacity_per_day": 350,
        "current_utilization": 90,
        "status": "Active"
    },
    {
        "line_id": "LINE-004",
        "name": "Hoodie Production Line",
        "capacity_per_day": 250,
        "current_utilization": 65,
        "status": "Active"
    }
]

db.production_lines.insert_many(production_lines)

print(f"Inserted {len(production_lines)} production lines.")


# --------------------------------------------------
# 11. PRODUCTION ORDERS
# --------------------------------------------------

production_orders = [
    {
        "production_order_id": "PROD-001",
        "order_id": "ORD-001",
        "sku": "GAR-001",
        "planned_quantity": 10000,
        "completed_quantity": 2500,
        "status": "In Progress",
        "line_id": "LINE-001"
    },
    {
        "production_order_id": "PROD-002",
        "order_id": "ORD-002",
        "sku": "GAR-002",
        "planned_quantity": 6000,
        "completed_quantity": 3000,
        "status": "In Progress",
        "line_id": "LINE-002"
    },
    {
        "production_order_id": "PROD-003",
        "order_id": "ORD-003",
        "sku": "GAR-003",
        "planned_quantity": 4000,
        "completed_quantity": 1000,
        "status": "In Progress",
        "line_id": "LINE-003"
    }
]

db.production_orders.insert_many(production_orders)

print(f"Inserted {len(production_orders)} production orders.")


# --------------------------------------------------
# 12. SHIPMENTS
# --------------------------------------------------

shipments = [
    {
        "shipment_id": "SHIP-001",
        "supplier_id": "SUP-001",
        "material_code": "FAB-001",
        "quantity": 2000,
        "status": "In Transit",
        "eta": datetime.now() + timedelta(days=5)
    },
    {
        "shipment_id": "SHIP-002",
        "supplier_id": "SUP-003",
        "material_code": "FAB-002",
        "quantity": 3000,
        "status": "Delivered",
        "eta": datetime.now() - timedelta(days=2)
    },
    {
        "shipment_id": "SHIP-003",
        "supplier_id": "SUP-004",
        "material_code": "FAB-006",
        "quantity": 1500,
        "status": "In Transit",
        "eta": datetime.now() + timedelta(days=9)
    }
]

db.shipments.insert_many(shipments)

print(f"Inserted {len(shipments)} shipments.")


# --------------------------------------------------
# 13. AGENT ACTIVITY
# --------------------------------------------------

agent_activity = [
    {
        "agent": "Inventory Agent",
        "action": "Low stock detected",
        "material_code": "FAB-001",
        "severity": "Medium",
        "timestamp": datetime.now()
    },
    {
        "agent": "Production Agent",
        "action": "High production utilization detected",
        "line_id": "LINE-003",
        "severity": "High",
        "timestamp": datetime.now()
    }
]

db.agent_activity.insert_many(agent_activity)

print(f"Inserted {len(agent_activity)} agent activity records.")


# --------------------------------------------------
# 14. Finish
# --------------------------------------------------

print("\n----------------------------------")
print("OMNI DATABASE SEEDING COMPLETE!")
print("----------------------------------")
print("Database: OMNI_DB")
print("Synthetic garment data inserted successfully.")

client.close()