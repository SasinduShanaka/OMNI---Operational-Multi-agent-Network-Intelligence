from datetime import datetime, timedelta

from agents.production_agent import (
    get_all_lines,
    get_line_utilization,
    identify_bottlenecks,
    get_production_orders,
    check_capacity,
    check_production_feasibility,
    get_production_kpis,
)


print("\n===== OMNI PRODUCTION AGENT =====\n")


# ============================================================
# 1. PRODUCTION LINES
# ============================================================

print("--- Production Lines ---\n")

for line in get_all_lines():

    print(f"{line['line_id']} — {line['name']}")
    print(f"  Status: {line['status']}")
    print(f"  Capacity: {line['capacity_per_day']} units/day")
    print(f"  Utilization: {line['current_utilization']}%")
    print(f"  Spare: {line['spare_capacity_per_day']} units/day")
    print(f"  Builds: {', '.join(line['supported_skus'])}")
    print()


# ============================================================
# 2. BOTTLENECKS
# ============================================================

print("--- Bottlenecks ---\n")

bottlenecks = identify_bottlenecks()

if not bottlenecks:
    print("No lines are above the bottleneck threshold.\n")

for line in bottlenecks:
    print(f"{line['line_id']} — {line['name']} at {line['current_utilization']}%")
    print(f"  {line['recommendation']}")
    print()


# ============================================================
# 3. PRODUCTION ORDERS
# ============================================================

print("--- Production Orders ---\n")

for order in get_production_orders():

    print(f"{order['production_order_id']} ({order['order_id']}) — {order['sku']}")
    print(f"  Line: {order['line_id']}")
    print(f"  Progress: {order['completed_quantity']:,} / {order['planned_quantity']:,} "
          f"({order['completion_percentage']}%)")
    print(f"  Status: {order['status']}")
    print()


# ============================================================
# 4. CAPACITY CHECK
# ============================================================

required_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

print("--- Capacity Check: 10,000 x GAR-001 in 30 days ---\n")

capacity = check_capacity(
    sku="GAR-001",
    quantity=10000,
    required_date=required_date
)

print(f"Status: {capacity['status']}")
print(f"Line: {capacity['line_name']} ({capacity['line_id']})")
print(f"Producible: {capacity['producible_quantity']:,} units")
print(f"Shortfall: {capacity['shortfall']:,} units")
print(f"Message: {capacity['message']}")
print()

print("Factors:")

for factor in capacity["factors"]:
    print(f"  - {factor}")

print()


# ============================================================
# 5. FULL FEASIBILITY — AGENT TO AGENT
# ============================================================

print("--- Feasibility: 10,000 Classic Black Polo in 30 days ---\n")

result = check_production_feasibility(
    product_name="Classic Black Polo",
    quantity=10000,
    required_date=required_date
)

print(f"Status: {result['status']}")
print(f"Product: {result['product_name']} ({result['sku']})")
print(f"Workflow: {' -> '.join(result['workflow'])}")
print(f"Requires approval: {result['requires_approval']}")
print(f"Message: {result['message']}")
print()

print("Agent-to-agent messages sent to the Inventory Agent:")
print()

for check in result["materials"]:

    request = check["request"]
    response = check["response"]

    print(f"  {request['message_type']} -> {request['receiver']}")
    print(f"    material: {request['material_code']}")
    print(f"    required: {request['required_quantity']:,}")
    print(f"    reply:    {response['status']}", end="")

    if response.get("shortage"):
        print(f" (short {response['shortage']:,.0f} {response['unit']})")
    else:
        print()

    print()

print("Evidence behind the verdict:")

for factor in result["factors"]:
    print(f"  - {factor}")

print()

if result.get("reallocation"):

    reallocation = result["reallocation"]

    print("Reallocation proposal (requires human approval):")
    print(f"  Shortfall: {reallocation['shortfall']:,} units")
    print(f"  Total absorbable elsewhere: {reallocation['total_absorbable']:,} units")
    print(f"  Fully recoverable: {reallocation['fully_recoverable']}")
    print()

    for option in reallocation["options"]:

        print(f"  {option['line_id']} — {option['line_name']}")
        print(f"    can absorb {option['absorbable_quantity']:,} units "
              f"at {option['current_utilization']}% utilization")
        print(f"    requires retooling: {option['requires_retooling']}")
        print()


# ============================================================
# 6. KPIs
# ============================================================

print("--- Production KPIs ---\n")

kpis = get_production_kpis()

for key, value in kpis.items():
    print(f"  {key}: {value}")

print()
