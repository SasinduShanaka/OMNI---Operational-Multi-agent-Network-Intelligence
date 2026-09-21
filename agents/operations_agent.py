import os
import json
import re

from datetime import datetime
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from backend.agent_progress import report_progress

try:
    from groq import Groq
except ImportError:
    Groq = None

from backend.mcp.factory_operations.client import (
    add_inventory_item,
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
    forecast_all_demand,
    forecast_demand,
    get_forecast_products,
    get_all_lines,
    identify_bottlenecks,
    get_production_orders,
    get_production_kpis,
    get_product_materials,
    check_production_feasibility,
)
from agents.forecast_product import resolve_forecast_product

# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(api_key=os.getenv("GROQ_API_KEY")) if Groq and os.getenv("GROQ_API_KEY") else None

MODEL_NAME = "openai/gpt-oss-20b"


INVENTORY_INTENTS = {
    "inventory_list",
    "low_stock",
    "out_of_stock",
    "healthy_stock",
    "material_status",
    "inventory_requirement",
    "reorder_requirements",
    "total_stock",
    "inventory_summary",
    "largest_shortages",
    "inventory_kpis",
    "inventory_add",
    "low_stock_procurement",
}

PRODUCTION_INTENTS = {
    "production_feasibility",
    "production_lines",
    "production_bottleneck",
    "production_status",
    "production_kpis",
    "product_materials",
}


class OperationsState(TypedDict, total=False):
    user_request: str
    decision: dict
    route: Literal["inventory", "forecast", "production", "planning", "low_stock_procurement", "procurement", "unknown"]
    response: dict
    product_name: str | None
    sku: str | None
    required_quantity: float | None
    required_date: str | None
    production: dict
    forecast: dict
    procurement: list[dict]
    inventory: list[dict]
    supply_chain_mode: str
    risks: list[str]


# ============================================================
# 1. UNDERSTAND USER REQUEST
# ============================================================

def _extract_common_entities(user_request: str) -> dict:
    sku_match = re.search(r"\bGAR-\d{3}\b", user_request, re.IGNORECASE)
    material_code_match = re.search(r"\b(?:FAB|THR|BTN|LBL|PKG|MAT)-\d{3}\b", user_request, re.IGNORECASE)
    quantity_match = re.search(r"(\d[\d,]*(?:\.\d+)?)", user_request)

    return {
        "material_name": None,
        "material_code": material_code_match.group().upper() if material_code_match else None,
        "product_name": None,
        "sku": sku_match.group().upper() if sku_match else None,
        "required_quantity": float(quantity_match.group(1).replace(",", "")) if quantity_match else None,
        "required_date": _extract_date(user_request),
    }


