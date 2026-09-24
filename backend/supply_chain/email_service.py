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
    """Generate a premium, modern HTML Purchase Order email."""
    po_id       = po_data.get("po_id", "—")
    supplier    = po_data.get("supplier_name", "—")
    email       = po_data.get("supplier_email", "—")
    country     = po_data.get("country", "—")
    material    = po_data.get("material_name", "—")
    base_colour = po_data.get("color_base", "")
    shade       = po_data.get("color_spec", "")
    
    empty_vals = ["—", "-", "", None]
    
    # Combine base color and shade intelligently
    if base_colour not in empty_vals and shade not in empty_vals:
        colour_display = f"{shade} (Base: {base_colour})"
    else:
        colour_display = shade if shade not in empty_vals else (base_colour if base_colour not in empty_vals else "—")
        
    # Fallback: Extract color from material_name if missing
    if colour_display in empty_vals and material not in empty_vals:
        known_colors = ["Black", "White", "Navy", "Grey", "Pink", "Blue", "Red", "Green", "Yellow", "Orange", "Purple", "Brown", "Beige", "Organic"]
        for kc in known_colors:
            if kc.lower() in material.lower():
                colour_display = kc
                break
                
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
    notes_html = f"""
    <div style='margin-top:25px; padding: 15px; background-color: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 4px;'>
      <strong style='color: #92400e; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;'>Special Instructions:</strong><br>
      <span style='color: #b45309;'>{notes}</span>
    </div>""" if notes else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Purchase Order #PO-{po_id:04d}</title>
