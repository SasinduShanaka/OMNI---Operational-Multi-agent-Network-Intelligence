import os
from dotenv import load_dotenv
from email_service import send_po_email

# Load .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

print("Testing Email SMTP Settings...")
print(f"SMTP HOST: {os.getenv('BREVO_SMTP_HOST')}")
print(f"SMTP USER: {os.getenv('BREVO_SMTP_USER')}")
print(f"SENDER EMAIL: {os.getenv('BREVO_SENDER_EMAIL')}")

fake_po_data = {
    "po_id": 9999,
    "supplier_name": "Test Supplier",
    "country": "LK",
    "material_name": "Test Fabric",
    "color_spec": "Red",
    "qty": 100,
    "unit": "meters",
    "price_per_unit": 260.0,
    "total_value": 26000.0,
    "destination": "Colombo, LK",
}

print("Attempting to send test email to dinujawerake003@gmail.com...")
result = send_po_email(fake_po_data, "dinujawerake003@gmail.com", "This is a test email")
print(f"Result: {result}")
