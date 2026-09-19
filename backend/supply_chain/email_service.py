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


# ──────────────────────────────────────────────────────────────────────────────
# HTML PO Email Template
# ──────────────────────────────────────────────────────────────────────────────

def _build_dimensions_rows(dimensions: dict) -> str:
    """Build HTML table rows for product-specific dimension fields."""
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
          <td style="padding:7px 16px;color:#64748b;font-size:13px;border-bottom:1px solid #f1f5f9;">{label}</td>
          <td style="padding:7px 16px;font-weight:600;font-size:13px;border-bottom:1px solid #f1f5f9;">{value}</td>
        </tr>"""
    return rows


def _build_po_html(po_data: dict) -> str:
    """Generate a professional HTML Purchase Order email."""
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
    dimensions  = po_data.get("dimensions", {})
    if isinstance(dimensions, str):
        try:
            dimensions = json.loads(dimensions)
        except Exception:
            dimensions = {}

    dim_rows = _build_dimensions_rows(dimensions)
    notes_section = f"""
    <tr>
      <td colspan="2" style="padding:12px 16px;background:#fffbeb;border-top:1px solid #fde68a;">
        <span style="color:#92400e;font-size:12px;font-weight:600;">NOTES</span><br>
        <span style="color:#78350f;font-size:13px;">{notes}</span>
      </td>
    </tr>""" if notes else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Purchase Order #{po_id:04d} — OMNI Procurement</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 0;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(15,23,42,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a2430 0%,#2c3e50 100%);padding:28px 32px;">
            <table width="100%"><tr>
              <td>
                <div style="color:#d9a441;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">OMNI Procurement System</div>
                <div style="color:#ffffff;font-size:22px;font-weight:700;">Purchase Order</div>
              </td>
              <td align="right">
                <div style="background:#d9a441;color:#1a2430;font-size:18px;font-weight:800;padding:10px 18px;border-radius:10px;letter-spacing:1px;">
                  #PO-{po_id:04d}
                </div>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- Meta row -->
        <tr>
          <td style="background:#f1f5f9;padding:14px 32px;border-bottom:1px solid #e2e8f0;">
            <table width="100%"><tr>
              <td style="font-size:12px;color:#64748b;">
                <b style="color:#1e293b;">Date:</b> {order_date}
              </td>
              <td align="center" style="font-size:12px;color:#64748b;">
                <b style="color:#1e293b;">Expected Delivery:</b> {delivery}
              </td>
              <td align="right">
                <span style="background:#dcfce7;color:#166534;font-size:11px;font-weight:700;padding:4px 12px;border-radius:20px;border:1px solid #bbf7d0;">✓ AUTHORIZED</span>
              </td>
            </tr></table>
          </td>
        </tr>

        <!-- Supplier & Delivery -->
        <tr>
          <td style="padding:24px 32px 0;">
            <table width="100%" style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
              <tr style="background:#f8fafc;">
                <td style="padding:10px 16px;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #e2e8f0;" width="50%">SUPPLIER</td>
                <td style="padding:10px 16px;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #e2e8f0;border-left:1px solid #e2e8f0;">DELIVER TO</td>
              </tr>
              <tr>
                <td style="padding:14px 16px;vertical-align:top;border-right:1px solid #e2e8f0;">
                  <div style="font-weight:700;font-size:14px;color:#1e293b;">{supplier}</div>
                  <div style="color:#64748b;font-size:13px;margin-top:4px;">{email}</div>
                  <div style="color:#94a3b8;font-size:12px;margin-top:2px;">{country}</div>
                </td>
                <td style="padding:14px 16px;vertical-align:top;">
                  <div style="font-weight:600;font-size:14px;color:#1e293b;">{destination}</div>
                  <div style="color:#64748b;font-size:13px;margin-top:4px;">Authorized by: {approved_by}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Items Table -->
        <tr>
          <td style="padding:24px 32px 0;">
            <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">ORDER ITEMS</div>
            <table width="100%" style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;border-collapse:collapse;">
              <tr style="background:#f8fafc;">
                <td style="padding:10px 16px;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">FIELD</td>
                <td style="padding:10px 16px;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #e2e8f0;">VALUE</td>
              </tr>
              <tr>
                <td style="padding:8px 16px;color:#64748b;font-size:13px;border-bottom:1px solid #f1f5f9;">Material</td>
                <td style="padding:8px 16px;font-weight:600;font-size:13px;border-bottom:1px solid #f1f5f9;">{material}</td>
              </tr>
              <tr style="background:#fafafa;">
                <td style="padding:8px 16px;color:#64748b;font-size:13px;border-bottom:1px solid #f1f5f9;">Colour / Shade</td>
                <td style="padding:8px 16px;font-weight:600;font-size:13px;border-bottom:1px solid #f1f5f9;">{colour}</td>
              </tr>
              {dim_rows}
              <tr>
                <td style="padding:8px 16px;color:#64748b;font-size:13px;border-bottom:1px solid #f1f5f9;">Quantity</td>
                <td style="padding:8px 16px;font-weight:600;font-size:13px;border-bottom:1px solid #f1f5f9;">{qty:,} {unit}</td>
              </tr>
              <tr style="background:#fafafa;">
                <td style="padding:8px 16px;color:#64748b;font-size:13px;border-bottom:1px solid #f1f5f9;">Unit Price</td>
                <td style="padding:8px 16px;font-weight:600;font-size:13px;border-bottom:1px solid #f1f5f9;">LKR {price_per_u:,.2f} / {unit[:-1] if unit.endswith('s') else unit}</td>
              </tr>
              <tr style="background:#fffbf0;">
                <td style="padding:10px 16px;color:#92400e;font-size:13px;font-weight:700;border-bottom:1px solid #f1f5f9;">Total Value</td>
                <td style="padding:10px 16px;font-weight:800;font-size:15px;color:#d9a441;border-bottom:1px solid #f1f5f9;">LKR {total_value:,.2f}</td>
              </tr>
              <tr style="background:#f0fdf4;">
                <td style="padding:8px 16px;color:#166534;font-size:12px;border-bottom:1px solid #f1f5f9;">Compliance</td>
                <td style="padding:8px 16px;font-size:12px;color:#15803d;border-bottom:1px solid #f1f5f9;">✓ {compliance}</td>
              </tr>
              {notes_section}
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:24px 32px 28px;">
            <div style="border-top:1px solid #e2e8f0;padding-top:20px;text-align:center;">
              <div style="font-size:11px;color:#94a3b8;">This Purchase Order was generated by <b style="color:#64748b;">OMNI Procurement System</b>.</div>
              <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Please confirm receipt and expected delivery date by replying to this email.</div>
              <div style="margin-top:12px;font-size:10px;color:#cbd5e1;">© {datetime.today().year} OMNI · Operational Multi-Agent Network Intelligence</div>
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
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
