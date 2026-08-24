import os
import json

from dotenv import load_dotenv
from groq import Groq

from agents.inventory_agent import (
    get_low_stock,
    get_material,
    get_total_stock,
    check_inventory_requirement
)


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# 1. UNDERSTAND USER REQUEST
# ============================================================

def understand_request(user_request: str):

    prompt = f"""
You are the Operations Agent of OMNI.

Your job is to understand the user's request and decide
what inventory operation is required.

Available operations:

1. low_stock
   User wants materials that are below their reorder level.

2. material_status
   User wants information about a specific material.

3. total_stock
   User wants the total amount of inventory.

4. inventory_requirement
   User wants to know whether a specific quantity of a
   material is available.

5. unknown
   The request is not related to inventory.

User request:

"{user_request}"

Return ONLY valid JSON.

For a low-stock request:

{{
    "intent": "low_stock",
    "material_name": null,
    "material_code": null,
    "required_quantity": null
}}

For a specific material request:

{{
    "intent": "material_status",
    "material_name": "Black Cotton Fabric",
    "material_code": null,
    "required_quantity": null
}}

For a total-stock request:

{{
    "intent": "total_stock",
    "material_name": null,
    "material_code": null,
    "required_quantity": null
}}

For a requirement request:

{{
    "intent": "inventory_requirement",
    "material_name": "Black Cotton Fabric",
    "material_code": null,
    "required_quantity": 4000
}}

For an unknown request:

{{
    "intent": "unknown",
    "material_name": null,
    "material_code": null,
    "required_quantity": null
}}

Important:

- Extract the actual material name when possible.
- Extract the requested quantity when the user provides one.
- required_quantity must be a number.
- Do not invent a quantity.
- Return ONLY JSON.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    try:

        return json.loads(content)

    except json.JSONDecodeError:

        return {
            "intent": "unknown",
            "material_name": None,
            "material_code": None,
            "required_quantity": None
        }


# ============================================================
# 2. GENERATE FINAL RESPONSE
# ============================================================

def generate_final_response(user_request, inventory_data):

    prompt = f"""
You are the Operations Agent of OMNI.

The user asked:

"{user_request}"

The Inventory Agent retrieved the following REAL data
from MongoDB:

{json.dumps(inventory_data, indent=2)}

Answer the user's question using ONLY the supplied data.

Do not invent numbers.

Keep the answer clear and concise.

If the result is an inventory requirement check,
clearly explain:

- material
- available quantity
- required quantity
- shortage if there is one
- whether the requirement can be satisfied

If there is enough stock, clearly say that the requirement
can be satisfied.

If there is not enough stock, clearly state the shortage.

Return only the natural-language answer.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


# ============================================================
# 3. OPERATIONS AGENT
# ============================================================

def process_request(user_request: str):

    # --------------------------------------------------------
    # Ask Groq to understand the request
    # --------------------------------------------------------

    decision = understand_request(user_request)

    intent = decision.get("intent")

    material_name = decision.get("material_name")
    material_code = decision.get("material_code")
    required_quantity = decision.get("required_quantity")


    # ========================================================
    # LOW STOCK
    # ========================================================

    if intent == "low_stock":

        inventory_data = get_low_stock()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Low Stock Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "answer": final_answer,
            "results": inventory_data
        }


    # ========================================================
    # SPECIFIC MATERIAL
    # ========================================================

    if intent == "material_status":

        inventory_data = get_material(
            material_name=material_name,
            material_code=material_code
        )

        if inventory_data is None:

            return {
                "agent": "Operations Agent",
                "task": "Material Status",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "not_found",
                "answer": "I could not find that material in the inventory."
            }

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Material Status",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # TOTAL STOCK
    # ========================================================

    if intent == "total_stock":

        inventory_data = get_total_stock()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Total Inventory Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # INVENTORY REQUIREMENT
    # ========================================================

    if intent == "inventory_requirement":

        # ----------------------------------------------------
        # Check that a quantity was actually provided
        # ----------------------------------------------------

        if required_quantity is None:

            return {
                "agent": "Operations Agent",
                "task": "Inventory Requirement Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_quantity",
                "answer": "Please specify the quantity you require."
            }


        # ----------------------------------------------------
        # Ask Inventory Agent to check requirement
        # ----------------------------------------------------

        inventory_data = check_inventory_requirement(
            material_name=material_name,
            material_code=material_code,
            required_quantity=required_quantity
        )


        # ----------------------------------------------------
        # Material not found
        # ----------------------------------------------------

        if inventory_data.get("status") == "NOT_FOUND":

            return {
                "agent": "Operations Agent",
                "task": "Inventory Requirement Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "not_found",
                "answer": "I could not find that material in the inventory."
            }


        # ----------------------------------------------------
        # Generate natural-language response
        # ----------------------------------------------------

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )


        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "agent": "Operations Agent",
            "task": "Inventory Requirement Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # UNKNOWN REQUEST
    # ========================================================

    return {
        "agent": "Operations Agent",
        "llm_used": True,
        "intent": "unknown",
        "status": "unable_to_route",
        "answer": "I don't currently have a specialized agent that can handle this request."
    }