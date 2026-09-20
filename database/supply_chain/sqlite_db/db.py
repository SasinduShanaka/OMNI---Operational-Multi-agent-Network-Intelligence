import sqlite3
import os

DIR = os.path.dirname(os.path.abspath(__file__))
ERP_DB_PATH = os.path.join(DIR, "mock-erp.db")
TMS_DB_PATH = os.path.join(DIR, "mock-tms.db")

def _get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def get_erp_db_connection():
    return _get_connection(ERP_DB_PATH)

def get_tms_db_connection():
    return _get_connection(TMS_DB_PATH)

def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None

def _run_schema(conn, schema_filename):
    schema_path = os.path.join(DIR, schema_filename)
    with open(schema_path, "r", encoding="utf-8") as schema_file:
        conn.executescript(schema_file.read())
    conn.commit()

def migrate_erp_schema():
    conn = get_erp_db_connection()
    try:
        for table, column, col_def in [
            ("suppliers", "email", "TEXT"),
            ("suppliers", "price_per_unit", "REAL"),
            ("purchase_orders", "po_details", "TEXT"),
        ]:
            if _table_exists(conn, table):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
    finally:
        conn.close()

def ensure_erp_db_ready():
    conn = get_erp_db_connection()
    try:
        if not _table_exists(conn, "suppliers"):
            _run_schema(conn, "schema_erp.sql")
            conn.close()

            migrate_erp_schema()
            from seed_erp import seed_erp
            seed_erp()
            return

        supplier_count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        conn.close()

        migrate_erp_schema()

        if supplier_count == 0 and os.path.getsize(ERP_DB_PATH) == 0:
            from seed_erp import seed_erp
            seed_erp()
    except Exception:
        conn.close()
        raise

def ensure_tms_db_ready():
    conn = get_tms_db_connection()
    try:
        if not _table_exists(conn, "shipments"):
            _run_schema(conn, "schema_tms.sql")
            conn.close()

            from seed_tms import seed_tms
            seed_tms()
    except Exception:
        conn.close()
        raise
