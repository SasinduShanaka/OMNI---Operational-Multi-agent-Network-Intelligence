import os
import sys
import json
import re
import colorsys
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    ChatGroq = None
    ChatPromptTemplate = None

from dotenv import load_dotenv

# Load env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

# ------------------------------------------------------------------
# Output Schemas
# ------------------------------------------------------------------

class SupervisorDecision(BaseModel):
    scenario: Literal["targeted", "autonomous", "unrelated"] = Field(
        description="targeted: User specifically named a supplier. autonomous: User just wants materials. unrelated: Not a supply chain request."
    )
    supplier_name: Optional[str] = Field(
        description="The exact name of the supplier if 'targeted'. E.g. 'EcoWeave Bangladesh'."
    )
    material_type: Literal["fabric_mill", "trim_vendor", "dye_house", "unknown"] = Field(
        description="The category of material needed. Map raw text to one of the 3 allowed categories."
    )
    qty: int = Field(
        description="Quantity of the material needed. Extract from text, default to 300 if not specified."
    )
    total_value: float = Field(
        description="Estimated cost. If trim_vendor, qty * 15. If fabric_mill or dye_house, qty * 260."
    )
    requirement_id: int = Field(
        description="Map material_type to requirement: trim_vendor=4, dye_house=5, fabric_mill=2."
    )


# ------------------------------------------------------------------
# LLM Router Agent (existing)
# ------------------------------------------------------------------

def process_chat_message(user_message: str) -> SupervisorDecision:
    """
    Uses ChatGroq to parse the user's natural language intent.
    Routes between Scenario A (Targeted) and Scenario B (Autonomous).
    """
    if ChatGroq is None:
        return _deterministic_decision(user_message)

    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        structured_llm = llm.with_structured_output(SupervisorDecision)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Supply Chain Supervisor AI.
Your job is to read user messages and extract procurement details.

Categories mapping:
- "fabric_mill": cotton, fabric, cloth, meters, yards
- "trim_vendor": buttons, zippers, accessories, trim
- "dye_house": dye, color, liters, dye house

Requirement ID mapping:
- fabric_mill -> 2
- trim_vendor -> 4
- dye_house   -> 5

Scenarios:
- If the user says "I need to order from [Supplier Name]", it is a "targeted" request.
- If the user says "I need 500 zippers", it is an "autonomous" request.
- If they say "hello", "what is the weather", it is "unrelated".

Calculate total_value:
- trim_vendor: qty * 15.0
- others: qty * 260.0

