from agents.operations_agent import process_request


request = "Which materials are low in stock?"

result = process_request(request)

print("\n===== OMNI OPERATIONS AGENT =====\n")

print(f"Agent: {result['agent']}")
print(f"Task: {result.get('task')}")
print(f"Delegated To: {result.get('delegated_to')}")
print(f"Status: {result['status']}")

print("\nResults:")

for item in result.get("results", []):

    print(f"\nMaterial: {item['material_name']}")
    print(f"Code: {item['material_code']}")
    print(f"Current Stock: {item['current_stock']} {item['unit']}")
    print(f"Reorder Level: {item['reorder_level']} {item['unit']}")
    print(f"Shortage: {item['shortage']} {item['unit']}")
    print(f"Recommendation: {item['recommendation']}")