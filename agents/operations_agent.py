import os
import json
import re

from dotenv import load_dotenv
from groq import Groq

from agents.inventory_agent import (
    get_all_inventory,
    get_low_stock,
    get_out_of_stock,
    get_healthy_stock,
    get_material,
    check_inventory_requirement,
    get_reorder_requirements,
    get_total_stock,
    get_inventory_summary,
    get_largest_shortages,
    get_inventory_kpis,
)
from agents.forecast_agent import forecast_all_demand, forecast_demand

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

Your responsibility is to understand natural-language
questions and determine which inventory operation is required.

The Inventory Agent can perform the following operations:

1. inventory_list

Use when the user asks for:
- all materials
- full stock list
- complete inventory
- materials we have
- everything in inventory
- show inventory
- list stock

2. low_stock

Use when the user asks:
- what is low in stock?
- which materials are below reorder level?
- what needs attention?
- which materials need replenishment?
- what is running low?

3. out_of_stock

Use when the user asks:
- what are we out of?
- which materials have zero stock?
- are we out of anything?
- unavailable materials

4. healthy_stock

Use when the user asks:
- which materials are healthy?
- which materials have enough stock?
- which stock is okay?
- what materials are above reorder level?

5. material_status

Use when the user asks about a specific material.

Examples:
- How much Black Cotton Fabric do we have?
- What is the stock of FAB-001?
- Tell me about Black Cotton Fabric.
- Is Black Cotton Fabric low?

6. inventory_requirement

Use when the user asks whether a specific quantity
can be satisfied.

Examples:
- Do we have enough Black Cotton Fabric for 4000 meters?
- Can we fulfill 5000 meters?
- Is there enough stock for 4000 meters?
- How much more material do we need?

7. reorder_requirements

Use when the user asks:
- what should we reorder?
- what do we need to buy?
- what needs replenishment?
- how much should we reorder?

8. total_stock

Use when the user asks:
- what is our total inventory?
- how much stock do we have in total?
- what is the total stock quantity?

9. inventory_summary

Use when the user asks:
- give me an inventory health check
- how is our inventory?
- is everything okay?
- anything I should worry about?
- give me an inventory overview

10. largest_shortages

Use when the user asks:
- which material has the biggest shortage?
- what are our biggest shortages?
- which shortages are most serious?

11. inventory_kpis

Use when the user asks:
- give me inventory KPIs
- inventory performance
- inventory percentages
- inventory statistics

12. procurement

Use when the user asks to order, buy, source, or procure materials.
Examples:
- I need 300 meters of organic cotton
- Order 500 zippers from YKK
- We need to buy more dye
- Source some fabric

13. unknown

Use only when the request is clearly unrelated
to inventory, operations, or procurement.

13. demand_forecast

Use when the user asks:

forecast demand
future demand
next month demand
predict sales
estimate demand
demand prediction

IMPORTANT:

Understand different ways humans ask the same question.

For example:

"Can you give me the full stock list?"
"Can you tell me the materials we have?"
"Show me our inventory."
"What materials are currently available?"

All of these should become:

inventory_list

Extract the following information when available:

- material_name
- material_code
- required_quantity

If a value is not present, return null.

Return ONLY valid JSON.

Example:

{{
    "intent": "inventory_list",
    "material_name": null,
    "material_code": null,
    "required_quantity": null
}}

User request:

"{user_request}"
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a precise intent classification and entity extraction system."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    # --------------------------------------------------------
    # Remove accidental markdown code fences
    # --------------------------------------------------------

    content = content.replace("```json", "")
    content = content.replace("```", "")
    content = content.strip()

    try:

        result = json.loads(content)

        return {
            "intent": result.get("intent", "unknown"),
            "material_name": result.get("material_name"),
            "material_code": result.get("material_code"),
            "required_quantity": result.get("required_quantity")
        }

    except json.JSONDecodeError:

        return {
            "intent": "unknown",
            "material_name": None,
            "material_code": None,
            "required_quantity": None
        }


# ============================================================
# 2. CLEAN LLM RESPONSE
# ============================================================

def clean_response(text):
    """
    Remove markdown formatting that does not look good
    in the frontend chat interface.
    """

    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")

    # Remove unnecessary leading/trailing whitespace
    text = text.strip()

    return text


# ============================================================
# 3. GENERATE HUMAN-FRIENDLY RESPONSE
# ============================================================