Extract the data strictly according to the schema.
"""),
            ("human", "{text}")
        ])

        chain = prompt | structured_llm
        decision = chain.invoke({"text": user_message})
        return decision
    except Exception as e:
        print(f"[Supervisor] Groq process_chat_message error: {e}")
        return _deterministic_decision(user_message)


def _deterministic_decision(user_message: str) -> SupervisorDecision:
    text = user_message.lower()
    qty_match = re.search(r"(\d[\d,]*)", user_message)
    qty = int(qty_match.group(1).replace(",", "")) if qty_match else 300

    supplier_names = [
        "Textiles Lanka",
        "Cotton World India",
        "Denim House Turkey",
        "EcoWeave Bangladesh",
        "Fleece Pro Pakistan",
        "Zipper King China",
        "Button & Thread Co.",
        "Label Craft India",
        "ColorDye House Sri Lanka",
        "DyeTech Bangladesh",
    ]
    supplier_name = next((name for name in supplier_names if name.lower() in text), None)

    if any(word in text for word in ("zipper", "button", "trim", "label", "accessor")):
        material_type = "trim_vendor"
        requirement_id = 4
        total_value = qty * 15.0
    elif any(word in text for word in ("dye", "color")):
        material_type = "dye_house"
        requirement_id = 5
        total_value = qty * 260.0
    elif any(word in text for word in ("fabric", "cotton", "cloth", "meter", "yard", "fleece", "denim")):
        material_type = "fabric_mill"
        requirement_id = 2
        total_value = qty * 260.0
    else:
        return SupervisorDecision(
            scenario="unrelated",
            supplier_name=None,
            material_type="unknown",
            qty=qty,
            total_value=0,
            requirement_id=2,
        )

    return SupervisorDecision(
        scenario="targeted" if supplier_name else "autonomous",
        supplier_name=supplier_name,
        material_type=material_type,
        qty=qty,
        total_value=total_value,
        requirement_id=requirement_id,
    )


# ------------------------------------------------------------------
# Multi-turn Requirements Gathering
# ------------------------------------------------------------------

GATHER_SYSTEM_PROMPT = """You are an expert procurement assistant for a garment & textile supply chain.
Your job: collect ALL required information through a friendly, professional conversation, then output a structured JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Detect product type from what the user says.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Map to material_type:
• "fabric_mill": cotton, woven fabric, denim, fleece, lining, interlining, padding, wadding, shoulder pad, bias tape, piping
• "trim_vendor": zipper, button, snap, rivet, eyelet, velcro, thread, embroidery thread, label, hang tag, cord, drawstring, elastic, sequin, bead, polybag
• "dye_house": dye, reactive dye, disperse dye, acid dye, vat dye, dyeing service, color treatment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Ask ONLY for missing fields, ONE at a time.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always collect:
A) material_name — exact spec (e.g. "Organic Cotton 180gsm", "YKK Coil Zipper")
B) qty           — number only (e.g. 500)
C) unit          — meters / pieces / kg / liters / rolls / cones / pairs / sets / gross
D) color_spec    — colour or shade; use "Natural/Undyed" if not applicable
E) compliance_keywords — e.g. ["Organic Cotton","Child-Labor Free","OEKO-TEX"]; use [] if none
F) destination   — city and country (e.g. "Colombo, LK")
G) dimensions    — product-specific technical specs (see table below)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIMENSIONS TABLE — ask ONLY the fields relevant to the product:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 1 Cotton/Woven Fabric   → width_inches (44/54/60/72), gsm
 2 Fleece/Knit Fabric    → gsm, width_inches
 3 Denim Fabric          → oz_weight (e.g. 12), width_inches
 4 Lining Fabric         → width_inches, composition (e.g. "100% polyester")
 5 Interlining/Fusible   → gsm, width_inches, fusible ("yes"/"no")
 6 Elastic Band          → width_mm (e.g. 25), stretch_pct (e.g. 120)
 7 Zipper                → length_cm, zipper_type ("coil"/"metal"/"invisible"/"waterproof"), brand (e.g. "YKK")
 8 Button                → diameter_mm, holes (2/4/"shank"), material ("plastic"/"metal"/"wood"/"corozo")
 9 Snap Button/Press Stud→ diameter_mm, material ("brass"/"stainless"/"plastic")
10 Rivet/Jeans Button    → cap_dia_mm, post_length_mm
11 Eyelet/Grommet        → inner_dia_mm, material ("brass"/"stainless"/"aluminium")
12 Velcro/Hook&Loop      → width_mm, velcro_type ("sew-on"/"adhesive"/"iron-on")
13 Sewing Thread         → thread_count (e.g. "40/2"), fibre ("polyester"/"cotton"/"nylon")
14 Embroidery Thread     → thread_count (e.g. "40wt"), fibre ("rayon"/"polyester"/"cotton"), colour_code
15 Woven Label           → size_mm (e.g. "50x30"), num_colours, label_content ("brand"/"care"/"size")
16 Printed/HT Label      → size_mm, print_type ("heat-transfer"/"screen-print"/"digital")
17 Hang Tag/Price Tag    → size_mm, tag_material ("card"/"plastic"), holes (0/1/2)
18 Cord/Drawstring       → diameter_mm, material ("cotton"/"polyester"/"nylon")
19 Bias Tape             → width_mm, fold_type ("single"/"double"/"bias")
20 Piping/Cord Trim      → diameter_mm, fabric_covered ("yes"/"no")
21 Shoulder Pad          → thickness_mm, pad_shape ("set-in"/"raglan"/"extended-shoulder")
22 Padding/Wadding       → gsm, width_inches, fill_type ("polyester"/"down"/"recycled")
23 Sequins/Beads         → size_mm, shape ("round"/"oval"/"cup"/"flat"), material ("plastic"/"metal")
24 Dye/Chemical          → dye_class ("reactive"/"disperse"/"acid"/"vat"/"pigment"), shade, depth_owf (e.g. "3%")
25 Polybag/Packaging     → size_cm (e.g. "40x60"), micron (e.g. 50), printed ("yes"/"no")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — When ALL fields are collected, output ONLY this JSON (no extra text, no markdown):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{"status":"ready","material_type":"fabric_mill","material_name":"Organic Cotton 180gsm","qty":500,"unit":"meters","color_spec":"Navy Blue","dimensions":{"width_inches":60,"gsm":180},"compliance_keywords":["Organic Cotton","Child-Labor Free"],"destination":"Colombo, LK","requirement_id":2,"total_value":127500.0}

