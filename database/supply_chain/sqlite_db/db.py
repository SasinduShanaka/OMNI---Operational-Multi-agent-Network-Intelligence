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
