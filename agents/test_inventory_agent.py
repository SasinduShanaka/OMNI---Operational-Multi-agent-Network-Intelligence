from inventory_agent import check_inventory


# Run Inventory Agent
results = check_inventory()


# Display results
print("\n==== OMNI INVENTORY AGENT ====\n")

for item in results:

    print(f"Material: {item['material_name']}")
    print(f"Code: {item['material_code']}")
    print(f"Status: {item['status']}")
    print(f"Current Stock: {item['current_stock']} {item['unit']}")
    print(f"Reorder Level: {item['reorder_level']} {item['unit']}")
    print(f"Shortage: {item['shortage']} {item['unit']}")
    print(f"Recommendation: {item['recommendation']}")

    print("-" * 50)