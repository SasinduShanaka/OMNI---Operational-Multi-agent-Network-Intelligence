import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load from backend/.env if needed, though usually run from root
# Let's dynamically find the backend/.env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")
load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Initialize the client synchronously
client = MongoClient(MONGO_URI)

# Expose databases for different modules
erp_db = client["omni_erp"]
wms_db = client["omni_wms"]
tms_db = client["omni_tms"]

def check_connection():
    try:
        # The ping command is cheap and does not require auth.
        client.admin.command('ping')
        print("Successfully connected to MongoDB.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
