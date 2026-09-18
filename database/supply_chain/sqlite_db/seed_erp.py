import os
import sys
import sqlite3

# --------------------------------------------------
# Path setup — import db.py from the same folder
# --------------------------------------------------
DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

from db import get_erp_db_connection


# --------------------------------------------------
# 1. Suppliers — 10 rows
# --------------------------------------------------

SUPPLIERS = [
    ("Textiles Lanka",           "Sri Lanka",  "fabric_mill",  21, 4.5),
    ("Cotton World India",       "India",      "fabric_mill",  14, 4.2),
    ("Denim House Turkey",       "Turkey",     "fabric_mill",  30, 3.8),
    ("EcoWeave Bangladesh",      "Bangladesh", "fabric_mill",  18, 4.7),
    ("Fleece Pro Pakistan",      "Pakistan",   "fabric_mill",  25, 4.0),
    ("Zipper King China",        "China",      "trim_vendor",  10, 3.5),
    ("Button & Thread Co.",      "Vietnam",    "trim_vendor",  12, 4.1),
    ("Label Craft India",        "India",      "trim_vendor",   8, 4.4),
    ("ColorDye House Sri Lanka", "Sri Lanka",  "dye_house",     7, 4.8),
    ("DyeTech Bangladesh",       "Bangladesh", "dye_house",     9, 4.3),
]


# --------------------------------------------------
# 2. Production Plan — 6 rows
# --------------------------------------------------

PRODUCTION_PLAN = [
    ("SS26 Denim Jacket",   "fabric", "Cotton Twill 12oz",       500.0,  "meters", "2026-11-01", "open"),
    ("SS26 Polo Shirt",     "fabric", "Organic Cotton 180gsm",   300.0,  "meters", "2026-10-15", "open"),
    ("FW26 Hoodie",         "fabric", "Fleece 300gsm",           200.0,  "meters", "2026-12-01", "open"),
    ("SS26 Denim Jacket",   "trim",   "YKK Zipper 15cm",        1000.0,  "pieces", "2026-11-01", "open"),
    ("SS26 Polo Shirt",     "dye",    "Navy Blue Reactive Dye",   50.0,  "kg",     "2026-10-10", "sourced"),
    ("FW26 Sports T-Shirt", "fabric", "Polyester Mesh 140gsm",   400.0,  "meters", "2026-12-15", "open"),
]


# --------------------------------------------------
# 3. Purchase Orders — 3 rows
# --------------------------------------------------

PURCHASE_ORDERS = [
    # (supplier_id, requirement_id, qty, total_value, order_date, expected_delivery_date, status, approved_by)
    (1, 1,  500.0, 125000.0, "2026-09-01", "2026-09-22", "approved",         "Nimal Perera"),
    (2, 2,  300.0,  78000.0, "2026-09-05", "2026-09-19", "pending_approval",  None),
    (6, 4, 1000.0,  15000.0, "2026-09-06", "2026-09-16", "draft",             None),
]


# --------------------------------------------------
# 4. Seed function
# --------------------------------------------------

def seed_erp():
    conn = get_erp_db_connection()
    cur = conn.cursor()

    # --- Clear existing data (dependency order: POs first, then plans & suppliers) ---
    cur.execute("DELETE FROM purchase_orders")
    cur.execute("DELETE FROM production_plan")
    cur.execute("DELETE FROM suppliers")
    # Reset autoincrement counters so IDs match the plan
    cur.execute("DELETE FROM sqlite_sequence WHERE name='purchase_orders'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='production_plan'")
    cur.execute("DELETE FROM sqlite_sequence WHERE name='suppliers'")
    print("Cleared existing ERP data.")

    # --- Suppliers ---
    cur.executemany(
        """INSERT INTO suppliers (name, country, category, lead_time_days, rating)
           VALUES (?, ?, ?, ?, ?)""",
        SUPPLIERS
    )
    print(f"Inserted {len(SUPPLIERS)} suppliers.")

    # --- Production Plan ---
    cur.executemany(
        """INSERT INTO production_plan
               (style_name, material_type, material_name, required_qty, unit, required_by_date, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        PRODUCTION_PLAN
    )
    print(f"Inserted {len(PRODUCTION_PLAN)} production plan requirements.")

    # --- Purchase Orders ---
    cur.executemany(
        """INSERT INTO purchase_orders
               (supplier_id, requirement_id, qty, total_value, order_date,
                expected_delivery_date, status, approved_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        PURCHASE_ORDERS
    )
    print(f"Inserted {len(PURCHASE_ORDERS)} purchase orders.")

    conn.commit()
    conn.close()
    print("\nERP seed complete. mock-erp.db is ready.")


if __name__ == "__main__":
    seed_erp()