def _clean_material_name(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = re.sub(
        r"\b(to|into|in|the|this|that|these|those|inventory|stock|material|materials|with|reorder|level|threshold|minimum|current|on hand)\b",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d[\d,]*(?:\.\d+)?\b", " ", cleaned)
    cleaned = re.sub(r"\b(meters?|yards?|pieces?|pcs|spools?|rolls?|kgs?|kilograms?|units?)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,.")

    return cleaned.title() if cleaned else None


def _extract_inventory_add_entities(user_request: str, entities: dict) -> dict:
    text = user_request.lower()
    extracted = {}

    unit_match = re.search(
        r"\b(meters?|yards?|pieces?|pcs|spools?|rolls?|kgs?|kilograms?|units?)\b",
        text,
    )
    if unit_match:
        unit = unit_match.group(1)
        extracted["unit"] = "pieces" if unit == "pcs" else unit

    reorder_match = re.search(
        r"(?:reorder(?:\s+level|\s+point)?|threshold|minimum|min)\s*(?:is|=|to|at|of)?\s*(\d[\d,]*(?:\.\d+)?)",
        text,
    )
    if reorder_match:
        extracted["reorder_level"] = float(reorder_match.group(1).replace(",", ""))

    numbers = [
        float(match.group(1).replace(",", ""))
        for match in re.finditer(r"(\d[\d,]*(?:\.\d+)?)", user_request)
    ]
    if numbers:
        extracted["current_stock"] = numbers[0]

    code_match = re.search(r"\b(?:FAB|THR|BTN|LBL|PKG|MAT)-\d{3}\b", user_request, re.IGNORECASE)
    if code_match:
        extracted["material_code"] = code_match.group().upper()

    class_match = re.search(r"\bclass(?:ification)?\s*([ABC])\b", user_request, re.IGNORECASE)
    if class_match:
        extracted["classification"] = class_match.group(1).upper()

    name_patterns = [
        r"(?:add|register|create)\s+(?:new\s+)?(?:material\s+)?(?:\d[\d,]*(?:\.\d+)?\s+\w+\s+(?:of\s+)?)?(.+?)(?:\s+(?:to|into|in)\s+(?:the\s+)?(?:inventory|stock)|\s+with\s+|\s+reorder|\s+threshold|\s+minimum|$)",
        r"(?:put|enter)\s+(?:\d[\d,]*(?:\.\d+)?\s+\w+\s+(?:of\s+)?)?(.+?)(?:\s+(?:to|into|in)\s+(?:the\s+)?(?:inventory|stock)|\s+with\s+|\s+reorder|\s+threshold|\s+minimum|$)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, user_request, re.IGNORECASE)
        if match:
            name = _clean_material_name(match.group(1))
            if name:
                extracted["material_name"] = name
                break

    if not extracted.get("material_name") and entities.get("material_name"):
        extracted["material_name"] = entities["material_name"]

    return {**entities, **extracted}


def _has_any_word(text: str, words: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in words
    )


def _extract_date(user_request: str) -> str | None:
    from calendar import monthrange
    from datetime import timedelta

    text = user_request.lower()
    today = datetime.now().date()

    if "month end" in text or "end of month" in text:
        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=last_day).isoformat()

    if "next month" in text:
        month = today.month + 1
        year = today.year
        if month == 13:
            month = 1
            year += 1
        day = min(today.day, monthrange(year, month)[1])
        return today.replace(year=year, month=month, day=day).isoformat()

    week_match = re.search(r"in\s+(\d+)\s+weeks?", text)
    if week_match:
        return (today + timedelta(days=int(week_match.group(1)) * 7)).isoformat()

    day_match = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", text)
    if day_match:
        return (today + timedelta(days=int(day_match.group(1)))).isoformat()

    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)

    return None


def _heuristic_understand_request(user_request: str) -> dict:
    text = user_request.lower()
    entities = _extract_common_entities(user_request)

    material_names = {
        "black cotton fabric": "Black Cotton Fabric",
        "white cotton fabric": "White Cotton Fabric",
        "navy cotton fabric": "Navy Cotton Fabric",
        "grey fleece fabric": "Grey Fleece Fabric",
        "gray fleece fabric": "Grey Fleece Fabric",
        "pink rayon fabric": "Pink Rayon Fabric",
        "blue denim fabric": "Blue Denim Fabric",
        "polyester fabric": "Polyester Fabric",
        "black sewing thread": "Black Sewing Thread",
        "white sewing thread": "White Sewing Thread",
        "polo buttons": "Polo Buttons",
        "garment labels": "Garment Labels",
        "garment packaging": "Garment Packaging",
    }

    product_names = {
        "black polo": "Classic Black Polo",
        "black polos": "Classic Black Polo",
        "polo": "Classic Black Polo",
        "t-shirt": "White Cotton T-Shirt",
        "t shirt": "White Cotton T-Shirt",
        "formal shirt": "Navy Formal Shirt",
        "hoodie": "Grey Hoodie",
        "hoodies": "Grey Hoodie",
        "casual top": "Women's Casual Top",
        "denim shirt": "Blue Denim Shirt",
        "sports t-shirt": "Green Sports T-Shirt",
        "cargo pants": "Beige Cargo Pants",
    }

    for needle, value in material_names.items():
        if needle in text:
            entities["material_name"] = value
            break

    for needle, value in product_names.items():
        if needle in text:
            entities["product_name"] = value
            break

    material_request = any(word in text for word in (
        "material",
        "materials",
        "component",
        "components",
        "bom",
        "bill of material",
        "fabric",
        "cotton",
        "cloth",
        "meter",
        "yard",
        "dye",
        "zipper",
        "button",
        "trim",
    ))
    product_material_question = (
        (entities["product_name"] or entities["sku"])
        and material_request
        and any(phrase in text for phrase in (
            "what material",
            "which material",
            "materials use",
            "material use",
            "materials used",
            "material used",
            "bill of material",
            "bom",
            "what do we use",
            "what is the material",
        ))
    )
    low_stock_supply_chain_question = (
        any(phrase in text for phrase in (
            "low stock",
            "low inventory",
            "these low stock",
            "those low stock",
            "reorder level",
            "below reorder",
        ))
        and _has_any_word(text, (
            "order",
            "buy",
            "procure",
            "source",
            "supplier",
            "suppliers",
            "purchase",
            "replenish",
        ))
    )
    inventory_add_question = (
        _has_any_word(text, ("add", "register", "create", "put", "enter"))
        and any(word in text for word in ("inventory", "stock", "material", "fabric", "thread", "button", "label", "packaging"))
        and not _has_any_word(text, ("order", "buy", "procure", "source", "supplier", "purchase"))
    )

    if any(word in text for word in ("forecast", "forcast", "predict", "prediction", "future demand", "demand outlook")):
        intent = "demand_forecast"
    elif inventory_add_question:
        entities = _extract_inventory_add_entities(user_request, entities)
        intent = "inventory_add"
    elif product_material_question:
        intent = "product_materials"
    elif low_stock_supply_chain_question:
        intent = "low_stock_procurement"
    elif _has_any_word(text, ("buy", "order", "source", "procure", "supplier", "purchase")) or ("need" in text and material_request):
        intent = "procurement"
    elif any(word in text for word in ("can we make", "produce", "manufacture", "feasible", "fulfill order", "deliver")):
        intent = "production_feasibility"
    elif any(word in text for word in ("production line", "capacity", "line planning")):
        intent = "production_lines"
    elif any(word in text for word in ("bottleneck", "overloaded", "constrained")):
        intent = "production_bottleneck"
    elif any(word in text for word in ("production kpi", "line utilization", "production performance")):
        intent = "production_kpis"
    elif any(word in text for word in ("production status", "production orders", "progress")):
        intent = "production_status"
    elif any(word in text for word in ("low stock", "below", "running low", "replenishment", "needs attention")):
        intent = "low_stock"
    elif any(word in text for word in ("out of stock", "zero stock", "unavailable")):
        intent = "out_of_stock"
    elif any(word in text for word in ("healthy", "enough stock", "stock ok")) and not entities["required_quantity"]:
        intent = "healthy_stock"
    elif any(word in text for word in ("reorder", "need to buy", "replenish")):
        intent = "reorder_requirements"
    elif any(word in text for word in ("total inventory", "total stock")):
        intent = "total_stock"
    elif any(word in text for word in ("inventory kpi", "inventory performance", "inventory statistics")):
        intent = "inventory_kpis"
    elif any(word in text for word in ("inventory overview", "inventory health", "stock health")):
        intent = "inventory_summary"
    elif "shortage" in text or "shortages" in text:
        intent = "largest_shortages"
    elif entities["material_name"] or entities["material_code"]:
        intent = "inventory_requirement" if entities["required_quantity"] else "material_status"
    elif any(word in text for word in ("inventory", "stock", "materials", "fabric stock")):
        intent = "inventory_list"
    else:
        intent = "unknown"

    return {"intent": intent, **entities}


def understand_request(user_request: str):

    if client is None:
        return _heuristic_understand_request(user_request)

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

12. inventory_add

Use when the user asks to add, create, register, enter or put
a material into inventory or stock.

Examples:
- add 500 meters of Red Cotton Fabric to inventory with reorder level 200
- register new material Black Rib Fabric, current stock 300 meters, reorder 100
- put 1000 pieces of metal buttons into stock

Extract material_name, material_code, current_stock, reorder_level,
unit and classification when available.

13. procurement

Use when the user asks to order, buy, source, or procure materials.
Examples:
- I need 300 meters of organic cotton
- Order 500 zippers from YKK
- We need to buy more dye
- Source some fabric

14. low_stock_procurement

Use when the user asks to source, find suppliers for, buy,
order, procure or replenish low-stock materials.

Examples:
- order the low stock materials
- place an order for low stock materials
- find suppliers for low inventory items
- source the items below reorder level
- replenish materials that are running low

13. production_feasibility

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

14. production_lines

Use when the user asks:
- show me the production lines
- what is our production capacity?
- how many units can we make per day?
- which lines are running?

15. production_bottleneck

Use when the user asks:
- which line is the bottleneck?
- where are we constrained?
- which lines are overloaded?
- what is slowing production down?

16. production_status

Use when the user asks about progress on
manufacturing work already underway.

Examples:
- how is production going?
- what is the progress on ORD-001?
- are the production orders on track?
- which orders are behind schedule?

17. production_kpis

Use when the user asks:
- give me production KPIs
- what is our line utilization?
- production performance
- production statistics

18. demand_forecast

Use when the user asks:

forecast demand
future demand
next month demand
predict sales
estimate demand
demand prediction

19. product_materials

Use when the user asks what materials, components or BOM
are used to make a finished product.

Examples:
- what materials do we use for Classic Black Polo?
- what is the material used in GAR-001?
- show the BOM for black polos
- which components are needed for hoodies?

20. unknown

Use only when the request is clearly unrelated
to inventory, production, procurement, forecasting or operations.

IMPORTANT:

Distinguish MATERIALS from FINISHED PRODUCTS.

Fabric, thread, buttons, labels and packaging are
materials — those are inventory intents, unless the
user is asking to source, buy or order them, which is
procurement.

Polos, t-shirts, shirts, hoodies, tops and trousers
are finished products — those are production intents.

"Do we have enough Black Cotton Fabric for 4000 meters?"
is inventory_requirement.

"Can we make 4000 Black Polos?"
is production_feasibility.

"I need 300 meters of organic cotton"
is procurement.

"Add 300 meters of Organic Cotton Fabric to inventory"
is inventory_add, not procurement.

"Place an order for low stock materials"
is low_stock_procurement.

"What will demand look like next month?"
is demand_forecast.

"What materials do we use for Classic Black Polo?"
is product_materials.

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
- current_stock      (only for inventory_add)
- reorder_level      (only for inventory_add)
- unit               (only for inventory_add, for example meters, pieces, units)
- classification     (only for inventory_add, A/B/C if supplied)

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
    "required_date": null,
    "current_stock": null,
    "reorder_level": null,
    "unit": null,
    "classification": null
}}

