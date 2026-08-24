from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# ----------------- ERP / Procurement Models -----------------

class ProductionPlan(BaseModel):
    requirement_id: Optional[int] = None
    style_name: str
    material_type: str
    material_name: str
    required_qty: float
    unit: str
    required_by_date: date
    status: str

class SupplierCertification(BaseModel):
    cert_id: Optional[int] = None
    cert_name: str
    expiry_date: date

class Supplier(BaseModel):
    supplier_id: Optional[int] = None
    name: str
    country: str
    category: str
    lead_time_days: int
    rating: float
    certifications: List[SupplierCertification] = Field(default_factory=list)

class RFQ(BaseModel):
    rfq_id: Optional[int] = None
    requirement_id: int
    created_date: date
    status: str

class Quote(BaseModel):
    quote_id: Optional[int] = None
    rfq_id: int
    supplier_id: int
    unit_price: float
    currency: str
    lead_time_days: int
    min_order_qty: float

class PurchaseOrder(BaseModel):
    po_id: Optional[int] = None
    quote_id: int
    supplier_id: int
    qty: float
    total_value: float
    order_date: date
    expected_delivery_date: date
    status: str
    approved_by: Optional[str] = None

class SupplierPerformance(BaseModel):
    record_id: Optional[int] = None
    supplier_id: int
    po_id: int
    delivered_date: date
    on_time: int
    quality_reject_pct: float
