CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT
);

CREATE TABLE IF NOT EXISTS stock_items (
    stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_id INTEGER,
    item_name TEXT,
    item_type TEXT,
    quantity REAL,
    unit TEXT,
    reorder_point REAL,
    last_updated DATE,
    FOREIGN KEY(warehouse_id) REFERENCES warehouses(warehouse_id)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    sku TEXT,
    qty REAL,
    required_date DATE,
    status TEXT
);

CREATE TABLE IF NOT EXISTS carriers (
    carrier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    mode TEXT,
    rate_per_unit REAL
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_type TEXT,
    reference_id INTEGER,
    carrier_id INTEGER,
    mode TEXT,
    origin TEXT,
    destination TEXT,
    status TEXT,
    booked_date DATE,
    eta DATE,
    actual_arrival DATE,
    FOREIGN KEY(carrier_id) REFERENCES carriers(carrier_id)
);