Mappings:
- requirement_id: fabric_mill=2, trim_vendor=4, dye_house=5
- total_value: trim_vendor = qty * 15, others = qty * 260

If not ready, output ONLY:
{"status":"needs_more_info","question":"What is the fabric width? (e.g. 44, 60, or 72 inches)"}

CRITICAL: Response must be valid JSON only. No markdown, no code fences, no explanation text whatsoever.
"""


def gather_requirements(conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Multi-turn requirements gathering using Groq LLM.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} messages

    Returns:
        dict with "status": "needs_more_info" + "question",
        or "status": "ready" with all requirements fields.
    """
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        messages = [{"role": "system", "content": GATHER_SYSTEM_PROMPT}]
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0,
            max_tokens=600,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        return result

    except Exception as e:
        print(f"[Supervisor] Groq gather error: {e}")
        return _deterministic_gather(conversation_history)


def _deterministic_gather(conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback: keyword-based extraction with dimension detection."""
    all_text = " ".join(
        msg["content"] for msg in conversation_history if msg["role"] == "user"
    ).lower()

    collected: Dict[str, Any] = {}
    dimensions: Dict[str, Any] = {}

    # ── material_type detection (extended for 25 products) ─────────────────
    fabric_words   = ("fabric", "cotton", "cloth", "denim", "fleece", "lining", "interlining",
                      "padding", "wadding", "shoulder pad", "bias tape", "piping", "woven")
    trim_words     = ("zipper", "button", "snap", "rivet", "eyelet", "velcro", "thread",
                      "embroidery", "label", "hang tag", "price tag", "cord", "drawstring",
                      "elastic", "sequin", "bead", "polybag", "trim", "accessor")
    dye_words      = ("dye", "dyeing", "reactive", "disperse", "acid dye", "vat dye")

    if any(w in all_text for w in fabric_words):
        collected["material_type"] = "fabric_mill"
        collected["requirement_id"] = 2
    elif any(w in all_text for w in trim_words):
        collected["material_type"] = "trim_vendor"
        collected["requirement_id"] = 4
    elif any(w in all_text for w in dye_words):
        collected["material_type"] = "dye_house"
        collected["requirement_id"] = 5

    # ── quantity ──────────────────────────────────────────────────────────
    qty_match = re.search(r"(\d+)(?:\.\d+)?", all_text)
    if qty_match:
        collected["qty"] = float(qty_match.group(1))
    else:
        number_words = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "couple", "hundred", "thousand"]
        if any(w in all_text for w in number_words):
            collected["qty_has_words"] = True

    # ── unit ──────────────────────────────────────────────────────────────
    for sing, plural in [("meter","meters"),("piece","pieces"),("kg","kg"),
                          ("liter","liters"),("cone","cones"),("roll","rolls"),
                          ("pair","pairs"),("set","sets"),("gross","gross"),("yard","yards")]:
        if sing in all_text or plural in all_text:
            collected["unit"] = plural
            break

    BASE_COLOR_HEX = {
        "navy blue": "#1E3A8A", "navy": "#1E3A8A", "royal blue": "#2563EB", 
        "sky blue": "#7DD3FC", "red": "#EF4444", "maroon": "#7F1D1D", 
        "green": "#22C55E", "olive": "#4D7C0F", "white": "#F8FAFC", 
        "off white": "#F1F5F9", "black": "#0F172A", "grey": "#64748B", 
        "gray": "#64748B", "beige": "#F5F5DC", "khaki": "#F0E68C",
        "yellow": "#EAB308", "orange": "#F97316", "purple": "#A855F7",
        "pink": "#EC4899", "natural": "#FDFBF7", "undyed": "#FDFBF7",
        "organic": "#FDFBF7"
    }
    
    KNOWN_COLORS = tuple(BASE_COLOR_HEX.keys())

    def generate_color_gradient(base_name: str) -> list:
        base_hex = BASE_COLOR_HEX.get(base_name.lower(), "#94A3B8")
        
        # Parse hex
        hex_code = base_hex.lstrip('#')
        r, g, b = tuple(int(hex_code[i:i+2], 16)/255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        
        def to_hex(r, g, b):
            return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
            
        shades = []
        # 5 Lighter (from lightest to standard)
        for i in range(5, 0, -1):
            lightness = min(0.96, l + (0.98 - l) * (i / 6.0))
            nr, ng, nb = colorsys.hls_to_rgb(h, lightness, s)
            shades.append({"name": f"Light {base_name} {6-i}", "hex": to_hex(nr, ng, nb)})
            
        # Standard
        shades.append({"name": f"Standard {base_name}", "hex": base_hex})
        
        # 5 Darker (from standard to darkest)
        for i in range(1, 6):
            lightness = max(0.04, l * (1 - (i / 6.0)))
            nr, ng, nb = colorsys.hls_to_rgb(h, lightness, s)
            shades.append({"name": f"Dark {base_name} {i}", "hex": to_hex(nr, ng, nb)})
            
        return shades

    def extract_color(text: str) -> str:
        for c in KNOWN_COLORS:
            if c in text:
                c_idx = text.find(c)
                prefix = text[:c_idx].strip().split()
                if prefix and prefix[-1] in ("not", "except", "but", "non", "without"):
                    continue
                return c.title()
        return None

    def is_context_switch(text: str) -> bool:
        if "?" in text: return True
        first_word = text.split()[0] if text.split() else ""
        if first_word in ("what", "how", "can", "why", "where", "who", "wait"): return True
        return False

    context_switch_detected = False

    # ── Replay conversation for context-dependent answers ─────────────────
    for i in range(len(conversation_history)):
        msg = conversation_history[i]
        if msg["role"] == "assistant":
            msg_lower = msg["content"].lower()
            if i + 1 < len(conversation_history) and conversation_history[i+1]["role"] == "user":
                next_user = conversation_history[i+1]["content"].lower()

                if is_context_switch(next_user):
                    context_switch_detected = True
                    continue

                if "please select the exact shade" in msg_lower or "please confirm the exact shade" in msg_lower:
                    collected["color_spec"] = next_user.strip().title()
                elif "what colour or shade do you need" in msg_lower or "what shade name do you need" in msg_lower:
                    extracted = extract_color(next_user)
                    if extracted:
                        collected["base_color"] = extracted
                elif "what is the fabric width" in msg_lower:
                    if any(w in next_user for w in ("don't know", "dont know", "not sure", "any")):
                        dimensions["width_inches"] = 54
                    else:
                        width_match = re.search(r"(\d+)", next_user)
                        if width_match:
                            dimensions["width_inches"] = int(width_match.group(1))

    # ── dimensions (basic extraction) ────────────────────────────────────
    inch_m = re.search(r"(\d+)\s*(?:inch|in\b|\")", all_text)
    gsm_m  = re.search(r"(\d+)\s*gsm", all_text)
    oz_m   = re.search(r"(\d+)\s*oz", all_text)
    mm_m   = re.search(r"(\d+)\s*mm", all_text)
    cm_m   = re.search(r"(\d+)\s*cm", all_text)
    if inch_m and "width_inches" not in dimensions: dimensions["width_inches"] = int(inch_m.group(1))
    if gsm_m:  dimensions["gsm"]          = int(gsm_m.group(1))
    if oz_m:   dimensions["oz_weight"]    = int(oz_m.group(1))
    if mm_m:   dimensions["width_mm"]     = int(mm_m.group(1))
    if cm_m:   dimensions["length_cm"]    = int(cm_m.group(1))
    if "coil"        in all_text: dimensions["zipper_type"] = "coil"
    elif "invisible" in all_text: dimensions["zipper_type"] = "invisible"
    elif "metal"     in all_text: dimensions["zipper_type"] = "metal"
    if "ykk" in all_text: dimensions["brand"] = "YKK"
    for dc in ("reactive","disperse","acid","vat","pigment"):
        if dc in all_text: dimensions["dye_class"] = dc; break
    if dimensions:
        collected["dimensions"] = dimensions

    # ── ask for missing fields ────────────────────────────────────────────
    mat = collected.get("material_type")
    if not mat:
        prompt = "What type of material do you need? (e.g. cotton fabric, zippers, dye, elastic, button...)"
        if context_switch_detected:
            prompt = "I can only assist with gathering procurement details right now. " + prompt
        return {"status": "needs_more_info", "question": prompt}
    
    if "qty" not in collected:
        prompt = "How much do you need? Please give a number and unit (e.g. 500 meters, 2000 pieces)."
        if collected.get("qty_has_words"):
            prompt = "Please use digits (e.g., 500) instead of words for the quantity."
        elif context_switch_detected:
            prompt = "I can only assist with gathering procurement details right now. " + prompt
        return {"status": "needs_more_info", "question": prompt}

    if "unit" not in collected:
        collected["unit"] = "meters" if mat == "fabric_mill" else ("kg" if mat == "dye_house" else "pieces")
    
    if "color_spec" not in collected:
        if "base_color" in collected:
            base = collected["base_color"]
            return {
                "status": "needs_shade_selection",
                "question": f"Please select the exact shade of {base}:",
                "shades": generate_color_gradient(base)
            }
        else:
            # See if there's a hardcoded color in all_text
            found_color = extract_color(all_text)
            if found_color:
                return {
                    "status": "needs_shade_selection",
                    "question": f"Please select the exact shade of {found_color}:",
                    "shades": generate_color_gradient(found_color)
                }
            
            prompt = ("What colour or shade do you need? (e.g. Navy Blue, Natural/Undyed)"
                      if mat != "dye_house" else
                      "What shade name do you need? (e.g. Navy Blue, Forest Green)")
            if context_switch_detected:
                prompt = "I can only assist with gathering procurement details right now. " + prompt
            return {"status": "needs_more_info", "question": prompt}

    if not collected.get("dimensions") and mat == "fabric_mill":
        prompt = "What is the fabric width? (e.g. 44, 54, 60, or 72 inches)"
        if context_switch_detected:
            prompt = "I can only assist with gathering procurement details right now. " + prompt
        return {"status": "needs_more_info", "question": prompt}

    qty   = collected["qty"]
    total = qty * 15.0 if mat == "trim_vendor" else qty * 260.0

    return {
        "status": "ready",
        "material_type": mat,
        "material_name": collected.get("color_spec", "Standard") + " material",
        "qty": qty,
        "unit": collected["unit"],
        "color_spec": collected.get("color_spec", "any"),
        "dimensions": collected.get("dimensions", {}),
        "compliance_keywords": collected.get("compliance_keywords", []),
        "destination": "Colombo, LK",
        "requirement_id": collected.get("requirement_id", 2),
        "total_value": total,
    }


if __name__ == "__main__":
    # Test cases
    print(process_chat_message("I need 400 meters of organic cotton"))
    print(process_chat_message("I need to order from EcoWeave Bangladesh"))
    print(process_chat_message("We are low on accessories, buy 1200 YKK zippers"))
