from pydantic import BaseModel
from typing import Optional
from datetime import date

# ----------------- WMS / Warehouse & Inventory Models -----------------

class Warehouse(BaseModel):
    warehouse_id: Optional[int] = None
    name: str
    type: str

class StockItem(BaseModel):
    stock_id: Optional[int] = None
    warehouse_id: int
    item_name: str
    item_type: str
    quantity: float
    unit: str
    reorder_point: float
    last_updated: date

class StockMovement(BaseModel):
    movement_id: Optional[int] = None
    stock_id: int
    movement_type: str
    quantity: float
    reference_id: str
    movement_date: date
