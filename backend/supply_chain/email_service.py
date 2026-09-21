"""
email_service.py
Brevo SMTP email sender for Purchase Order notifications.
Called automatically when a PO is authorized via the chatbot.
"""

import os
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))


def email_configuration_status():
    required = ("BREVO_SMTP_USER", "BREVO_SMTP_PASS", "BREVO_SENDER_EMAIL")
    missing = [key for key in required if not os.getenv(key, "").strip()
               or os.getenv(key, "").startswith("your_")]
    try:
        port_valid = 1 <= int(os.getenv("BREVO_SMTP_PORT", "587")) <= 65535
    except ValueError:
        port_valid = False
    if missing or not port_valid:
        return {"status": "needs_attention", "message": "Supplier email is not configured. Check SMTP credentials, sender address, and port.",
                "missing_settings": missing}
    return {"status": "configured", "message": "SMTP settings configured. Delivery has not been tested."}


# ──────────────────────────────────────────────────────────────────────────────
# HTML PO Email Template
# ──────────────────────────────────────────────────────────────────────────────

def _build_dimensions_rows(dimensions: dict) -> str:
    """Build HTML table rows for product-specific dimension fields (Formal Style)."""
    if not dimensions:
        return ""
    label_map = {
        "width_inches":   "Fabric Width",
        "gsm":            "GSM / Weight",
        "oz_weight":      "Oz Weight",
        "composition":    "Composition",
        "fusible":        "Fusible",
        "width_mm":       "Width (mm)",
        "stretch_pct":    "Stretch %",
        "length_cm":      "Length (cm)",
        "zipper_type":    "Zipper Type",
        "brand":          "Brand",
        "diameter_mm":    "Diameter (mm)",
        "holes":          "Holes",
        "material":       "Material",
        "thread_count":   "Thread Count",
        "fibre":          "Fibre",
        "size_mm":        "Label Size (mm)",
        "print_type":     "Print Type",
        "fold_type":      "Fold Type",
        "dye_class":      "Dye Class",
        "shade":          "Shade",
        "depth_owf":      "Depth (% owf)",
        "thickness_mm":   "Thickness (mm)",
        "shape":          "Shape",
        "fill_type":      "Fill Type",
        "micron":         "Thickness (micron)",
        "size_cm":        "Size (cm)",
        "inner_dia_mm":   "Inner Diameter (mm)",
        "post_length_mm": "Post Length (mm)",
        "cap_dia_mm":     "Cap Diameter (mm)",
    }
    rows = ""
    for key, value in dimensions.items():
        label = label_map.get(key, key.replace("_", " ").title())
        rows += f"""
      <tr>
        <td><strong>{label}</strong></td>
        <td>{value}</td>
      </tr>"""
    return rows


def _build_po_html(po_data: dict) -> str:
    """Generate a formal business letter HTML Purchase Order email."""
    po_id       = po_data.get("po_id", "—")
    supplier    = po_data.get("supplier_name", "—")
    email       = po_data.get("supplier_email", "—")
    country     = po_data.get("country", "—")
    material    = po_data.get("material_name", "—")
    colour      = po_data.get("color_spec", "—")
    qty         = po_data.get("qty", 0)
    unit        = po_data.get("unit", "units")
    price_per_u = po_data.get("price_per_unit", 0)
    total_value = po_data.get("total_value", 0)
    compliance  = ", ".join(po_data.get("compliance_keywords", [])) or "Standard"
    destination = po_data.get("destination", "—")
    order_date  = po_data.get("order_date", datetime.today().strftime("%Y-%m-%d"))
    delivery    = po_data.get("expected_delivery_date", "—")
    approved_by = po_data.get("approved_by", "Human Manager")
    notes       = po_data.get("notes", "")
    incoterms   = po_data.get("incoterms", "DDP (Delivered Duty Paid)")
    payment_terms = po_data.get("payment_terms", "Net 30 Days")
    billing_address = po_data.get("billing_address", "OMNI Corporate HQ, Colombo, LK")
    
    dimensions  = po_data.get("dimensions", {})
    if isinstance(dimensions, str):
        try:
            dimensions = json.loads(dimensions)
        except Exception:
            dimensions = {}

    dim_rows = _build_dimensions_rows(dimensions)
    notes_html = f"<div style='margin-top:12px; padding-top:12px; border-top:1px solid #e2e8f0;'><strong>Special Notes:</strong><br>{notes}</div>" if notes else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Official Purchase Order #{po_id:04d}</title>