</head>
<body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 40px 20px; line-height: 1.6; -webkit-font-smoothing: antialiased;">
  <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05); border: 1px solid #e5e7eb;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); padding: 40px 30px; color: #ffffff; text-align: left;">
      <div style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
          <h1 style="margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;">OMNI Procurement</h1>
          <p style="margin: 5px 0 0 0; color: #93c5fd; font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 1.5px;">Purchase Order</p>
        </div>
        <div style="text-align: right;">
          <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #ffffff;">#PO-{po_id:04d}</h2>
          <div style="display: inline-block; margin-top: 8px; background-color: rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            Authorized
          </div>
        </div>
      </div>
    </div>
    
    <div style="padding: 40px 30px;">
      <!-- Parties Info -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px; font-size: 14px;">
        <tr>
          <td width="50%" valign="top" style="padding-right: 20px;">
            <h3 style="margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; color: #6b7280; letter-spacing: 1px;">Supplier</h3>
            <p style="margin: 0; color: #111827; font-weight: 600; font-size: 16px;">{supplier}</p>
            <p style="margin: 4px 0 0 0; color: #4b5563;">{email}<br>{country}</p>
          </td>
          <td width="50%" valign="top">
            <h3 style="margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; color: #6b7280; letter-spacing: 1px;">Bill To</h3>
            <p style="margin: 0; color: #111827; font-weight: 600; font-size: 16px;">OMNI Supply Chain</p>
            <p style="margin: 4px 0 0 0; color: #4b5563;">{billing_address}</p>
          </td>
        </tr>
      </table>

      <!-- Dates -->
      <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; border-radius: 8px; padding: 15px 20px; margin-bottom: 35px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box;">
        <tr>
          <td width="33%">
            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px;">Order Date</div>
            <div style="font-weight: 600; color: #0f172a; font-size: 14px;">{order_date}</div>
          </td>
          <td width="33%">
            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px;">Expected Delivery</div>
            <div style="font-weight: 600; color: #0f172a; font-size: 14px;">{delivery}</div>
          </td>
          <td width="34%">
            <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px;">Approved By</div>
            <div style="font-weight: 600; color: #0f172a; font-size: 14px;">{approved_by}</div>
          </td>
        </tr>
      </table>

      <div style="margin-bottom: 20px; font-size: 15px; color: #374151;">
        Dear <strong>{supplier}</strong>,<br>
        Please proceed with the supply of the following materials as per the specifications below.
      </div>
      
      <!-- Items Table -->
      <h3 style="font-size: 18px; margin-bottom: 15px; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">Order Details</h3>
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px; font-size: 14px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; border-collapse: separate; border-spacing: 0;">
        <tr>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; background-color: #f9fafb; font-weight: 600; color: #6b7280; width: 35%;">Material</td>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; border-left: 1px solid #e5e7eb; font-weight: 500; color: #111827;">{material}</td>
        </tr>
        <tr>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; background-color: #f9fafb; font-weight: 600; color: #6b7280;">Colour / Shade</td>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; border-left: 1px solid #e5e7eb; font-weight: 500; color: #111827;">{colour_display}</td>
        </tr>
        {dim_rows.replace('<tr>', '<tr>').replace('<td><strong>', '<td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; background-color: #f9fafb; font-weight: 600; color: #6b7280;">').replace('</strong></td>', '</td>').replace('<td>', '<td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; border-left: 1px solid #e5e7eb; font-weight: 500; color: #111827;">')}
        <tr>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; background-color: #f9fafb; font-weight: 600; color: #6b7280;">Order Quantity</td>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; border-left: 1px solid #e5e7eb; font-weight: 600; color: #2563eb;">{qty:,} {unit}</td>
        </tr>
        <tr>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; background-color: #f9fafb; font-weight: 600; color: #6b7280;">Unit Price</td>
          <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb; border-left: 1px solid #e5e7eb; color: #4b5563;">LKR {price_per_u:,.2f} / {unit[:-1] if unit.endswith('s') else unit}</td>
        </tr>
        <tr>
          <td style="padding: 16px 15px; background-color: #eff6ff; font-weight: 700; color: #1e3a8a; font-size: 16px;">Total Value</td>
          <td style="padding: 16px 15px; border-left: 1px solid #e5e7eb; background-color: #eff6ff; font-weight: 800; color: #1e3a8a; font-size: 16px;">LKR {total_value:,.2f}</td>
        </tr>
      </table>
      
      <!-- Logistics -->
      <h3 style="font-size: 18px; margin-bottom: 15px; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">Delivery & Commercials</h3>
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 10px; font-size: 14px; background-color: #f9fafb; border-radius: 8px; padding: 20px; border: 1px solid #e5e7eb;">
        <tr>
          <td width="50%" style="padding: 20px 20px 10px 20px;">
            <strong style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Deliver To:</strong><br>
            <span style="font-weight: 500; color: #111827;">{destination}</span>
          </td>
          <td width="50%" style="padding: 20px 20px 10px 20px;">
            <strong style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Payment Terms:</strong><br>
            <span style="font-weight: 500; color: #111827;">{payment_terms}</span>
          </td>
        </tr>
        <tr>
          <td width="50%" style="padding: 10px 20px 20px 20px;">
            <strong style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Required Compliance:</strong><br>
            <span style="font-weight: 500; color: #111827;">{compliance}</span>
          </td>
          <td width="50%" style="padding: 10px 20px 20px 20px;">
            <strong style="color: #6b7280; font-size: 12px; text-transform: uppercase;">Incoterms:</strong><br>
            <span style="font-weight: 500; color: #111827;">{incoterms}</span>
          </td>
        </tr>
      </table>
      
      {notes_html}
      
      <div style="margin-top: 40px; font-size: 14px; color: #6b7280; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 20px;">
        <p>This is a digitally generated Purchase Order by the OMNI Supply Chain Multi-Agent Network.</p>
        <p style="margin-top: 5px; font-size: 12px;">&copy; {datetime.today().year} OMNI Corporation. All rights reserved.</p>
      </div>

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
    
    text_body = f"Purchase Order #PO-{po_id:04d}\n\nDear {supplier_name},\nPlease find your purchase order details inside this email. Make sure your email client supports HTML to view the official document.\n\nThank you,\n{sender_name}"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
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
