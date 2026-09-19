import os
import pymongo
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))
MONGO_URI = os.getenv("MONGO_URI")

client = pymongo.MongoClient(MONGO_URI)
db = client["omni_erp"]

suppliers = db.suppliers.find().limit(5)
print("SUPPLIER EMAILS IN DB:")
for s in suppliers:
    print(f"- {s.get('name')}: {s.get('email')}")