<style>
  body {{ font-family: 'Times New Roman', Times, serif; background-color: #ffffff; color: #111111; margin: 0; padding: 40px; line-height: 1.6; }}
  .container {{ max-width: 750px; margin: 0 auto; background: #ffffff; }}
  .header {{ text-align: center; margin-bottom: 40px; border-bottom: 2px solid #111111; padding-bottom: 20px; }}
  .company-name {{ font-size: 26px; font-weight: bold; font-family: Arial, sans-serif; letter-spacing: 2px; color: #1a2430; }}
  .document-title {{ font-size: 16px; font-weight: normal; margin-top: 10px; font-family: Arial, sans-serif; text-transform: uppercase; color: #555555; }}
  .meta-info {{ width: 100%; margin-bottom: 40px; font-family: Arial, sans-serif; font-size: 14px; color: #333333; }}
  .meta-info td {{ vertical-align: top; }}
  .salutation {{ font-size: 16px; margin-bottom: 20px; }}
  .body-text {{ font-size: 16px; margin-bottom: 30px; text-align: justify; }}
  .items-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-family: Arial, sans-serif; font-size: 14px; }}
  .items-table th, .items-table td {{ border: 1px solid #cccccc; padding: 12px 15px; text-align: left; }}
  .items-table th {{ background-color: #f8fafc; font-weight: bold; color: #333333; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; }}
  .total-row td {{ font-weight: bold; background-color: #f8fafc; font-size: 15px; color: #111111; }}
  .terms-box {{ border: 1px solid #cccccc; padding: 20px; margin-bottom: 40px; font-family: Arial, sans-serif; font-size: 14px; background-color: #fafafa; }}
  .sign-off {{ font-size: 16px; margin-top: 50px; }}
  .signature-line {{ border-bottom: 1px solid #111111; width: 250px; margin-bottom: 5px; margin-top: 40px; }}
  .footer {{ margin-top: 60px; font-size: 11px; text-align: center; color: #888888; font-family: Arial, sans-serif; border-top: 1px solid #eeeeee; padding-top: 15px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="company-name">OMNI PROCUREMENT SYSTEM</div>
      <div class="document-title">Official Purchase Order</div>
    </div>
    
    <table class="meta-info">
      <tr>
        <td width="33%">
          <strong>Supplier:</strong><br>
          {supplier}<br>
          {email}<br>
          {country}
        </td>
        <td width="34%">
          <strong>Bill To:</strong><br>
          OMNI Procurement System<br>
          {billing_address}
        </td>
        <td width="33%" style="text-align: right;">
          <strong>PO Number:</strong> PO-{po_id:04d}<br>
          <strong>Order Date:</strong> {order_date}<br>
          <strong>Status:</strong> <span style="color: #166534; font-weight: bold;">AUTHORIZED</span>
        </td>
      </tr>
    </table>
    
    <div class="salutation">Dear {supplier} Representative,</div>
    
    <div class="body-text">
      This document serves as a formal Purchase Order generated by OMNI Procurement. Please proceed with the supply and delivery of the following materials as per the specifications and commercial terms outlined below.
    </div>
    
    <table class="items-table">
      <tr>
        <th width="40%">Specification</th>
        <th width="60%">Details</th>
      </tr>
      <tr>
        <td><strong>Material Description</strong></td>
        <td>{material}</td>
      </tr>
      <tr>
        <td><strong>Colour / Shade</strong></td>
        <td>{colour}</td>
      </tr>
      {dim_rows}
      <tr>
        <td><strong>Order Quantity</strong></td>
        <td>{qty:,} {unit}</td>
      </tr>
      <tr>
        <td><strong>Unit Price</strong></td>
        <td>LKR {price_per_u:,.2f} / {unit[:-1] if unit.endswith('s') else unit}</td>
      </tr>
      <tr class="total-row">
        <td><strong>Total PO Value</strong></td>
        <td>LKR {total_value:,.2f}</td>
      </tr>
    </table>
    
    <div class="terms-box">
      <div style="font-weight: bold; margin-bottom: 12px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #555555;">Commercial & Delivery Terms</div>
      <table width="100%" style="font-size: 14px; font-family: Arial, sans-serif; line-height: 1.8;">
        <tr>
          <td width="50%"><strong>Deliver To:</strong> {destination}</td>
          <td width="50%"><strong>Payment Terms:</strong> {payment_terms}</td>
        </tr>
        <tr>
          <td><strong>Expected Delivery:</strong> {delivery}</td>
          <td><strong>Incoterms:</strong> {incoterms}</td>
        </tr>
        <tr>
          <td colspan="2"><strong>Required Compliance:</strong> {compliance}</td>
        </tr>
      </table>
      {notes_html}
    </div>
    
    <div class="body-text">
      Please confirm receipt of this Purchase Order and formally acknowledge the expected delivery date by replying to this communication. Should you have any queries regarding these specifications or commercial terms, please do not hesitate to contact us immediately.
    </div>
    
    <div class="sign-off">
      Sincerely,<br>
      <div style="font-family: 'Brush Script MT', 'Lucida Handwriting', cursive; font-size: 28px; color: #1a365d; margin: 15px 0;">{approved_by}</div>
      <strong>{approved_by}</strong><br>
      Authorized Representative<br>
      OMNI Procurement System
    </div>
    
    <div class="footer">
      This is a digitally authorized purchase order generated by OMNI (Operational Multi-Agent Network Intelligence).<br>
      &copy; {datetime.today().year} OMNI Corporation
    </div>
  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# SMTP Sender
# ──────────────────────────────────────────────────────────────────────────────

def send_po_email(po_data: dict, supplier_email: str, notes: str = "") -> dict:
    """
    Send a formatted HTML Purchase Order email via Brevo SMTP.

    Args:
        po_data:        Dict with all PO fields (po_id, supplier_name, material_name, etc.)
        supplier_email: Recipient email address
        notes:          Optional free-text notes to include in the PO body

    Returns:
        dict: { "sent": True, "recipient": email } on success
              { "sent": False, "error": reason }   on failure
    """
    configuration = email_configuration_status()
    if configuration["status"] != "configured":
        return {"sent": False, "error": configuration["message"]}

    smtp_host   = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
    smtp_port   = int(os.getenv("BREVO_SMTP_PORT", "587"))
    smtp_user   = os.getenv("BREVO_SMTP_USER", "")
    smtp_pass   = os.getenv("BREVO_SMTP_PASS", "")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "procurement@omni.com")
    sender_name  = os.getenv("BREVO_SENDER_NAME", "OMNI Procurement")

    # If credentials are placeholders, skip silently
    if not smtp_user or smtp_user == "your_brevo_login@email.com":
        return {
            "sent": False,
            "error": "Brevo SMTP credentials not configured. Add them to backend/.env to enable email sending."
        }

    po_data["notes"] = notes
    html_body = _build_po_html(po_data)
    po_id = po_data.get("po_id", "")
    supplier_name = po_data.get("supplier_name", "Supplier")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Purchase Order #PO-{po_id:04d} — OMNI Procurement"
    msg["From"]    = f"{sender_name} <{sender_email}>"
    msg["To"]      = supplier_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, [supplier_email], msg.as_string())

        print(f"[Email] SUCCESS: PO #{po_id} sent to {supplier_email}")
        return {"sent": True, "recipient": supplier_email}

    except Exception as exc:
        print(f"[Email] ERROR: Failed to send PO #{po_id}: {exc}")
        return {"sent": False, "error": str(exc)}
