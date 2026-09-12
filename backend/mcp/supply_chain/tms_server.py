import os
import sys
from datetime import date

# --------------------------------------------------
# Path resolution — import db.py from database/sqlite_db
# --------------------------------------------------

DB_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "supply_chain", "sqlite_db")
)
sys.path.insert(0, DB_DIR)

from db import get_tms_db_connection

from fastmcp import FastMCP


# --------------------------------------------------
# Initialize MCP Server
# --------------------------------------------------

mcp = FastMCP("OMNI TMS Server")


# --------------------------------------------------
# Tool 4: get_carriers
# --------------------------------------------------

@mcp.tool()
def get_carriers(mode: str = None) -> list[dict]:
    """
    Retrieve available freight carriers from the TMS database.
    Use this to see shipping options before booking a shipment.

    Args:
        mode: Optional filter for transport mode.
              Accepted values: 'sea', 'air', 'road'.
              If omitted, all carriers are returned.

    Returns:
        A list of carriers with their id, name, mode, and rate per unit.
    """
    conn = get_tms_db_connection()
    try:
        if mode:
            rows = conn.execute(
                "SELECT carrier_id, name, mode, rate_per_unit FROM carriers WHERE mode = ? ORDER BY rate_per_unit ASC",
                (mode,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT carrier_id, name, mode, rate_per_unit FROM carriers ORDER BY mode, rate_per_unit ASC"
            ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# --------------------------------------------------
# Tool 5: book_shipment
# --------------------------------------------------

@mcp.tool()
def book_shipment(
    po_id: int,
    carrier_id: int,
    mode: str,
    origin: str,
    destination: str,
    eta: str
) -> dict:
    """
    Book a shipment for an approved Purchase Order in the TMS database.
    Only call this after a PO has been approved via the ERP server.

    Args:
        po_id:       The approved Purchase Order ID (reference).
        carrier_id:  The chosen carrier's ID (from get_carriers).
        mode:        Transport mode: 'sea', 'air', or 'road'.
        origin:      Origin location (city, country).
        destination: Destination location (city, country).
        eta:         Estimated arrival date in YYYY-MM-DD format.

    Returns:
        The newly created shipment id, status, and ETA.
    """
    conn = get_tms_db_connection()
    try:
        # Validate carrier exists
        carrier = conn.execute(
            "SELECT carrier_id, name FROM carriers WHERE carrier_id = ?",
            (carrier_id,)
        ).fetchone()

        if not carrier:
            return {"error": f"Carrier with id={carrier_id} not found."}

        today = date.today().isoformat()

        cursor = conn.execute(
            """
            INSERT INTO shipments
                (reference_type, reference_id, carrier_id, mode,
                 origin, destination, status, booked_date, eta)
            VALUES ('po', ?, ?, ?, ?, ?, 'booked', ?, ?)
            """,
            (po_id, carrier_id, mode, origin, destination, today, eta)
        )
        conn.commit()
        shipment_id = cursor.lastrowid

        return {
            "shipment_id": shipment_id,
            "po_id": po_id,
            "carrier": carrier["name"],
            "mode": mode,
            "origin": origin,
            "destination": destination,
            "status": "booked",
            "booked_date": today,
            "eta": eta,
            "message": f"Shipment #{shipment_id} booked successfully via {carrier['name']}."
        }

    finally:
        conn.close()


# --------------------------------------------------
# Tool 6: get_shipment_status
# --------------------------------------------------

@mcp.tool()
def get_shipment_status(shipment_id: int) -> dict:
    """
    Retrieve the current tracking status and ETA of a shipment.
    Use this to monitor active shipments for delays or delivery.

    Args:
        shipment_id: The ID of the shipment to track.

    Returns:
        The shipment's current status, ETA, and location details.
    """
    conn = get_tms_db_connection()
    try:
        row = conn.execute(
            """
            SELECT s.shipment_id, s.status, s.eta, s.actual_arrival,
                   s.origin, s.destination, s.mode,
                   c.name AS carrier_name
            FROM shipments s
            JOIN carriers c ON s.carrier_id = c.carrier_id
            WHERE s.shipment_id = ?
            """,
            (shipment_id,)
        ).fetchone()

        if not row:
            return {"error": f"Shipment with id={shipment_id} not found."}

        return dict(row)

    finally:
        conn.close()


# --------------------------------------------------
# Tool 7: update_shipment_status
# --------------------------------------------------

@mcp.tool()
def update_shipment_status(shipment_id: int, new_status: str) -> dict:
    """
    Update the status of an active shipment.
    Use this when a delay is detected (e.g., from a weather alert) or when
    a shipment has been delivered.

    Args:
        shipment_id: The ID of the shipment to update.
        new_status:  The new status string. Valid values:
                     'booked', 'in_transit', 'delayed', 'delivered'.

    Returns:
        Confirmation of the status update.
    """
    valid_statuses = {"booked", "in_transit", "delayed", "delivered"}

    if new_status not in valid_statuses:
        return {
            "error": f"Invalid status '{new_status}'. Must be one of: {valid_statuses}"
        }

    conn = get_tms_db_connection()
    try:
        shipment = conn.execute(
            "SELECT shipment_id, status FROM shipments WHERE shipment_id = ?",
            (shipment_id,)
        ).fetchone()

        if not shipment:
            return {"error": f"Shipment with id={shipment_id} not found."}

        today = date.today().isoformat()

        if new_status == "delivered":
            conn.execute(
                "UPDATE shipments SET status = ?, actual_arrival = ? WHERE shipment_id = ?",
                (new_status, today, shipment_id)
            )
        else:
            conn.execute(
                "UPDATE shipments SET status = ? WHERE shipment_id = ?",
                (new_status, shipment_id)
            )

        conn.commit()

        return {
            "shipment_id": shipment_id,
            "previous_status": shipment["status"],
            "new_status": new_status,
            "actual_arrival": today if new_status == "delivered" else None,
            "message": f"Shipment #{shipment_id} status updated to '{new_status}'."
        }

    finally:
        conn.close()


# --------------------------------------------------
# Run Server
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