Example for "Can we make 10,000 Black Polos by September 30?":

{{
    "intent": "production_feasibility",
    "material_name": null,
    "material_code": null,
    "product_name": "Black Polo",
    "sku": null,
    "required_quantity": 10000,
    "required_date": "{example_date}",
    "current_stock": null,
    "reorder_level": null,
    "unit": null,
    "classification": null
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
            "required_date": result.get("required_date"),
            "current_stock": result.get("current_stock"),
            "reorder_level": result.get("reorder_level"),
            "unit": result.get("unit"),
            "classification": result.get("classification")
        }

    except json.JSONDecodeError:

        return {
            "intent": "unknown",
            "material_name": None,
            "material_code": None,
            "product_name": None,
            "sku": None,
            "required_quantity": None,
            "required_date": None,
            "current_stock": None,
            "reorder_level": None,
            "unit": None,
            "classification": None
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


def _format_count(value, decimals=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if decimals == 0:
        return f"{number:,.0f}"

    return f"{number:,.{decimals}f}"


def _friendly_status(status):
    labels = {
        "FEASIBLE": "we can do it",
        "AT_RISK": "we can try, but there are risks",
        "INFEASIBLE": "not with the current plan",
        "NOT_FOUND": "I could not find that product",
        "NO_LINE": "there is no production line set up for it",
    }
    return labels.get(str(status).upper(), str(status).replace("_", " ").lower())


def _friendly_date(value):
    if not value:
        return None

    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError):
        return str(value)

    return parsed.strftime("%b %d, %Y")


def _unit_phrase(quantity, unit):
    label = str(unit or "units")

    try:
        number = float(quantity)
    except (TypeError, ValueError):
        return label

    if number == 1 and label.endswith("s"):
        return label[:-1]

    return label


def generate_deterministic_response(user_request, data, source_agent="Inventory Agent"):
    if source_agent == "Forecast Agent":
        if isinstance(data, dict) and data.get("status") == "success":
            return (
                f"I expect around {_format_count(data['forecast'], 2)} units of "
                f"{data['product_name']} ({data['sku']}) for {data['forecast_period']}. "
                f"Demand is trending {data['trend'].lower()}, so I would use this as the planning baseline. "
                f"{data['recommendation']}"
            )
        return data.get("message", "I could not create a reliable forecast from the available demand history.") if isinstance(data, dict) else "I could not create a reliable forecast from the available demand history."

    if source_agent == "Production Agent":
        if isinstance(data, dict) and "status" in data:
            factors = data.get("factors", [])
            factor_text = " ".join(factors[:4])
            return f"My read is: {_friendly_status(data['status'])}. {data.get('message', '')} {factor_text}".strip()
        if isinstance(data, list):
            return f"I found {len(data)} production record(s) for this request."

    if isinstance(data, list):
        if not data:
            return "No matching records were found."
        low = [item for item in data if item.get("status") == "LOW_STOCK"]
        if low:
            return f"I found {len(low)} material(s) that need attention out of {len(data)} inventory record(s)."
        return f"I found {len(data)} inventory material record(s)."

    if isinstance(data, dict):
        if data.get("status") == "SHORTAGE":
            return (
                f"No. {data['material_name']} has {data['available_quantity']:,.0f} {data['unit']} available, "
                f"but {data['required_quantity']:,.0f} {data['unit']} are required. "
                f"The shortage is {data['shortage']:,.0f} {data['unit']}."
            )
        if data.get("status") == "SUFFICIENT":
            return (
                f"Yes. {data['material_name']} has {data['available_quantity']:,.0f} {data['unit']} available, "
                f"which covers the required {data['required_quantity']:,.0f} {data['unit']}."
            )
        if "inventory_health" in data:
            return (
                f"Inventory health is {data['inventory_health'].lower()}. "
                f"{data['healthy_materials']} materials are healthy and {data['low_stock_materials']} are low."
            )
        if "total_stock" in data:
            return f"Total inventory is {data['total_stock']:,.0f} units across {data['material_count']} materials."

    return "The requested agent completed the task and returned data for review."


# ============================================================
# 3. GENERATE HUMAN-FRIENDLY RESPONSE
# ============================================================

def generate_final_response(user_request, inventory_data, source_agent="Inventory Agent"):

    if client is None:
        return generate_deterministic_response(user_request, inventory_data, source_agent)

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

def _execute_specialist_request(user_request: str):

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
    current_stock = decision.get("current_stock")
    reorder_level = decision.get("reorder_level")
    unit = decision.get("unit") or "units"
    classification = decision.get("classification") or "B"

    product_name = decision.get("product_name")
    sku = decision.get("sku")
    required_date = decision.get("required_date")


    # ========================================================
    # ADD OR UPDATE INVENTORY MATERIAL
    # ========================================================

    if intent == "inventory_add":

        if not material_name:

            return {
                "agent": "Operations Agent",
                "task": "Add Inventory Material",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "needs_more_info",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": "Sure, I can add that to inventory. What is the material name?"
            }

        if current_stock is None:

            return {
                "agent": "Operations Agent",
                "task": "Add Inventory Material",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "needs_more_info",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": f"Got it. How much {material_name} should I add to inventory?"
            }

        if reorder_level is None:

            return {
                "agent": "Operations Agent",
                "task": "Add Inventory Material",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "needs_more_info",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": f"I can add {material_name}. What reorder level should I use?"
            }

        try:
            result = add_inventory_item(
                material_name=material_name,
                current_stock=current_stock,
                reorder_level=reorder_level,
                unit=unit,
                material_code=material_code,
                classification=classification,
            )
        except ValueError as error:
            return {
                "agent": "Operations Agent",
                "task": "Add Inventory Material",
                "delegated_to": "Inventory Agent",
                "llm_used": True,
                "intent": intent,
                "status": "invalid_input",
                "workflow": [
                    "Operations Agent",
                    "Inventory Agent"
                ],
                "answer": str(error)
            }

        item = result["item"]
        action_text = "added" if result["action"] == "created" else "updated"
        status_text = item["status"].replace("_", " ").lower()

        return {
            "agent": "Operations Agent",
            "task": "Add Inventory Material",
            "delegated_to": "Inventory Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Inventory Agent"
            ],
            "answer": (
                f"Done. I {action_text} {item['material_name']} ({item['material_code']}) "
                f"with {_format_count(item['current_stock'])} {item['unit']} on hand and a reorder level of "
                f"{_format_count(item['reorder_level'])} {item['unit']}. It is currently {status_text}."
            ),
            "result": item
        }


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

        try:
            products = [] if re.search(r'\bGAR-\d{3}\b', user_request, re.IGNORECASE) else get_forecast_products()
            selection = resolve_forecast_product(user_request, products)
        except Exception:
            selection = {"status": "unavailable", "message": "I could not load the forecast product catalog. Please check the demand data connection and try again."}

        if selection["status"] not in {"matched", "all"}:
            return {
                "agent": "Operations Agent", "delegated_to": "Forecast Agent",
                "intent": intent, "status": "error" if selection["status"] == "unavailable" else "needs_information",
                "workflow": ["Operations Agent", "Forecast Agent"],
                "answer": selection["message"],
                "forecast_periods": selection.get("periods", 1),
                "forecast_mode": selection.get("mode", "forecast"),
                "suggested_products": [
                    {"sku": product["sku"], "product_name": product.get("product_name") or product["sku"]}
                    for product in selection.get("products", [])
                ],
            }

        if selection.get("mode") == "comparison":
            from agents.forecast_comparison import compare_last_month
            try:
                comparisons = compare_last_month([selection["sku"]] if selection["status"] == "matched" else [p["sku"] for p in products])
            except Exception:
                return {"intent": intent, "status": "error", "answer": "Unable to load actual demand or saved forecasts. Check the database connection and try again."}
            completed = sum(row['status'] == 'success' for row in comparisons)
            return {"intent": intent, "status": "success" if completed and completed == len(comparisons) else "partial",
                    "delegated_to": "Forecast Agent", "answer": f"Last completed calendar month (UTC): comparison available for {completed} of {len(comparisons)} products. Saved forecasts are used first; otherwise, labeled historical backtests use only earlier demand. Unavailable values are shown as N/A.",
                    "comparisons": comparisons}

        if selection["status"] == "all":
            forecasts = forecast_all_demand(periods=selection.get("periods", 1))

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

        forecast = forecast_demand(selection["sku"], periods=selection.get("periods", 1))

        if forecast["status"] == "success":
            accuracy = forecast["accuracy"]
            accuracy_text = (
                f"Backtest accuracy is {accuracy['accuracy_percent']:.2f}%. "
                if accuracy.get("accuracy_percent") is not None
                else "Backtest accuracy is unavailable for this history. "
            )
            final_answer = (
                f"The Demand Forecast Agent predicts {forecast['forecast']:,.2f} units of "
                f"{forecast['product_name']} ({forecast['sku']}) for {forecast['forecast_period']}. "
                f"Demand is {forecast['trend'].lower()} at {forecast['trend_per_period']:+,.2f} units per month. "
                f"The model used {forecast['history_points']} monthly demand records. "
                f"{accuracy_text}"
                f"{forecast['recommendation']}"
            )
            if selection.get("periods", 1) > 1:
                monthly = "; ".join(f"{point['date']}: {point['quantity']:,.2f} units" for point in forecast['predictions'])
                final_answer += f" Requested {selection['periods']}-month outlook: {monthly}. Periods start after the latest recorded demand month."
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
        return {
            "agent": "Operations Agent",
            "task": "Procurement Request",
            "delegated_to": "Supply Chain Agent",
            "llm_used": True,
            "intent": "procurement",
            "status": "init_session",
            "workflow": ["Operations Agent", "Supply Chain Agent"],
            "answer": "Starting procurement gathering session.",
            "user_request": user_request
        }

    # ========================================================
    # PRODUCT MATERIALS / BILL OF MATERIALS
    # ========================================================

    if intent == "product_materials":

        if not sku and not product_name:

            return {
                "agent": "Operations Agent",
                "task": "Product Materials Lookup",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "missing_product",
                "workflow": [
                    "Operations Agent"
                ],
                "answer": "Which product should I check the materials for?"
            }

        quantity = required_quantity or 1

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            quantity = 1

        material_data = get_product_materials(
            sku=sku,
            product_name=product_name,
            quantity=quantity,
        )

        if material_data.get("status") == "NOT_FOUND":
            return {
                "agent": "Operations Agent",
                "task": "Product Materials Lookup",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "not_found",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": "I couldn't find that product in our catalogue. Please check the product name or SKU.",
                "result": material_data,
            }

        if material_data.get("status") == "NO_BOM":
            return {
                "agent": "Operations Agent",
                "task": "Product Materials Lookup",
                "delegated_to": "Production Agent",
                "llm_used": True,
                "intent": intent,
                "status": "no_bom",
                "workflow": [
                    "Operations Agent",
                    "Production Agent"
                ],
                "answer": "I found the product, but there is no bill of materials configured for it yet.",
                "result": material_data,
            }

        material_lines = [
            (
                f"{item.get('material_name') or item.get('material_code')} "
                f"({_format_count(item.get('qty_per_unit'), 2).rstrip('0').rstrip('.')} "
                f"{_unit_phrase(item.get('qty_per_unit'), item.get('unit'))} per unit)"
            )
            for item in material_data.get("materials", [])
        ]
        product_label = f"{material_data['product_name']} ({material_data['sku']})"

        return {
            "agent": "Operations Agent",
            "task": "Product Materials Lookup",
            "delegated_to": "Production Agent",
            "llm_used": True,
            "intent": intent,
            "status": "success",
            "workflow": [
                "Operations Agent",
                "Production Agent",
                "Inventory Agent"
            ],
            "answer": (
                f"Sure. {product_label} is made with "
                + ", ".join(material_lines[:-1])
                + (f", and {material_lines[-1]}" if len(material_lines) > 1 else material_lines[0])
                + ". I also checked inventory for those materials while pulling the BOM."
            ),
            "result": material_data,
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


# ============================================================
# LANGGRAPH OPERATIONS ORCHESTRATOR
# ============================================================

def _route_from_intent(intent: str) -> str:
    if intent == "production_feasibility":
        return "planning"
    if intent == "low_stock_procurement":
        return "low_stock_procurement"
    if intent in INVENTORY_INTENTS:
        return "inventory"
    if intent == "demand_forecast":
        return "forecast"
    if intent in PRODUCTION_INTENTS:
        return "production"
    if intent == "procurement":
        return "procurement"
    return "unknown"


def _node_classify(state: OperationsState) -> OperationsState:
    decision = understand_request(state["user_request"])
    route = _route_from_intent(decision.get("intent", "unknown"))
    return {**state, "decision": decision, "route": route}


def _node_inventory(state: OperationsState) -> OperationsState:
    report_progress("Inventory Agent", "Checking material stock")
    response = _execute_specialist_request(state["user_request"])
    response["graph"] = ["Operations Agent", "Inventory Agent"]
    return {**state, "response": response}


def _node_forecast(state: OperationsState) -> OperationsState:
    report_progress("Forecast Agent", "Checking demand history")
    response = _execute_specialist_request(state["user_request"])
    response["graph"] = ["Operations Agent", "Forecast Agent"]
    return {**state, "response": response}


def _wants_purchase_order(user_request: str) -> bool:
    text = user_request.lower()
    return any(word in text for word in ("order", "buy", "procure", "purchase", "replenish"))


def _node_production(state: OperationsState) -> OperationsState:
    report_progress("Production Agent", "Checking production records")
    response = _execute_specialist_request(state["user_request"])
    response["graph"] = response.get("workflow", ["Operations Agent", "Production Agent"])
    return {**state, "response": response}


def _node_low_stock_inventory(state: OperationsState) -> OperationsState:
    report_progress("Inventory Agent", "Checking low-stock materials")
    low_stock_items = get_low_stock()
    mode = "order" if _wants_purchase_order(state["user_request"]) else "source"

    return {
        **state,
        "inventory": low_stock_items,
        "supply_chain_mode": mode,
    }


def _node_low_stock_supply_chain(state: OperationsState) -> OperationsState:
    report_progress("Supply Chain Agent", "Finding suppliers for material shortages")
    import asyncio

    inventory = state.get("inventory") or []
    mode = state.get("supply_chain_mode", "source")
    supply_chain_results = []

    for item in inventory:
        material_type, requirement_id, unit_cost = _material_type_for_shortage(
            item.get("material_code"),
            item.get("material_name"),
        )
        qty = float(item.get("shortage") or 0)
        if qty <= 0:
            qty = max(float(item.get("reorder_level") or 0), 1.0)

        try:
            if mode == "order":
                from backend.supply_chain.orchestrator import start_pipeline

                run = asyncio.run(start_pipeline(
                    material_type=material_type,
                    requirement_id=requirement_id,
                    qty=qty,
                    total_value=qty * unit_cost,
                    compliance_keywords=["Organic Cotton", "Child-Labor Free"],
                    destination="Colombo, LK",
                    po_details={
                        "material_code": item.get("material_code"),
                        "material_name": item.get("material_name"),
                        "unit": item.get("unit"),
                        "price_basis": "planning_estimate",
                    },
                ))
                supply_chain_results.append({
                    "material": item,
                    "material_type": material_type,
                    "mode": mode,
                    "run": run,
                })
            else:
                from agents.supply_chain.sourcing_agent import run_sourcing_agent

                supplier = asyncio.run(run_sourcing_agent(
                    material_type=material_type,
                    requirement_id=requirement_id,
                    compliance_keywords=["Organic Cotton", "Child-Labor Free"],
                ))
                supply_chain_results.append({
                    "material": item,
                    "material_type": material_type,
                    "mode": mode,
                    "supplier": supplier,
                })
        except Exception as error:
            supply_chain_results.append({
                "material": item,
                "material_type": material_type,
                "mode": mode,
                "error": str(error),
            })

    return {**state, "procurement": supply_chain_results}


def _node_synthesize_low_stock_procurement(state: OperationsState) -> OperationsState:
    report_progress("Operations Agent", "Preparing your results")
    inventory = state.get("inventory") or []
    procurement = state.get("procurement") or []
    mode = state.get("supply_chain_mode", "source")

    if not inventory:
        response = {
            "agent": "Operations Agent",
            "task": "Low Stock Supply Chain Check",
            "delegated_to": "Inventory Agent",
            "llm_used": client is not None,
            "intent": "low_stock_procurement",
            "status": "success",
            "workflow": ["Operations Agent", "Inventory Agent"],
            "answer": "Good news. I checked inventory, and there are no low-stock materials to source or order right now.",
            "results": [],
            "procurement": [],
        }
        response["graph"] = response["workflow"]
        return {**state, "response": response}

    item_summaries = [
        (
            f"{item.get('material_name')} needs {_format_count(item.get('shortage', 0))} "
            f"{_unit_phrase(item.get('shortage', 0), item.get('unit'))}"
        )
        for item in inventory
    ]
    successful = [
        result for result in procurement
        if result.get("supplier") or (result.get("run") or {}).get("supplier")
    ]
    failed = [result for result in procurement if result.get("error")]

    if mode == "order":
        drafted = [
            result for result in procurement
            if (result.get("run") or {}).get("status") == "awaiting_approval"
        ]
        answer = (
            f"I found {len(inventory)} low-stock material(s): "
            f"{'; '.join(item_summaries)}. "
        )
        if drafted:
            answer += (
                f"I asked Supply Chain to source them and drafted {len(drafted)} purchase order(s). "
                "Manual approval is required before anything is finalized. "
                "Please review the PO card(s) below and click Authorize PO if you want me to continue."
            )
        else:
            answer += "I tried to create purchase orders, but none were drafted. Please review the supplier errors below."
    else:
        supplier_summaries = []
        for result in successful:
            item = result.get("material") or {}
            supplier = result.get("supplier") or {}
            supplier_summaries.append(
                f"{item.get('material_name')}: {supplier.get('supplier_name')} "
                f"({supplier.get('country')}, rating {supplier.get('rating')})"
            )
        answer = (
            f"I checked the low-stock materials and found suitable suppliers. "
            f"{'; '.join(supplier_summaries)}."
            if supplier_summaries
            else "I checked the low-stock materials, but I could not find suitable suppliers automatically."
        )

    if failed:
        answer += f" {len(failed)} item(s) need manual review because supplier lookup failed."

    response = {
        "agent": "Operations Agent",
        "task": "Low Stock Supply Chain Coordination",
        "delegated_to": "Supply Chain Agent",
        "llm_used": client is not None,
        "intent": "low_stock_procurement",
        "status": "success",
        "workflow": ["Operations Agent", "Inventory Agent", "Supply Chain Agent"],
        "answer": answer,
        "results": inventory,
        "procurement": procurement,
        "requires_approval": mode == "order" and any((item.get("run") or {}).get("status") == "awaiting_approval" for item in procurement),
    }
    response["graph"] = response["workflow"]
    return {**state, "response": response}


def _node_prepare_plan(state: OperationsState) -> OperationsState:
    decision = state.get("decision") or {}
    quantity = decision.get("required_quantity")
    try:
        quantity = float(quantity) if quantity is not None else None
    except (TypeError, ValueError):
        quantity = None

    return {
        **state,
        "product_name": decision.get("product_name"),
        "sku": decision.get("sku"),
        "required_quantity": quantity,
        "required_date": decision.get("required_date"),
        "risks": [],
        "procurement": [],
    }


def _node_production_evidence(state: OperationsState) -> OperationsState:
    report_progress("Production Agent", "Checking capacity and the deadline")
    if not state.get("sku") and not state.get("product_name"):
        return {
            **state,
            "production": {"status": "MISSING_PRODUCT", "message": "A product or SKU is required."},
            "risks": [*state.get("risks", []), "Missing product details."],
        }

    if not state.get("required_quantity"):
        return {
            **state,
            "production": {"status": "MISSING_QUANTITY", "message": "A required quantity is needed."},
            "risks": [*state.get("risks", []), "Missing order quantity."],
        }

    if not state.get("required_date"):
        return {
            **state,
            "production": {"status": "MISSING_DATE", "message": "A required date is needed."},
            "risks": [*state.get("risks", []), "Missing required-by date."],
        }

    production = check_production_feasibility(
        sku=state.get("sku"),
        product_name=state.get("product_name"),
        quantity=state["required_quantity"],
        required_date=state["required_date"],
    )

    risks = list(state.get("risks", []))
    if production.get("status") != "FEASIBLE":
        risks.append(f"Production verdict is {production.get('status', 'unknown')}.")
    for material in production.get("blocking_materials", []):
        if material.get("status") == "SHORTAGE":
            risks.append(
                f"{material.get('material_name', material.get('material_code'))} short by "
                f"{material.get('shortage', 0):,.0f} {material.get('unit', 'units')}."
            )

    return {
        **state,
        "sku": production.get("sku") or state.get("sku"),
        "product_name": production.get("product_name") or state.get("product_name"),
        "production": production,
        "risks": risks,
    }


def _node_forecast_evidence(state: OperationsState) -> OperationsState:
    report_progress("Forecast Agent", "Checking demand for this product")
    sku = state.get("sku")
    if not sku:
        return {**state, "forecast": {"status": "skipped", "message": "Forecast skipped because SKU could not be resolved."}}

    forecast = forecast_demand(sku, periods=3, save_audit=True)
    risks = list(state.get("risks", []))
    if forecast.get("status") == "success" and forecast.get("trend") == "Increasing":
        risks.append(f"Demand trend for {sku} is increasing.")

    return {**state, "forecast": forecast, "risks": risks}


def _material_type_for_shortage(material_code: str | None, material_name: str | None = None) -> tuple[str, int, float]:
    value = f"{material_code or ''} {material_name or ''}".lower()
    if "dye" in value:
        return "dye_house", 5, 260.0
    if any(token in value for token in ("btn", "button", "zipper", "thr", "thread", "lbl", "label", "pkg", "packaging")):
        return "trim_vendor", 4, 15.0
    return "fabric_mill", 2, 260.0


def _needs_procurement(state: OperationsState) -> str:
    production = state.get("production") or {}
    return "procurement_evidence" if production.get("blocking_materials") else "synthesize_plan"


def _node_procurement_evidence(state: OperationsState) -> OperationsState:
    report_progress("Supply Chain Agent", "Reviewing material shortages")
    import asyncio
    from backend.supply_chain.orchestrator import start_pipeline

    procurement_runs = []
    for material in (state.get("production") or {}).get("blocking_materials", []):
        material_type, requirement_id, unit_cost = _material_type_for_shortage(
            material.get("material_code"),
            material.get("material_name"),
        )
        shortage = float(material.get("shortage") or 0)
        if material.get("status") != "SHORTAGE" or shortage <= 0:
            procurement_runs.append({
                "material_code": material.get("material_code"),
                "material_name": material.get("material_name"),
                "error": "Verify the inventory record and required quantity before drafting an order.",
            })
            continue
        qty = shortage

        try:
            run = asyncio.run(start_pipeline(
                material_type=material_type,
                requirement_id=requirement_id,
                qty=qty,
                total_value=qty * unit_cost,
                compliance_keywords=["Organic Cotton", "Child-Labor Free"],
                destination="Colombo, LK",
                po_details={
                    "material_code": material.get("material_code"),
                    "material_name": material.get("material_name"),
                    "unit": material.get("unit"),
                    "required_date": state.get("required_date"),
                    "price_basis": "planning_estimate",
                },
            ))
            procurement_runs.append({
                "material_code": material.get("material_code"),
                "material_name": material.get("material_name"),
                "shortage": shortage,
                "unit": material.get("unit"),
                "run": run,
            })
        except Exception as error:
            procurement_runs.append({
                "material_code": material.get("material_code"),
                "material_name": material.get("material_name"),
                "shortage": shortage,
                "error": str(error),
            })

    return {**state, "procurement": procurement_runs}


def _node_synthesize_plan(state: OperationsState) -> OperationsState:
    report_progress("Operations Agent", "Combining the evidence and next steps")
    production = state.get("production") or {}
    forecast = state.get("forecast") or {}
    procurement = state.get("procurement") or []
    risks = state.get("risks", [])

    workflow = ["Operations Agent", "Production Agent", "Inventory Agent"]
    if forecast:
        workflow.insert(1, "Forecast Agent")
    if procurement:
        workflow.extend(["Supply Chain Agent", "Sourcing Agent", "Purchasing Agent"])

    status = production.get("status", "unknown")
    product_name = state.get("product_name") or state.get("sku") or "the requested product"
    quantity = state.get("required_quantity") or 0
    required_date = state.get("required_date")
    status_label = _friendly_status(status)
    deadline_text = f" by {_friendly_date(required_date)}" if required_date else ""

    if status == "FEASIBLE":
        answer_parts = [
            f"Yes, we can produce {_format_count(quantity)} units of {product_name}{deadline_text}.",
            "I checked the production plan and the required materials, and nothing critical is blocking it right now.",
        ]
    elif status == "AT_RISK":
        answer_parts = [
            f"We may be able to produce {_format_count(quantity)} units of {product_name}{deadline_text}, but I would not treat it as safe yet.",
            "I found a few constraints that need action before we commit to the order.",
        ]
    elif status == "INFEASIBLE":
        answer_parts = [
            f"With the current setup, we cannot reliably produce {_format_count(quantity)} units of {product_name}{deadline_text}.",
            "The plan needs capacity, timing, or material changes before it is realistic.",
        ]
    else:
        answer_parts = [
            f"I checked the plan for {_format_count(quantity)} units of {product_name}{deadline_text}.",
            production.get("message") or f"My current read is: {status_label}.",
        ]

    if forecast.get("status") == "success":
        answer_parts.append(
            f"Demand is also worth watching: the forecast is about {_format_count(forecast.get('forecast', 0))} units next period, and the trend is {forecast.get('trend', 'unknown').lower()}."
        )

    blocking = production.get("blocking_materials", [])
    if blocking:
        shortage_text = "; ".join(
            (f"{item.get('material_name', item.get('material_code'))} is short by {_format_count(item.get('shortage', 0))} {item.get('unit', 'units')}"
             if item.get("status") == "SHORTAGE"
             else f"{item.get('material_code')} has no inventory record")
            for item in blocking
        )
        answer_parts.append(f"The main material issue is this: {shortage_text}.")

    drafted = [
        item for item in procurement
        if (item.get("run") or {}).get("status") == "awaiting_approval"
        and (item.get("run", {}).get("po") or {}).get("po_id")
    ]
    if drafted:
        answer_parts.append(
            f"I drafted {len(drafted)} purchase order(s). Please review and authorize each order below before it is sent or booked for shipping."
        )
    if blocking and len(drafted) < len(blocking):
        answer_parts.append("Some shortages still need manual review; purchase orders were not drafted for all missing materials.")

    if (production.get("reallocation") or {}).get("options"):
        answer_parts.append("There is also a possible production reallocation, but that should be approved by a manager before changing commitments.")

    response = {
        "agent": "Operations Agent",
        "task": "Operational Multi-Agent Plan",
        "delegated_to": "Multi-Agent Planning Graph",
        "llm_used": client is not None,
        "intent": "operational_plan",
        "status": "success" if status in {"FEASIBLE", "AT_RISK", "INFEASIBLE"} else "needs_more_info",
        "workflow": workflow,
        "answer": " ".join(answer_parts),
        "requires_approval": bool(production.get("requires_approval") or drafted),
        "risks": risks,
        "result": {
            "goal": state.get("user_request"),
            "product_name": product_name,
            "sku": state.get("sku"),
            "required_quantity": quantity,
            "required_date": state.get("required_date"),
            "forecast": forecast,
            "production": production,
            "procurement": procurement,
        },
    }

    response["graph"] = workflow
    return {**state, "response": response}


def _node_procurement(state: OperationsState) -> OperationsState:
    report_progress("Supply Chain Agent", "Reviewing your procurement request")
    try:
        response = _execute_specialist_request(state["user_request"])
    except ImportError as error:
        response = {
            "agent": "Operations Agent",
            "task": "Procurement Request",
            "delegated_to": "Supply Chain Agent",
            "llm_used": client is not None,
            "intent": "procurement",
            "status": "dependency_missing",
            "workflow": ["Operations Agent", "Supply Chain Agent"],
            "answer": (
                "The Operations Agent routed this to the Supply Chain Agent, "
                f"but a required package is missing: {error}. Install the project requirements, "
                "then retry the procurement workflow."
            ),
        }
    response["graph"] = response.get("workflow", [
        "Operations Agent",
        "Supply Chain Agent",
        "Sourcing Agent",
        "Purchasing Agent",
    ])
    return {**state, "response": response}


def _node_unknown(state: OperationsState) -> OperationsState:
    response = _execute_specialist_request(state["user_request"])
    response["graph"] = ["Operations Agent"]
    return {**state, "response": response}


def _select_next_node(state: OperationsState) -> str:
    return state.get("route", "unknown")


def build_operations_graph():
    graph = StateGraph(OperationsState)
    graph.add_node("classify", _node_classify)
    graph.add_node("inventory", _node_inventory)
    graph.add_node("forecast", _node_forecast)
    graph.add_node("production", _node_production)
    graph.add_node("low_stock_inventory", _node_low_stock_inventory)
    graph.add_node("low_stock_supply_chain", _node_low_stock_supply_chain)
    graph.add_node("synthesize_low_stock_procurement", _node_synthesize_low_stock_procurement)
    graph.add_node("prepare_plan", _node_prepare_plan)
    graph.add_node("production_evidence", _node_production_evidence)
    graph.add_node("forecast_evidence", _node_forecast_evidence)
    graph.add_node("procurement_evidence", _node_procurement_evidence)
    graph.add_node("synthesize_plan", _node_synthesize_plan)
    graph.add_node("procurement", _node_procurement)
    graph.add_node("unknown", _node_unknown)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        _select_next_node,
        {
            "inventory": "inventory",
            "forecast": "forecast",
            "production": "production",
            "planning": "prepare_plan",
            "low_stock_procurement": "low_stock_inventory",
            "procurement": "procurement",
            "unknown": "unknown",
        },
    )

    graph.add_edge("low_stock_inventory", "low_stock_supply_chain")
    graph.add_edge("low_stock_supply_chain", "synthesize_low_stock_procurement")
    graph.add_edge("synthesize_low_stock_procurement", END)

    graph.add_edge("prepare_plan", "production_evidence")
    graph.add_edge("production_evidence", "forecast_evidence")
    graph.add_conditional_edges(
        "forecast_evidence",
        _needs_procurement,
        {
            "procurement_evidence": "procurement_evidence",
            "synthesize_plan": "synthesize_plan",
        },
    )
    graph.add_edge("procurement_evidence", "synthesize_plan")
    graph.add_edge("synthesize_plan", END)

    for node in ("inventory", "forecast", "production", "procurement", "unknown"):
        graph.add_edge(node, END)

    return graph.compile()


operations_graph = build_operations_graph()


def process_request(user_request: str):
    """Run the Operations Agent as a LangGraph supervisor over specialist agents."""
    final_state = operations_graph.invoke({"user_request": user_request})
    response = final_state["response"]
    response["llm_used"] = client is not None
    response.setdefault("orchestrator", "LangGraph")
    response.setdefault("decision", final_state.get("decision"))
    return response
