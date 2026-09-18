"""
Production Agent reference data.

This script is ADDITIVE and IDEMPOTENT. It only:

    1. Rebuilds the `bom` collection (owned by the Production Agent).
    2. Adds `supported_skus` and `working_days_per_week` to
       existing `production_lines` documents.

It never deletes or clears any collection owned by another agent,
so it is safe to run against the shared OMNI_DB at any time.

Run:
    python database/seed_production_data.py
"""

import os
import sys

# Run directly as a file (python database/seed_production_data.py),
# so the project root has to be on the path before importing the
# shared connection module.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.connection import db, check_connection


# --------------------------------------------------
# 1. Connect to MongoDB
# --------------------------------------------------

if not check_connection():
    raise SystemExit("Cannot reach MongoDB — aborting seed.")


# --------------------------------------------------
# 2. BILL OF MATERIALS
# --------------------------------------------------
#
# How much of each material is consumed to produce ONE unit
# of a finished garment. This is what lets the Production Agent
# translate "10,000 polo shirts" into a material requirement it
# can send to the Inventory Agent.
#
# Note: the synthetic material master has no beige fabric, so
# GAR-008 (Beige Cargo Pants) is mapped to the cotton base fabric.

bom = [

    # GAR-001 — Classic Black Polo
    {"sku": "GAR-001", "material_code": "FAB-001", "qty_per_unit": 1.2,  "unit": "meters"},
    {"sku": "GAR-001", "material_code": "THR-001", "qty_per_unit": 0.05, "unit": "spools"},
    {"sku": "GAR-001", "material_code": "BTN-001", "qty_per_unit": 3,    "unit": "pieces"},
    {"sku": "GAR-001", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-001", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-002 — White Cotton T-Shirt
    {"sku": "GAR-002", "material_code": "FAB-002", "qty_per_unit": 1.0,  "unit": "meters"},
    {"sku": "GAR-002", "material_code": "THR-002", "qty_per_unit": 0.04, "unit": "spools"},
    {"sku": "GAR-002", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-002", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-003 — Navy Formal Shirt
    {"sku": "GAR-003", "material_code": "FAB-003", "qty_per_unit": 1.6,  "unit": "meters"},
    {"sku": "GAR-003", "material_code": "THR-002", "qty_per_unit": 0.06, "unit": "spools"},
    {"sku": "GAR-003", "material_code": "BTN-001", "qty_per_unit": 8,    "unit": "pieces"},
    {"sku": "GAR-003", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-003", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-004 — Grey Hoodie
    {"sku": "GAR-004", "material_code": "FAB-004", "qty_per_unit": 2.0,  "unit": "meters"},
    {"sku": "GAR-004", "material_code": "THR-001", "qty_per_unit": 0.08, "unit": "spools"},
    {"sku": "GAR-004", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-004", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-005 — Women's Casual Top
    {"sku": "GAR-005", "material_code": "FAB-005", "qty_per_unit": 1.1,  "unit": "meters"},
    {"sku": "GAR-005", "material_code": "THR-002", "qty_per_unit": 0.04, "unit": "spools"},
    {"sku": "GAR-005", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-005", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-006 — Blue Denim Shirt
    {"sku": "GAR-006", "material_code": "FAB-006", "qty_per_unit": 1.8,  "unit": "meters"},
    {"sku": "GAR-006", "material_code": "THR-001", "qty_per_unit": 0.07, "unit": "spools"},
    {"sku": "GAR-006", "material_code": "BTN-001", "qty_per_unit": 6,    "unit": "pieces"},
    {"sku": "GAR-006", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-006", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-007 — Green Sports T-Shirt
    {"sku": "GAR-007", "material_code": "FAB-007", "qty_per_unit": 1.0,  "unit": "meters"},
    {"sku": "GAR-007", "material_code": "THR-002", "qty_per_unit": 0.04, "unit": "spools"},
    {"sku": "GAR-007", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-007", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},

    # GAR-008 — Beige Cargo Pants
    {"sku": "GAR-008", "material_code": "FAB-002", "qty_per_unit": 1.9,  "unit": "meters"},
    {"sku": "GAR-008", "material_code": "THR-002", "qty_per_unit": 0.09, "unit": "spools"},
    {"sku": "GAR-008", "material_code": "BTN-001", "qty_per_unit": 4,    "unit": "pieces"},
    {"sku": "GAR-008", "material_code": "LBL-001", "qty_per_unit": 1,    "unit": "pieces"},
    {"sku": "GAR-008", "material_code": "PKG-001", "qty_per_unit": 1,    "unit": "pieces"},
]

db.bom.delete_many({})

db.bom.insert_many(bom)

print(f"Inserted {len(bom)} bill-of-materials lines.")


# --------------------------------------------------
# 3. PRODUCTION LINE — SKU ROUTING
# --------------------------------------------------
#
# `production_lines` only carried a human-readable name, so the
# Production Agent had no way to decide which line builds which
# product. These fields make that routing explicit.

line_routing = {

    "LINE-001": {
        "supported_skus": ["GAR-001"],
        "working_days_per_week": 6,
    },

    "LINE-002": {
        "supported_skus": ["GAR-002", "GAR-007"],
        "working_days_per_week": 6,
    },

    "LINE-003": {
        "supported_skus": ["GAR-003", "GAR-006"],
        "working_days_per_week": 6,
    },

    "LINE-004": {
        "supported_skus": ["GAR-004", "GAR-005", "GAR-008"],
        "working_days_per_week": 5,
    },
}

updated = 0

for line_id, fields in line_routing.items():

    result = db.production_lines.update_one(
        {"line_id": line_id},
        {"$set": fields}
    )

    updated += result.matched_count

print(f"Updated {updated} production lines with SKU routing.")


# --------------------------------------------------
# 4. Verify every SKU is buildable
# --------------------------------------------------

product_skus = {
    product["sku"]
    for product in db.products.find({}, {"sku": 1})
}

bom_skus = set(db.bom.distinct("sku"))

routed_skus = {
    sku
    for line in db.production_lines.find({}, {"supported_skus": 1})
    for sku in line.get("supported_skus", [])
}

missing_bom = product_skus - bom_skus
missing_line = product_skus - routed_skus

if missing_bom:
    print(f"WARNING: products with no BOM: {sorted(missing_bom)}")

if missing_line:
    print(f"WARNING: products with no production line: {sorted(missing_line)}")

if not missing_bom and not missing_line:
    print(f"All {len(product_skus)} products have a BOM and a production line.")


# --------------------------------------------------
# 5. Finish
# --------------------------------------------------

print("Production reference data seeded successfully.")
