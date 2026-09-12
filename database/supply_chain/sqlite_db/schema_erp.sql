CREATE TABLE IF NOT EXISTS production_plan (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    style_name TEXT,
    material_type TEXT,
    material_name TEXT,
    required_qty REAL,
    unit TEXT,
    required_by_date DATE,
    status TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    country TEXT,
    category TEXT,
    lead_time_days INTEGER,
    rating REAL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    requirement_id INTEGER,
    qty REAL,
    total_value REAL,
    order_date DATE,
    expected_delivery_date DATE,
    status TEXT,
    approved_by TEXT,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY(requirement_id) REFERENCES production_plan(requirement_id)
);
