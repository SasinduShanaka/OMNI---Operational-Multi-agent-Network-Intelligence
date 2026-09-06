import os
import sys

# --------------------------------------------------
# Path setup — import db.py from the same folder
# --------------------------------------------------
DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

from db import get_tms_db_connection


# --------------------------------------------------
# 1. Carriers — 5 rows
# --------------------------------------------------

CARRIERS = [
    ("Maersk Line",           "sea",  2.50),
    ("MSC Shipping",          "sea",  2.20),
    ("FedEx International",   "air", 12.00),
    ("DHL Express",           "air", 14.50),
    ("Lanka Freight Road",    "road",  0.80),
]


# --------------------------------------------------
# 2. Warehouses — 3 rows
# --------------------------------------------------

WAREHOUSES = [
    ("Colombo Main Distribution Center", "raw_material"),
    ("Dhaka Raw Materials Store",        "raw_material"),
    ("Colombo Finished Goods Hub",       "finished_goods"),
]


# --------------------------------------------------
# 3. Stock Items — 6 rows (linked to warehouse_ids)
# NOTE: items 2 and 6 are intentionally below reorder_point
# --------------------------------------------------

STOCK_ITEMS = [
    # (warehouse_id, item_name, item_type, quantity, unit, reorder_point, last_updated)
    (1, "Cotton Twill 12oz",          "raw_material",  120.0, "meters",  50.0, "2026-09-01"),
    (1, "Organic Cotton 180gsm",      "raw_material",   45.0, "meters", 100.0, "2026-09-03"),  # BELOW reorder
    (2, "Fleece 300gsm",              "raw_material",  200.0, "meters",  80.0, "2026-09-05"),
    (2, "Polyester Mesh 140gsm",      "raw_material",   80.0, "meters", 100.0, "2026-09-04"),  # BELOW reorder
    (3, "SS26 Denim Jacket (GAR-011)","finished_good", 350.0, "pieces",  50.0, "2026-09-06"),
    (3, "SS26 Polo Shirt (GAR-012)",  "finished_good",  15.0, "pieces", 100.0, "2026-09-06"),  # BELOW reorder
]


# --------------------------------------------------
# 4. Sales Orders — 4 rows
# --------------------------------------------------

SALES_ORDERS = [
    ("Marks & Spencer UK", "GAR-011", 200.0, "2026-10-30", "open"),
    ("H&M Germany",        "GAR-012", 500.0, "2026-10-15", "open"),
    ("Zara Spain",         "GAR-011", 150.0, "2026-11-10", "open"),
    ("Uniqlo Japan",       "GAR-013", 300.0, "2026-12-01", "dispatched"),
]


# --------------------------------------------------
# 5. Shipments — 3 rows
# --------------------------------------------------

SHIPMENTS = [
    # (reference_type, reference_id, carrier_id, mode, origin, destination, status, booked_date, eta, actual_arrival)
    ("po",          1, 1, "sea",  "Colombo, LK",  "Dhaka, BD",        "in_transit", "2026-09-02", "2026-09-18", None),
    ("po",          2, 3, "air",  "Chennai, IN",  "Colombo, LK",      "booked",     "2026-09-06", "2026-09-11", None),
    ("sales_order", 4, 5, "road", "Colombo, LK",  "Colombo Port, LK", "delivered",  "2026-08-28", "2026-09-01", "2026-09-01"),
]


# --------------------------------------------------
# 6. Seed function
# --------------------------------------------------

def seed_tms():
    conn = get_tms_db_connection()
    cur = conn.cursor()

    # --- Clear existing data (dependency order) ---
    cur.execute("DELETE FROM shipments")
    cur.execute("DELETE FROM sales_orders")
    cur.execute("DELETE FROM stock_items")
    cur.execute("DELETE FROM warehouses")
    cur.execute("DELETE FROM carriers")
    # Reset autoincrement counters
    for table in ["shipments", "sales_orders", "stock_items", "warehouses", "carriers"]:
        cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
    print("Cleared existing TMS data.")

    # --- Carriers ---
    cur.executemany(
        "INSERT INTO carriers (name, mode, rate_per_unit) VALUES (?, ?, ?)",
        CARRIERS
    )
    print(f"Inserted {len(CARRIERS)} carriers.")

    # --- Warehouses ---
    cur.executemany(
        "INSERT INTO warehouses (name, type) VALUES (?, ?)",
        WAREHOUSES
    )
    print(f"Inserted {len(WAREHOUSES)} warehouses.")

    # --- Stock Items ---
    cur.executemany(
        """INSERT INTO stock_items
               (warehouse_id, item_name, item_type, quantity, unit, reorder_point, last_updated)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        STOCK_ITEMS
    )
    print(f"Inserted {len(STOCK_ITEMS)} stock items.")

    # --- Sales Orders ---
    cur.executemany(
        "INSERT INTO sales_orders (customer_name, sku, qty, required_date, status) VALUES (?, ?, ?, ?, ?)",
        SALES_ORDERS
    )
    print(f"Inserted {len(SALES_ORDERS)} sales orders.")

    # --- Shipments ---
    cur.executemany(
        """INSERT INTO shipments
               (reference_type, reference_id, carrier_id, mode, origin, destination,
                status, booked_date, eta, actual_arrival)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        SHIPMENTS
    )
    print(f"Inserted {len(SHIPMENTS)} shipments.")

    conn.commit()
    conn.close()
    print("\nTMS seed complete. mock-tms.db is ready.")


if __name__ == "__main__":
    seed_tms()
