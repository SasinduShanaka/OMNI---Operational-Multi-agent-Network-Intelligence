from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# ----------------- TMS / Freight & Shipment Models -----------------

class Carrier(BaseModel):
    carrier_id: Optional[int] = None
    name: str
    mode: str
    rate_per_unit: float

class ShipmentEvent(BaseModel):
    event_id: Optional[int] = None
    event_type: str
    event_date: date
    notes: str

class Shipment(BaseModel):
    shipment_id: Optional[int] = None
    reference_type: str
    reference_id: int
    carrier_id: int
    mode: str
    origin: str
    destination: str
    status: str
    booked_date: date
    eta: date
    actual_arrival: Optional[date] = None
    events: List[ShipmentEvent] = Field(default_factory=list)

class SalesOrder(BaseModel):
    order_id: Optional[int] = None
    customer_name: str
    sku: str
    qty: float
    required_date: date
    status: str