def generate_final_response(user_request, inventory_data):

    prompt = f"""
You are the Operations Agent of OMNI.

The user asked:

"{user_request}"

The Inventory Agent retrieved this REAL data
from MongoDB:

{json.dumps(inventory_data, indent=2)}

Your job is to explain the result naturally to a human.

IMPORTANT RULES:

1. Use ONLY the supplied inventory data.
2. Never invent numbers.
3. Never invent materials.
4. Do not use Markdown.
5. Do not use ** symbols.
6. Do not use bullet points unless they genuinely improve readability.
7. Use simple, natural business language.
8. Be concise but informative.
9. If there are multiple materials, organize the answer clearly.
10. Mention important numbers such as current stock,
    reorder level and shortage when relevant.
11. If there is a problem, clearly explain what needs attention.
12. If everything is fine, clearly say that.
13. Do not mention that you are an AI.
14. Do not mention Groq, MongoDB or internal implementation.

Examples of the desired style:

User:
"How much Black Cotton Fabric do we have?"

Good answer:
"We currently have 3,200 meters of Black Cotton Fabric.
The reorder level is 3,500 meters, so we're 300 meters below
the recommended level."

User:
"Which materials are low in stock?"

Good answer:
"Two materials are currently below their reorder levels:
Grey Fleece Fabric has 1,800 meters, which is 200 meters below
its reorder level, and Black Cotton Fabric has 3,200 meters,
which is 300 meters below its reorder level."

User:
"Do we have enough Black Cotton Fabric for 4,000 meters?"

Good answer:
"No. We currently have 3,200 meters, but 4,000 meters are
required. That leaves a shortage of 800 meters."

Return only the final natural-language answer.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You generate clear, professional and human-friendly operational responses."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return clean_response(
        response.choices[0].message.content
    )


# ============================================================
# 4. PROCESS INVENTORY REQUEST
# ============================================================

def process_request(user_request: str):

    # --------------------------------------------------------
    # Understand the user's request
    # --------------------------------------------------------

    normalized_request = user_request.lower()
    forecast_phrases = (
        "forecast",
        "forcast",
        "fore cast",
        "demand",
        "prediction",
        "predict sales",
        "sales prediction",
        "expected sales",
        "future sales",
    )
    planning_question = (
        re.search(r'\bGAR-\d{3}\b', user_request, re.IGNORECASE)
        and any(phrase in normalized_request for phrase in ("next month", "future", "will we need", "expected units"))
    )

    # Forecast questions have a deterministic route and do not need an LLM
    # classification step before being delegated to the Forecast Agent.
    if any(phrase in normalized_request for phrase in forecast_phrases) or planning_question:
        decision = {
            "intent": "demand_forecast",
            "material_name": None,
            "material_code": None,
            "required_quantity": None,
        }
    else:
        decision = understand_request(user_request)

    intent = decision.get("intent")

    material_name = decision.get("material_name")
    material_code = decision.get("material_code")
    required_quantity = decision.get("required_quantity")


    # ========================================================
    # INVENTORY LIST
    # ========================================================

    if intent == "inventory_list":

        inventory_data = get_all_inventory()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Inventory Overview",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "results": inventory_data
        }


    # ========================================================
    # LOW STOCK
    # ========================================================

    if intent == "low_stock":

        inventory_data = get_low_stock()

        if not inventory_data:

            return {
                "agent": "Operations Agent",
                "task": "Low Stock Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": "Good news — there are currently no materials below their reorder levels.",
                "results": []
            }

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
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "results": inventory_data
        }


    # ========================================================
    # OUT OF STOCK
    # ========================================================

    if intent == "out_of_stock":

        inventory_data = get_out_of_stock()

        if not inventory_data:

            return {
                "agent": "Operations Agent",
                "task": "Out of Stock Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": "There are currently no materials completely out of stock.",
                "results": []
            }

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Out of Stock Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "results": inventory_data
        }


    # ========================================================
    # HEALTHY STOCK
    # ========================================================

    if intent == "healthy_stock":

        inventory_data = get_healthy_stock()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Healthy Inventory Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
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
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "I couldn't find that material in our inventory. "
                    "Please check the material name or code and try again."
                )
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
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # INVENTORY REQUIREMENT
    # ========================================================

    if intent == "inventory_requirement":

        if required_quantity is None:

            return {
                "agent": "Operations Agent",
                "task": "Inventory Requirement Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_quantity",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "Sure — I can check that. "
                    "How much material do you need?"
                )
            }

        try:
            required_quantity = float(required_quantity)

        except (ValueError, TypeError):

            return {
                "agent": "Operations Agent",
                "task": "Inventory Requirement Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "invalid_quantity",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "I couldn't understand the required quantity. "
                    "Please provide the amount you need."
                )
            }

        inventory_data = check_inventory_requirement(
            material_name=material_name,
            material_code=material_code,
            required_quantity=required_quantity
        )

        if inventory_data.get("status") == "NOT_FOUND":

            return {
                "agent": "Operations Agent",
                "task": "Inventory Requirement Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "not_found",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "I couldn't find that material in our inventory."
                ),
                "result": inventory_data
            }

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Inventory Requirement Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # REORDER REQUIREMENTS
    # ========================================================

    if intent == "reorder_requirements":

        inventory_data = get_reorder_requirements()

        if not inventory_data:

            return {
                "agent": "Operations Agent",
                "task": "Reorder Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "Everything looks good. "
                    "There are currently no materials that need replenishment."
                ),
                "results": []
            }

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Reorder Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "results": inventory_data
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
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # INVENTORY SUMMARY
    # ========================================================

    if intent == "inventory_summary":

        inventory_data = get_inventory_summary()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Inventory Health Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "result": inventory_data
        }


    # ========================================================
    # LARGEST SHORTAGES
    # ========================================================

    if intent == "largest_shortages":

        inventory_data = get_largest_shortages()

        if not inventory_data:

            return {
                "agent": "Operations Agent",
                "task": "Shortage Analysis",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": (
                    "There are currently no material shortages."
                ),
                "results": []
            }

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Shortage Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "results": inventory_data
        }


    # ========================================================
    # INVENTORY KPIs
    # ========================================================

    if intent == "inventory_kpis":

        inventory_data = get_inventory_kpis()

        final_answer = generate_final_response(
            user_request,
            inventory_data
        )

        return {
            "agent": "Operations Agent",
            "task": "Inventory KPI Analysis",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "result": inventory_data
        }

    # Demand Forecast
    if intent == "demand_forecast":

        sku_match = re.search(r'\bGAR-\d{3}\b', user_request, re.IGNORECASE)

        if not sku_match:
            forecasts = forecast_all_demand()

            if not forecasts:
                return {
                    "agent": "Operations Agent",
                    "delegated_to": "Forecast Agent",
                    "intent": intent,
                    "status": "no_data",
                    "workflow": ["Operations Agent", "Forecast Agent"],
                    "answer": "The Demand Forecast Agent could not find enough demand history to create a forecast.",
                    "results": [],
                }

            total_forecast = sum(item["forecast"] for item in forecasts)
            increasing = sum(item["trend"] == "Increasing" for item in forecasts)
            decreasing = sum(item["trend"] == "Decreasing" for item in forecasts)
            stable = sum(item["trend"] == "Stable" for item in forecasts)

            return {
                "agent": "Operations Agent",
                "delegated_to": "Forecast Agent",
                "intent": intent,
                "status": "success",
                "workflow": ["Operations Agent", "Forecast Agent"],
                "answer": (
                    f"The Demand Forecast Agent analyzed {len(forecasts)} products and predicts "
                    f"a combined demand of {total_forecast:,.2f} units for the next period. "
                    f"{increasing} product(s) are increasing, {decreasing} are decreasing, "
                    f"and {stable} are stable. The individual product forecasts are shown below."
                ),
                "summary": {
                    "products_forecasted": len(forecasts),
                    "combined_forecast": round(total_forecast, 2),
                    "increasing": increasing,
                    "decreasing": decreasing,
                    "stable": stable,
                },
                "results": forecasts,
            }

        forecast = forecast_demand(sku_match.group())

        if forecast["status"] == "success":
            accuracy = forecast["accuracy"]
            final_answer = (
                f"The Demand Forecast Agent predicts {forecast['forecast']:,.2f} units of "
                f"{forecast['product_name']} ({forecast['sku']}) for {forecast['forecast_period']}. "
                f"Demand is {forecast['trend'].lower()} at {forecast['trend_per_period']:+,.2f} units per month. "
                f"The model used {forecast['history_points']} monthly demand records and achieved "
                f"{accuracy['accuracy_percent']:.2f}% backtest accuracy (MAPE {accuracy['mape_percent']:.2f}%). "
                f"{forecast['recommendation']}"
            )
        else:
            final_answer = forecast["message"]

        return {
            "agent": "Operations Agent",
            "delegated_to": "Forecast Agent",
            "intent": intent,
            "status": forecast["status"],
            "workflow": ["Operations Agent", "Forecast Agent"],
            "answer": final_answer,
            "result": forecast,
        }

    # ========================================================
    # PROCUREMENT
    # ========================================================

    if intent == "procurement":
        import asyncio
        from backend.supply_chain.supervisor import process_chat_message
        from backend.supply_chain.orchestrator import start_pipeline

        decision = process_chat_message(user_request)

        if decision.scenario == "unrelated":
            return {
                "agent": "Operations Agent",
                "task": "Procurement Request",
                "delegated_to": "Supply Chain Agent",
                "llm_used": True,
                "intent": "unknown",
                "status": "success",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": "I can help you source and procure materials. Try: 'I need 400 meters of organic cotton'."
            }

        result = asyncio.run(start_pipeline(
            material_type=decision.material_type,
            requirement_id=decision.requirement_id,
            qty=float(decision.qty),
            total_value=decision.total_value,
            compliance_keywords=["Organic Cotton", "Child-Labor Free"],
            destination="Colombo, LK",
            targeted_supplier=decision.supplier_name,
        ))

        return {
            "agent": "Operations Agent",
            "task": "Procurement Request",
            "delegated_to": "Supply Chain Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Supply Chain Agent"
            ],
            "answer": "I found a compliant supplier and drafted a Purchase Order. Please review and authorize below.",
            "data": result,
            "user_request": user_request
        }

    # ========================================================
    # UNKNOWN
    # ========================================================

    return {
        "agent": "Operations Agent",
        "llm_used": True,
        "intent": "unknown",
        "status": "unable_to_route",
        "workflow": [
            "Operations Agent"
        ],
        "answer": (
            "I can help with inventory and operational questions. "
            "For example, you can ask me about current stock, "
            "low-stock materials, shortages, reorder requirements, "
            "or whether we have enough material for a specific order."
        )
    }
