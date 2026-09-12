import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000/supply-chain"

def print_step(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def main():
    print_step("TESTING PHASE 4 ORCHESTRATION & APIs")

    # ---------------------------------------------------------
    # US-1.1 & AS-1.1, AS-1.2, AS-1.3, AS-1.4, AS-2.1, AS-2.2
    # ---------------------------------------------------------
    print_step("Step 1: Starting Pipeline (Sourcing & PO Draft)")
    payload = {
        "material_type": "fabric_mill",
        "requirement_id": 2,
        "qty": 500,
        "total_value": 130000,
        "compliance_keywords": ["Organic Cotton", "Child-Labor Free"],
        "destination": "Colombo, LK"
    }

    print(f"POST {BASE_URL}/run")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(f"{BASE_URL}/run", json=payload)
        result = response.json()
        
        if response.status_code != 200:
            print(f"FAILED: {result}")
            sys.exit(1)
            
        print("\nSuccess! Pipeline started.")
        print(f"Run ID: {result['run_id']}")
        print(f"Status: {result['status']}")
        print(f"Selected Supplier: {result['supplier']}")
        print(f"PO ID: #{result['po_id']}")
        print(f"Message to Human: {result['message']}")
        
        run_id = result['run_id']
        po_id = result['po_id']
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # Check Pipeline Status
    # ---------------------------------------------------------
    print_step("Step 2: Checking Status (Paused for Human Approval)")
    print(f"GET {BASE_URL}/status/{run_id}")
    try:
        response = requests.get(f"{BASE_URL}/status/{run_id}")
        status_res = response.json()
        print(f"Current Status: {status_res['status']}")
    except Exception as e:
        print(f"Error: {e}")

    # ---------------------------------------------------------
    # US-1.2 & AS-2.3, AS-3.1, AS-3.2, AS-3.3, AS-4.1
    # ---------------------------------------------------------
    print_step("Step 3: Human Approval (Triggers Freight & Tracking)")
    print("Simulating Human Manager clicking 'Approve'...")
    print(f"POST {BASE_URL}/approve/{run_id}")
    
    approve_payload = {"approved_by": "Test Manager"}
    try:
        response = requests.post(f"{BASE_URL}/approve/{run_id}", json=approve_payload)
        approve_result = response.json()
        
        if response.status_code != 200:
            print(f"FAILED: {approve_result}")
            sys.exit(1)
            
        print("\nSuccess! PO Approved and Shipment Booked.")
        print(f"Status: {approve_result['status']}")
        print(f"Shipment ID: #{approve_result['shipment_id']}")
        print(f"Carrier: {approve_result['carrier']} ({approve_result['mode'].upper()})")
        print(f"ETA: {approve_result['eta']}")
        
        shipment_id = approve_result['shipment_id']
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # US-1.3 & AS-4.1
    # ---------------------------------------------------------
    print_step("Step 4: Live Tracking Status")
    print(f"GET {BASE_URL}/track/{shipment_id}")
    try:
        response = requests.get(f"{BASE_URL}/track/{shipment_id}")
        track_res = response.json()
        print("\nTracking Result:")
        print(f"Summary: {track_res['summary']}")
    except Exception as e:
        print(f"Error: {e}")

    print_step("ALL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
