# Mock Supply Chain Database Schema

This document outlines the simplified schema for the mock ERP, WMS, and TMS databases. Secondary tables (like certifications, RFQs, and event logs) have been omitted to focus on the core flow.

## 1. Mock ERP (Procurement)

### `production_plan`
Tracks what raw materials or items are needed based on production planning.

| Column | Type | Description |
| :--- | :--- | :--- |
| `requirement_id` | `INTEGER` | Primary Key |
| `style_name` | `TEXT` | e.g., "SS26 Denim Jacket" |
| `material_type` | `TEXT` | fabric / trim / dye |
| `material_name` | `TEXT` | e.g., "Cotton Twill 12oz" |
| `required_qty` | `REAL` | Quantity required |
| `unit` | `TEXT` | meters / kg / pieces |
| `required_by_date`| `DATE` | When the material is needed |
| `status` | `TEXT` | open / sourced / closed |

### `suppliers`
Master data for suppliers and vendors.

| Column | Type | Description |
| :--- | :--- | :--- |
| `supplier_id` | `INTEGER` | Primary Key |
| `name` | `TEXT` | Supplier name |
| `country` | `TEXT` | Origin country |
| `category` | `TEXT` | fabric_mill / trim_vendor / dye_house |
| `lead_time_days` | `INTEGER` | Expected lead time |
| `rating` | `REAL` | 0-5 performance rating |

### `purchase_orders`
Records purchase orders sent to suppliers to fulfill production requirements.

| Column | Type | Description |
| :--- | :--- | :--- |
| `po_id` | `INTEGER` | Primary Key |
| `supplier_id` | `INTEGER` | Foreign Key -> `suppliers.supplier_id` |
| `requirement_id` | `INTEGER` | Foreign Key -> `production_plan.requirement_id` |
| `qty` | `REAL` | Quantity ordered |
| `total_value` | `REAL` | Total cost of the PO |
| `order_date` | `DATE` | Date PO was placed |
| `expected_delivery_date` | `DATE` | Expected arrival |
| `status` | `TEXT` | draft / pending_approval / approved / issued / received |
| `approved_by` | `TEXT` | Name of approver (human gate) |

---

## 2. Mock WMS (Warehouse & Inventory)

### `warehouses`
Locations where inventory is stored.

| Column | Type | Description |
| :--- | :--- | :--- |
| `warehouse_id` | `INTEGER` | Primary Key |
| `name` | `TEXT` | e.g., "Main Distribution Center" |
| `type` | `TEXT` | raw_material / finished_goods |

### `stock_items`
Current inventory levels for materials and finished goods.

| Column | Type | Description |
| :--- | :--- | :--- |
| `stock_id` | `INTEGER` | Primary Key |
| `warehouse_id` | `INTEGER` | Foreign Key -> `warehouses.warehouse_id` |
| `item_name` | `TEXT` | Material name or garment SKU |
| `item_type` | `TEXT` | raw_material / finished_good |
| `quantity` | `REAL` | Current on-hand quantity |
| `unit` | `TEXT` | e.g., meters / pieces |
| `reorder_point` | `REAL` | Threshold to trigger reordering |
| `last_updated` | `DATE` | Date of last stock change |

---

## 3. Mock TMS (Freight & Orders)

### `sales_orders`
Customer orders that need to be fulfilled and shipped out.

| Column | Type | Description |
| :--- | :--- | :--- |
| `order_id` | `INTEGER` | Primary Key |
| `customer_name` | `TEXT` | Name of the customer |
| `sku` | `TEXT` | Finished good being sold |
| `qty` | `REAL` | Order quantity |
| `required_date` | `DATE` | Delivery deadline |
| `status` | `TEXT` | open / dispatched / fulfilled |

### `carriers`
Logistics providers for transporting goods.

| Column | Type | Description |
| :--- | :--- | :--- |
| `carrier_id` | `INTEGER` | Primary Key |
| `name` | `TEXT` | Carrier name (e.g., FedEx, Maersk) |
| `mode` | `TEXT` | sea / air / road |
| `rate_per_unit` | `REAL` | Simulated cost basis |

### `shipments`
Tracking of inbound (POs) and outbound (Sales Orders) movements.

| Column | Type | Description |
| :--- | :--- | :--- |
| `shipment_id` | `INTEGER` | Primary Key |
| `reference_type` | `TEXT` | 'po' (inbound) or 'sales_order' (outbound) |
| `reference_id` | `INTEGER` | Links to `po_id` or `order_id` |
| `carrier_id` | `INTEGER` | Foreign Key -> `carriers.carrier_id` |
| `mode` | `TEXT` | Transport mode |
| `origin` | `TEXT` | Origin location |
| `destination` | `TEXT` | Destination location |
| `status` | `TEXT` | booked / in_transit / delayed / delivered |
| `booked_date` | `DATE` | Date shipment was booked |
| `eta` | `DATE` | Estimated time of arrival |
| `actual_arrival`| `DATE` | Actual arrival date |
