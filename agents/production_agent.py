import re

from datetime import datetime, date

from database.connection import db

from agents.inventory_agent import check_inventory_requirement


# ============================================================
# MONGODB
# ============================================================

production_lines_collection = db["production_lines"]
production_orders_collection = db["production_orders"]
customer_orders_collection = db["customer_orders"]
products_collection = db["products"]
bom_collection = db["bom"]
agent_activity_collection = db["agent_activity"]


# ============================================================
# CONFIGURATION
# ============================================================

# A line at or above this utilization is treated as a bottleneck.
BOTTLENECK_THRESHOLD = 85


# ============================================================
# HELPERS
# ============================================================

def parse_date(value):
    """
    Accept a date, a datetime or an ISO date string and return
    a datetime. Returns None when the value cannot be understood.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    if isinstance(value, str):

        text = value.strip()

        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):

            try:
                return datetime.strptime(text, pattern)

            except ValueError:
                continue

        try:
            return datetime.fromisoformat(text)

        except ValueError:
            return None

    return None


def singular_forms(word):
    """
    Candidate singular spellings of an English plural.

    Returns every plausible form rather than committing to one,
    because the usual rules disagree: "hoodies" becomes "hoody"
    under the -ies rule but "hoodie" under simple -s stripping,
    and only the second matches the catalogue.
    """

    lowered = word.lower()

    forms = {lowered}

    if lowered.endswith("ies") and len(lowered) > 4:
        forms.add(lowered[:-3] + "y")

    if lowered.endswith("es") and len(lowered) > 3:
        forms.add(lowered[:-2])

    # "trousers" and "pants" are plural-only, so the bare word
    # is kept as a candidate too.
    if lowered.endswith("s") and not lowered.endswith("ss") and len(lowered) > 3:
        forms.add(lowered[:-1])

    return forms


# Words that carry no product meaning on their own.
STOP_WORDS = {
    "the", "a", "an", "of", "for", "and", "our", "some",
    "unit", "units", "piece", "pieces", "order", "orders",
}


def resolve_sku(sku=None, product_name=None):
    """
    Find a product SKU from either an explicit code or a
    natural-language product name.

    Users do not speak in catalogue names — they ask for
    "hoodies" or "black polos", not "Grey Hoodie". Matching
    therefore widens in stages, from strictest to loosest.
    """

    if sku:

        product = products_collection.find_one({"sku": sku.upper()})

        if product:
            return product["sku"]

    if not product_name:
        return None

    text = product_name.strip()

    if not text:
        return None

    # --------------------------------------------------------
    # Stage 1 — the phrase as given, against name or category
    # --------------------------------------------------------

    product = products_collection.find_one({
        "$or": [
            {"name": {"$regex": re.escape(text), "$options": "i"}},
            {"category": {"$regex": re.escape(text), "$options": "i"}},
        ]
    })

    if product:
        return product["sku"]

    # --------------------------------------------------------
    # Stage 2 — the phrase singularized ("hoodies" -> "hoodie")
    # --------------------------------------------------------

    for form in singular_forms(text):

        if form == text.lower():
            continue

        product = products_collection.find_one({
            "$or": [
                {"name": {"$regex": re.escape(form), "$options": "i"}},
                {"category": {"$regex": re.escape(form), "$options": "i"}},
            ]
        })

        if product:
            return product["sku"]

    # --------------------------------------------------------
    # Stage 3 — score every product on how many of the user's
    #           words it matches, and take the best
    # --------------------------------------------------------

    word_forms = [
        singular_forms(word)
        for word in re.split(r"[^A-Za-z0-9]+", text)
        if word and word.lower() not in STOP_WORDS
    ]

    if not word_forms:
        return None

    best_product = None
    best_score = 0

    for candidate in products_collection.find():

        haystack = (
            f"{candidate.get('name', '')} "
            f"{candidate.get('category', '')} "
            f"{candidate.get('color', '')} "
            f"{candidate.get('fabric', '')}"
        ).lower()

        score = sum(
            1
            for forms in word_forms
            if any(form in haystack for form in forms)
        )

        if score > best_score:
            best_score = score
            best_product = candidate

    if best_product:
        return best_product["sku"]

    return None


def format_line(line):
    """
    Convert a MongoDB production line document into a clean
    dictionary used by the agents.
    """

    capacity_per_day = line.get("capacity_per_day", 0)
    utilization = line.get("current_utilization", 0)

    spare_capacity_per_day = round(
        capacity_per_day * (1 - utilization / 100),
        2
    )

    if line.get("status") != "Active":
        status = "OFFLINE"

    elif utilization >= BOTTLENECK_THRESHOLD:
        status = "BOTTLENECK"

    else:
        status = "AVAILABLE"

    return {
        "line_id": line.get("line_id"),
        "name": line.get("name"),
        "status": status,
        "line_status": line.get("status"),
        "capacity_per_day": capacity_per_day,
        "current_utilization": utilization,
        "spare_capacity_per_day": spare_capacity_per_day,
        "working_days_per_week": line.get("working_days_per_week", 6),
        "supported_skus": line.get("supported_skus", []),
        "recommendation": (
            "Line is offline and cannot be scheduled"
            if status == "OFFLINE"
            else "Utilization is critical — consider reallocation or overtime"
            if status == "BOTTLENECK"
            else "Line has spare capacity available"
        )
    }


def log_agent_activity(agent, action, severity="Low", **context):
    """
    Write an entry to the shared agent_activity collection so the
    Report Agent can build an audit trail (Responsible AI §11).
    """

    record = {
        "agent": agent,
        "action": action,
        "severity": severity,
        "timestamp": datetime.now(),
    }

    record.update(context)

    agent_activity_collection.insert_one(record)

    # Drop the ObjectId that pymongo attaches so the record stays
    # JSON-serializable when it is returned inside an API response.
    record.pop("_id", None)

    return record


# ============================================================
# 1. GET ALL PRODUCTION LINES
# ============================================================

def get_all_lines():
    """
    Return every production line with its derived capacity status.
    """

    lines = production_lines_collection.find()

    return [
        format_line(line)
        for line in lines
    ]


# ============================================================
# 1b. GET PRODUCIBLE PRODUCTS
# ============================================================

def get_producible_products():
    """
    Return the products this factory can actually build — those
    that have both a bill of materials and a production line.
    """

    routed_skus = {
        sku
        for line in production_lines_collection.find({}, {"supported_skus": 1})
        for sku in line.get("supported_skus", [])
    }

    bom_skus = set(bom_collection.distinct("sku"))

    buildable = routed_skus & bom_skus

    products = products_collection.find(
        {"sku": {"$in": list(buildable)}},
        {"_id": 0, "sku": 1, "name": 1, "category": 1}
    )

    return sorted(
        list(products),
        key=lambda product: product["sku"]
    )


# ============================================================
# 2. GET LINE FOR A SPECIFIC SKU
# ============================================================

def get_line_for_sku(sku):
    """
    Find the production line that builds a given product.
    """

    line = production_lines_collection.find_one({
        "supported_skus": sku
    })

    if not line:
        return None

    return format_line(line)


# ============================================================
# 3. GET LINE UTILIZATION
# ============================================================

def get_line_utilization():
    """
    Return utilization figures for every line, highest first.
    """

    lines = get_all_lines()

    return sorted(
        [
            {
                "line_id": line["line_id"],
                "name": line["name"],
                "current_utilization": line["current_utilization"],
                "capacity_per_day": line["capacity_per_day"],
                "spare_capacity_per_day": line["spare_capacity_per_day"],
                "status": line["status"],
            }
            for line in lines
        ],
        key=lambda line: line["current_utilization"],
        reverse=True
    )


# ============================================================
# 4. IDENTIFY BOTTLENECKS
# ============================================================

def identify_bottlenecks(threshold=BOTTLENECK_THRESHOLD):
    """
    Return lines running at or above the bottleneck threshold.
    """

    return [
        line
        for line in get_all_lines()
        if line["line_status"] == "Active"
        and line["current_utilization"] >= threshold
    ]


# ============================================================
# 5. GET PRODUCTION ORDERS
# ============================================================

def get_production_orders():
    """
    Return every production order with its completion progress.
    """

    orders = production_orders_collection.find()

    results = []

    for order in orders:

        planned = order.get("planned_quantity", 0)
        completed = order.get("completed_quantity", 0)

        remaining = max(planned - completed, 0)

        completion_percentage = (
            round(completed / planned * 100, 2)
            if planned
            else 0
        )

        results.append({
            "production_order_id": order.get("production_order_id"),
            "order_id": order.get("order_id"),
            "sku": order.get("sku"),
            "line_id": order.get("line_id"),
            "planned_quantity": planned,
            "completed_quantity": completed,
            "remaining_quantity": remaining,
            "completion_percentage": completion_percentage,
            "order_status": order.get("status"),
            "status": (
                "COMPLETED"
                if remaining == 0
                else "BEHIND_SCHEDULE"
                if completion_percentage < 50
                else "ON_TRACK"
            )
        })

    return results


# ============================================================
# 6. GET PROGRESS FOR ONE ORDER
# ============================================================

def get_production_progress(order_id=None, production_order_id=None):
    """
    Return the progress of a single production order, located by
    either the customer order id or the production order id.
    """

    for order in get_production_orders():

        if production_order_id and order["production_order_id"] == production_order_id:
            return order

        if order_id and order["order_id"] == order_id:
            return order

    return None


# ============================================================
# 7. GET MATERIAL REQUIREMENTS FROM THE BILL OF MATERIALS
# ============================================================

def get_material_requirements(sku, quantity):
    """
    Explode the bill of materials for a product into the total
    material quantities needed to build `quantity` units.
    """

    requirements = []

    for line in bom_collection.find({"sku": sku}):

        requirements.append({
            "material_code": line["material_code"],
            "qty_per_unit": line["qty_per_unit"],
            "required_quantity": round(line["qty_per_unit"] * quantity, 2),
            "unit": line["unit"],
        })

    return requirements


# ============================================================
# 8. CHECK CAPACITY
# ============================================================

def check_capacity(sku=None, product_name=None, quantity=0, required_date=None):
    """
    Determine whether a production line can build `quantity` units
    of a product before `required_date`.

    Three outcomes are possible:

        FEASIBLE    — the spare capacity alone is enough
        AT_RISK     — only achievable by freeing up existing capacity
        INFEASIBLE  — impossible even if the line ran at 100%
    """

    resolved_sku = resolve_sku(sku=sku, product_name=product_name)

    if resolved_sku is None:

        return {
            "status": "NOT_FOUND",
            "sku": sku,
            "product_name": product_name,
            "message": "Product was not found in the product master."
        }

    line = get_line_for_sku(resolved_sku)

    if line is None:

        return {
            "status": "NO_LINE",
            "sku": resolved_sku,
            "message": "No production line is configured to build this product."
        }

    target_date = parse_date(required_date)

    if target_date is None:

        return {
            "status": "MISSING_DATE",
            "sku": resolved_sku,
            "line_id": line["line_id"],
            "message": "A required-by date is needed to assess capacity."
        }

    days_available = (target_date - datetime.now()).days

    if days_available <= 0:

        return {
            "status": "INFEASIBLE",
            "sku": resolved_sku,
            "line_id": line["line_id"],
            "line_name": line["name"],
            "required_quantity": quantity,
            "days_available": days_available,
            "producible_quantity": 0,
            "shortfall": quantity,
            "message": "The required date has already passed.",
            "factors": [
                f"Required date is {abs(days_available)} days in the past"
            ]
        }

    # Calendar days are converted to working days so the estimate
    # reflects the line's actual shift pattern.
    working_days = days_available * (line["working_days_per_week"] / 7)

    producible_at_spare = line["spare_capacity_per_day"] * working_days
    producible_at_full = line["capacity_per_day"] * working_days

    shortfall = max(quantity - producible_at_spare, 0)

    days_needed = (
        round(quantity / line["spare_capacity_per_day"], 1)
        if line["spare_capacity_per_day"] > 0
        else None
    )

    if producible_at_spare >= quantity:
        status = "FEASIBLE"
        message = "Existing spare capacity is sufficient."

    elif producible_at_full >= quantity:
        status = "AT_RISK"
        message = (
            "The order can only be met by freeing up capacity that is "
            "already committed on this line."
        )

    else:
        status = "INFEASIBLE"
        message = (
            "The order exceeds what this line can physically produce "
            "before the required date, even at full capacity."
        )

    factors = [
        f"{line['name']} ({line['line_id']}) runs at {line['current_utilization']}% utilization",
        f"{line['spare_capacity_per_day']:,.0f} units/day spare of {line['capacity_per_day']:,} total",
        f"{days_available} calendar days available ({working_days:.1f} working days)",
        f"{producible_at_spare:,.0f} units producible with spare capacity",
    ]

    if shortfall > 0:
        factors.append(f"Shortfall of {shortfall:,.0f} units")

    return {
        "status": status,
        "sku": resolved_sku,
        "line_id": line["line_id"],
        "line_name": line["name"],
        "required_quantity": quantity,
        "required_date": target_date.strftime("%Y-%m-%d"),
        "days_available": days_available,
        "working_days": round(working_days, 1),
        "capacity_per_day": line["capacity_per_day"],
        "current_utilization": line["current_utilization"],
        "spare_capacity_per_day": line["spare_capacity_per_day"],
        "producible_quantity": round(producible_at_spare),
        "producible_at_full_capacity": round(producible_at_full),
        "shortfall": round(shortfall),
        "days_needed_at_current_pace": days_needed,
        "is_bottleneck": line["status"] == "BOTTLENECK",
        "message": message,
        "factors": factors,
    }


# ============================================================
# 9. SUGGEST REALLOCATION
# ============================================================

def suggest_reallocation(sku, shortfall, days_available):
    """
    Identify other active lines with spare capacity that could
    absorb a shortfall.

    This is a PROPOSAL only. It is never applied automatically —
    high-impact production changes require human approval (§9).
    """

    resolved_sku = resolve_sku(sku=sku)

    current_line = get_line_for_sku(resolved_sku) if resolved_sku else None

    current_line_id = current_line["line_id"] if current_line else None

    candidates = []

    for line in get_all_lines():

        if line["line_id"] == current_line_id:
            continue

        if line["line_status"] != "Active":
            continue

        if line["spare_capacity_per_day"] <= 0:
            continue

        # A line that is itself a bottleneck is not a credible place
        # to absorb overflow, even though it has spare capacity on paper.
        if line["status"] == "BOTTLENECK":
            continue

        working_days = days_available * (line["working_days_per_week"] / 7)

        absorbable = line["spare_capacity_per_day"] * working_days

        candidates.append({
            "line_id": line["line_id"],
            "line_name": line["name"],
            "current_utilization": line["current_utilization"],
            "spare_capacity_per_day": line["spare_capacity_per_day"],
            "absorbable_quantity": round(min(absorbable, shortfall)),
            "covers_full_shortfall": absorbable >= shortfall,
            "requires_retooling": resolved_sku not in line["supported_skus"],
        })

    candidates.sort(
        key=lambda option: option["absorbable_quantity"],
        reverse=True
    )

    total_absorbable = sum(
        option["absorbable_quantity"]
        for option in candidates
    )

    return {
        "sku": resolved_sku,
        "shortfall": round(shortfall),
        "total_absorbable": round(total_absorbable),
        "fully_recoverable": total_absorbable >= shortfall,
        "requires_approval": True,
        "options": candidates,
    }


# ============================================================
# 10. CHECK PRODUCTION FEASIBILITY
# ============================================================
#
# This is the agent-to-agent workflow required by the system
# design (§5, §6). The Production Agent explodes the bill of
# materials and sends one MATERIAL_CHECK message per material to
# the Inventory Agent. The replies change the final verdict — a
# line with enough capacity is still AT_RISK if the fabric to
# feed it is not in stock.

def check_production_feasibility(
    sku=None,
    product_name=None,
    quantity=0,
    required_date=None
):
    """
    Full feasibility assessment combining line capacity with a
    material availability check delegated to the Inventory Agent.
    """

    resolved_sku = resolve_sku(sku=sku, product_name=product_name)

    if resolved_sku is None:

        return {
            "status": "NOT_FOUND",
            "sku": sku,
            "product_name": product_name,
            "message": "Product was not found in the product master."
        }

    product = products_collection.find_one({"sku": resolved_sku})

    # --------------------------------------------------------
    # Capacity assessment
    # --------------------------------------------------------

    capacity = check_capacity(
        sku=resolved_sku,
        quantity=quantity,
        required_date=required_date
    )

    # --------------------------------------------------------
    # Material assessment — Production Agent → Inventory Agent
    # --------------------------------------------------------

    material_checks = []

    for requirement in get_material_requirements(resolved_sku, quantity):

        message = {
            "sender": "production_agent",
            "receiver": "inventory_agent",
            "message_type": "MATERIAL_CHECK",
            "material_code": requirement["material_code"],
            "required_quantity": requirement["required_quantity"],
        }

        response = check_inventory_requirement(
            material_code=requirement["material_code"],
            required_quantity=requirement["required_quantity"]
        )

        material_checks.append({
            "request": message,
            "response": response,
        })

    blocking_materials = [
        check["response"]
        for check in material_checks
        if check["response"].get("status") in ("SHORTAGE", "NOT_FOUND")
    ]

    # --------------------------------------------------------
    # Combined verdict
    # --------------------------------------------------------
    #
    # Material availability genuinely changes the outcome: an
    # order the line could build is still at risk without stock.

    if capacity["status"] in ("NOT_FOUND", "NO_LINE", "MISSING_DATE"):
        status = capacity["status"]

    elif capacity["status"] == "INFEASIBLE":
        status = "INFEASIBLE"

    elif capacity["status"] == "AT_RISK" or blocking_materials:
        status = "AT_RISK"

    else:
        status = "FEASIBLE"

    # --------------------------------------------------------
    # Explainability — the evidence behind the verdict (§11)
    # --------------------------------------------------------

    factors = list(capacity.get("factors", []))

    for material in blocking_materials:

        if material.get("status") == "SHORTAGE":

            factors.append(
                f"{material['material_name']} short by "
                f"{material['shortage']:,.0f} {material['unit']}"
            )

        else:

            factors.append(
                f"{material.get('material_code')} not found in inventory"
            )

    if not blocking_materials:
        factors.append("All required materials are in stock")

    # --------------------------------------------------------
    # Reallocation proposal when capacity is the constraint
    # --------------------------------------------------------

    reallocation = None

    if capacity.get("shortfall", 0) > 0:

        reallocation = suggest_reallocation(
            sku=resolved_sku,
            shortfall=capacity["shortfall"],
            days_available=capacity.get("days_available", 0)
        )

    # --------------------------------------------------------
    # Audit trail (§11)
    # --------------------------------------------------------

    log_agent_activity(
        agent="Production Agent",
        action=f"Feasibility assessed for {quantity:,} x {resolved_sku}: {status}",
        severity=(
            "High"
            if status == "INFEASIBLE"
            else "Medium"
            if status == "AT_RISK"
            else "Low"
        ),
        sku=resolved_sku,
        line_id=capacity.get("line_id"),
        required_quantity=quantity,
        materials_checked=len(material_checks),
        blocking_materials=[
            material.get("material_code")
            for material in blocking_materials
        ],
    )

    return {
        "status": status,
        "sku": resolved_sku,
        "product_name": product.get("name") if product else None,
        "required_quantity": quantity,
        "required_date": capacity.get("required_date"),
        "capacity": capacity,
        "materials": material_checks,
        "blocking_materials": blocking_materials,
        "reallocation": reallocation,
        "requires_approval": status != "FEASIBLE",
        "factors": factors,
        "workflow": [
            "Production Agent",
            "Inventory Agent"
        ],
        "message": (
            "The order can be produced on schedule."
            if status == "FEASIBLE"
            else "The order is at risk and needs attention before it is committed."
            if status == "AT_RISK"
            else capacity.get("message", "The order cannot be produced as requested.")
        ),
    }


# ============================================================
# 11. PRODUCTION KPIs
# ============================================================

def get_production_kpis():
    """
    Calculate basic production KPIs.
    """

    lines = get_all_lines()

    active_lines = [
        line
        for line in lines
        if line["line_status"] == "Active"
    ]

    orders = get_production_orders()

    total_planned = sum(order["planned_quantity"] for order in orders)
    total_completed = sum(order["completed_quantity"] for order in orders)

    average_utilization = (
        round(
            sum(line["current_utilization"] for line in active_lines)
            / len(active_lines),
            2
        )
        if active_lines
        else 0
    )

    on_track = sum(
        1
        for order in orders
        if order["status"] in ("ON_TRACK", "COMPLETED")
    )

    return {
        "total_lines": len(lines),
        "active_lines": len(active_lines),
        "average_utilization": average_utilization,
        "bottleneck_count": len(identify_bottlenecks()),
        "total_capacity_per_day": sum(
            line["capacity_per_day"] for line in active_lines
        ),
        "spare_capacity_per_day": round(
            sum(line["spare_capacity_per_day"] for line in active_lines),
            2
        ),
        "total_production_orders": len(orders),
        "orders_on_track": on_track,
        "on_track_percentage": (
            round(on_track / len(orders) * 100, 2)
            if orders
            else 0
        ),
        "total_planned_quantity": total_planned,
        "total_completed_quantity": total_completed,
        "overall_completion_percentage": (
            round(total_completed / total_planned * 100, 2)
            if total_planned
            else 0
        ),
        "production_health": (
            "CRITICAL"
            if len(identify_bottlenecks()) >= 2
            else "NEEDS_ATTENTION"
            if identify_bottlenecks()
            else "HEALTHY"
        ),
    }


# ============================================================
# 12. PRODUCTION SUMMARY
# ============================================================

def get_production_summary():
    """
    Provide a high-level production health summary.
    """

    kpis = get_production_kpis()

    bottlenecks = identify_bottlenecks()

    behind = [
        order
        for order in get_production_orders()
        if order["status"] == "BEHIND_SCHEDULE"
    ]

    return {
        "average_utilization": kpis["average_utilization"],
        "active_lines": kpis["active_lines"],
        "bottlenecks": [
            {
                "line_id": line["line_id"],
                "name": line["name"],
                "current_utilization": line["current_utilization"],
            }
            for line in bottlenecks
        ],
        "orders_behind_schedule": [
            {
                "production_order_id": order["production_order_id"],
                "sku": order["sku"],
                "completion_percentage": order["completion_percentage"],
            }
            for order in behind
        ],
        "production_health": kpis["production_health"],
    }
