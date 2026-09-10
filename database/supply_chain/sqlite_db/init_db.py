import os
import sqlite3
from db import ERP_DB_PATH, TMS_DB_PATH, get_erp_db_connection, get_tms_db_connection

DIR = os.path.dirname(os.path.abspath(__file__))

def init_db(schema_filename, get_conn_func, db_path):
    schema_path = os.path.join(DIR, schema_filename)
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    print(f"Initializing database at: {db_path}")
    
    conn = get_conn_func()
    try:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"Successfully initialized {db_path}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("--- Initializing ERP Database ---")
    init_db("schema_erp.sql", get_erp_db_connection, ERP_DB_PATH)
    
    print("\n--- Initializing TMS Database ---")
    init_db("schema_tms.sql", get_tms_db_connection, TMS_DB_PATH)
