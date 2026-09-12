import os
import json
import re

from datetime import datetime

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

from agents.production_agent import (
    get_all_lines,
    identify_bottlenecks,
    get_production_orders,
    get_production_kpis,
    check_production_feasibility,
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

    # The model has no clock, so today's date is supplied
    # explicitly to let it resolve deadlines like "by September 30".
    today = datetime.now().strftime("%Y-%m-%d")

    example_date = datetime(datetime.now().year, 9, 30).strftime("%Y-%m-%d")

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

12. production_feasibility

Use when the user asks whether an ORDER can be
manufactured — a finished garment, a quantity and
usually a deadline.

Examples:
- Can we make 10,000 Black Polos by September 30?
- Can we fulfill order ORD-001 on time?
- Are we able to produce 5,000 hoodies in three weeks?
- Is the polo order feasible?
- Can we deliver 4,000 formal shirts by month end?

Extract product_name (or sku), required_quantity
and required_date for this intent.

13. production_lines

Use when the user asks:
- show me the production lines
- what is our production capacity?
- how many units can we make per day?
- which lines are running?

14. production_bottleneck

Use when the user asks:
- which line is the bottleneck?
- where are we constrained?
- which lines are overloaded?
- what is slowing production down?

15. production_status

Use when the user asks about progress on
manufacturing work already underway.

Examples:
- how is production going?
- what is the progress on ORD-001?
- are the production orders on track?
- which orders are behind schedule?

16. production_kpis

Use when the user asks:
- give me production KPIs
- what is our line utilization?
- production performance
- production statistics

17. unknown

Use only when the request is clearly unrelated
to inventory, production or operations.

IMPORTANT:

Distinguish MATERIALS from FINISHED PRODUCTS.

Fabric, thread, buttons, labels and packaging are
materials — those are inventory intents.

Polos, t-shirts, shirts, hoodies, tops and trousers
are finished products — those are production intents.

"Do we have enough Black Cotton Fabric for 4000 meters?"
is inventory_requirement.

"Can we make 4000 Black Polos?"
is production_feasibility.

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

- material_name      (a fabric, thread, button, label or packaging)
- material_code      (for example FAB-001)
- product_name       (a finished garment, for example "Classic Black Polo")
- sku                (for example GAR-001)
- required_quantity  (a number, with no thousands separators)
- required_date      (see the date rule below)

DATE RULE:

Today's date is {today}.

Always return required_date in YYYY-MM-DD format.

Resolve relative and partial dates against today:

- "by September 30"   -> the next 30 September on or after today
- "in three weeks"    -> today plus 21 days
- "by month end"      -> the last day of the current month
- "next month"        -> the same day next month

If no deadline is mentioned, return null.

If a value is not present, return null.

Return ONLY valid JSON.

Example for an inventory question:

{{
    "intent": "inventory_list",
    "material_name": null,
    "material_code": null,
    "product_name": null,
    "sku": null,
    "required_quantity": null,
    "required_date": null
}}

Example for "Can we make 10,000 Black Polos by September 30?":

{{
    "intent": "production_feasibility",
    "material_name": null,
    "material_code": null,
    "product_name": "Black Polo",
    "sku": null,
    "required_quantity": 10000,
    "required_date": "{example_date}"
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
            "product_name": result.get("product_name"),
            "sku": result.get("sku"),
            "required_quantity": result.get("required_quantity"),
            "required_date": result.get("required_date")
        }

    except json.JSONDecodeError:

        return {
            "intent": "unknown",
            "material_name": None,
            "material_code": None,
            "product_name": None,
            "sku": None,
            "required_quantity": None,
            "required_date": None
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

def generate_final_response(user_request, inventory_data, source_agent="Inventory Agent"):

    prompt = f"""
You are the Operations Agent of OMNI.

The user asked:

"{user_request}"

The {source_agent} retrieved this REAL data
from MongoDB:

{json.dumps(inventory_data, indent=2, default=str)}

Your job is to explain the result naturally to a human.

IMPORTANT RULES:

1. Use ONLY the supplied data.
2. Never invent numbers.
3. Never invent materials, products or production lines.
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

User:
"Can we make 10,000 Black Polos by September 30?"

Good answer:
"That order is at risk on two fronts. The Polo Production Line
is already running at 85% utilization, so with the spare capacity
it has we could only build about 1,900 units before the deadline,
leaving us roughly 8,100 short. Materials are also tight: we need
12,000 meters of Black Cotton Fabric but hold 3,200, and we need
30,000 Polo Buttons against 25,000 in stock. Moving some volume to
the T-Shirt and Hoodie lines could recover around 7,000 units, but
that needs approval and the fabric shortfall has to be resolved
before the date can be committed."

When explaining a production answer:

- Lead with whether the order is feasible, at risk or not possible.
- Give the capacity picture and the material picture separately.
- Mention the line by name and its utilization.
- State shortfalls and shortages with their numbers and units.
- If a reallocation is proposed, say it requires approval.

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

    product_name = decision.get("product_name")
    sku = decision.get("sku")
    required_date = decision.get("required_date")


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
    # PRODUCTION FEASIBILITY
    # ========================================================
    #
    # The deepest workflow in OMNI: the Operations Agent delegates
    # to the Production Agent, which in turn queries the Inventory
    # Agent for every material on the bill of materials.

    if intent == "production_feasibility":

        if not sku and not product_name:

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_product",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": (
                    "I can check that. Which product should I assess?"
                )
            }

        if required_quantity is None:

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_quantity",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": (
                    "Sure — how many units do you need?"
                )
            }

        if not required_date:

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_date",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": (
                    "I can check that. By what date do you need them?"
                )
            }

        try:
            required_quantity = float(required_quantity)

        except (ValueError, TypeError):

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "invalid_quantity",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": (
                    "I couldn't understand the quantity. "
                    "Please tell me how many units are required."
                )
            }

        production_data = check_production_feasibility(
            sku=sku,
            product_name=product_name,
            quantity=required_quantity,
            required_date=required_date
        )

        if production_data.get("status") == "NOT_FOUND":

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "not_found",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": (
                    "I couldn't find that product in our catalogue. "
                    "Please check the product name or SKU and try again."
                ),
                "result": production_data
            }

        if production_data.get("status") == "NO_LINE":

            return {
                "agent": "Operations Agent",
                "task": "Production Feasibility Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "no_line",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": (
                    "We don't currently have a production line set up "
                    "to build that product."
                ),
                "result": production_data
            }

        final_answer = generate_final_response(
            user_request,
            production_data,
            source_agent="Production Agent"
        )

        return {
            "agent": "Operations Agent",
            "task": "Production Feasibility Analysis",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent",
                "Inventory Agent"
            ],
            "answer": final_answer,
            "requires_approval": production_data.get("requires_approval", False),
            "factors": production_data.get("factors", []),
            "result": production_data
        }


    # ========================================================
    # PRODUCTION LINES
    # ========================================================

    if intent == "production_lines":

        production_data = get_all_lines()

        final_answer = generate_final_response(
            user_request,
            production_data,
            source_agent="Production Agent"
        )

        return {
            "agent": "Operations Agent",
            "task": "Production Capacity Overview",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent"
            ],
            "answer": final_answer,
            "results": production_data
        }


    # ========================================================
    # PRODUCTION BOTTLENECKS
    # ========================================================

    if intent == "production_bottleneck":

        production_data = identify_bottlenecks()

        if not production_data:

            return {
                "agent": "Operations Agent",
                "task": "Bottleneck Analysis",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": (
                    "No production lines are currently running above "
                    "their utilization threshold."
                ),
                "results": []
            }

        final_answer = generate_final_response(
            user_request,
            production_data,
            source_agent="Production Agent"
        )

        return {
            "agent": "Operations Agent",
            "task": "Bottleneck Analysis",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent"
            ],
            "answer": final_answer,
            "results": production_data
        }


    # ========================================================
    # PRODUCTION STATUS
    # ========================================================

    if intent == "production_status":

        production_data = get_production_orders()

        if not production_data:

            return {
                "agent": "Operations Agent",
                "task": "Production Status",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "success",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": "There are no production orders in the system.",
                "results": []
            }

        final_answer = generate_final_response(
            user_request,
            production_data,
            source_agent="Production Agent"
        )

        return {
            "agent": "Operations Agent",
            "task": "Production Status",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent"
            ],
            "answer": final_answer,
            "results": production_data
        }


    # ========================================================
    # PRODUCTION KPIs
    # ========================================================

    if intent == "production_kpis":

        production_data = get_production_kpis()

        final_answer = generate_final_response(
            user_request,
            production_data,
            source_agent="Production Agent"
        )

        return {
            "agent": "Operations Agent",
            "task": "Production KPI Analysis",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent"
            ],
            "answer": final_answer,
            "result": production_data
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
            "I can help with inventory, production and operational "
            "questions. For example, you can ask me about current stock, "
            "low-stock materials, shortages or reorder requirements — or "
            "about line capacity, bottlenecks, production progress, and "
            "whether we can manufacture an order by a given date."
        )
    }
