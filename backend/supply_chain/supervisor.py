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

from backend.supply_chain.security_utils import mask_pii, detect_prompt_injection, validate_output

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
    material_name: Optional[str] = Field(
        default=None, description="The name of the material being ordered (e.g., 'Grey Fleece Fabric', 'YKK Zippers')."
    )
    color_base: Optional[str] = Field(
        default=None, description="The base color extracted from the text (e.g., 'Grey' from 'Grey Fleece Fabric')."
    )
    color_spec: Optional[str] = Field(
        default=None, description="The specific shade if mentioned, otherwise leave empty or match color_base."
    )


# ------------------------------------------------------------------
# LLM Router Agent (existing)
# ------------------------------------------------------------------

def process_chat_message(user_message: str) -> SupervisorDecision:
    """
    Uses ChatGroq to parse the user's natural language intent.
    Routes between Scenario A (Targeted) and Scenario B (Autonomous).
    """
    # 1. Security Check: Prompt Injection
    if detect_prompt_injection(user_message):
        return SupervisorDecision(
            scenario="unrelated",
            supplier_name=None,
            material_type="unknown",
            qty=300,
            total_value=0.0,
            requirement_id=2
        )
        
    # 2. Privacy Check: Mask PII
    safe_message = mask_pii(user_message)

    if ChatGroq is None:
        return _deterministic_decision(safe_message)

    try:
        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
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
        decision = chain.invoke({"text": safe_message})
        
        # 3. Responsible AI Check: Validate Output
        validated_dict = validate_output(decision.model_dump())
        return SupervisorDecision(**validated_dict)
    except Exception as e:
        print(f"[Supervisor] Groq process_chat_message error: {e}")
        return _deterministic_decision(safe_message)


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

    # Simple extraction for direct low-stock orders
    colors = ["grey", "blue", "red", "green", "white", "black", "yellow", "orange", "purple", "pink"]
    found_color = next((c.capitalize() for c in colors if c in text), None)
    
    # Try to extract the item name, e.g. "Order 200 meters of Grey Fleece Fabric"
    material_name = "Material"
    if " of " in user_message.lower():
        material_name = user_message.split(" of ", 1)[-1].strip().title()
        if " from " in material_name.lower():
            material_name = material_name.split(" From ", 1)[0].split(" from ", 1)[0]
    elif "order " in user_message.lower():
        material_name = user_message.split("order ", 1)[-1].strip().title()
        if " from " in material_name.lower():
            material_name = material_name.split(" From ", 1)[0].split(" from ", 1)[0]

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
            material_name=None,
            color_base=None,
            color_spec=None,
        )

    return SupervisorDecision(
        scenario="targeted" if supplier_name else "autonomous",
        supplier_name=supplier_name,
        material_type=material_type,
        qty=qty,
        total_value=total_value,
        requirement_id=requirement_id,
        material_name=material_name,
        color_base=found_color,
        color_spec=found_color,
    )


# ------------------------------------------------------------------
# Multi-turn Requirements Gathering
# ------------------------------------------------------------------

GATHER_SYSTEM_PROMPT = """You are a procurement assistant for a textile supply chain.
Collect these fields through a friendly conversation, then return a JSON summary.

FIELDS TO COLLECT (ask only for what is missing, ONE question at a time):
1. material_name  - brief description (e.g. "Cotton 180gsm", "YKK Coil Zipper"). Extract this automatically if the user mentions materials like cotton, zippers, dye, etc. If missing, ask "What type of material do you need?".
2. material_type  - Automatically deduce this from material_name. MUST be one of: "fabric_mill" (for cotton/fabric/denim/fleece), "trim_vendor" (for zipper/button/trim/label), "dye_house" (for dye/dyeing). NEVER ask the user to provide this.
3. qty            - integer number (e.g. 400). Extract automatically if provided.
4. unit           - meters / pieces / kg / liters / yards. Extract automatically if provided.
5. color_base     - Extract this automatically if the user mentions a color in their request (e.g., if they say "Grey Fleece", color_base is "Grey"). ONLY if missing, ask the user: "What base colour do you need? (e.g. White, Blue, Green, Red, Grey)".
6. color_spec     - Extract this automatically if a specific shade is mentioned. If only color_base is known but not the exact shade, ask them: "Please select the exact shade of {color_base}:"

RULES:
- Ask exactly ONE question per turn.
- Accept any answer the user gives for color or dimensions.
- If compliance is not mentioned, set compliance_keywords to [].
- DO NOT ask for destination. It is ALWAYS "Colombo, Sri Lanka".
- Once you have all fields (including color_spec), output status "ready" immediately.
- Only two valid status values: "needs_more_info" or "ready". Never output any other status.

Output format when still gathering:
{"status":"needs_more_info","question":"<your single question here>"}

Output format when ALL fields are known:
{"status":"ready","material_type":"fabric_mill","material_name":"Organic Cotton 180gsm","qty":400,"unit":"meters","color_base":"Green","color_spec":"Dark Green","compliance_keywords":[],"destination":"Colombo, Sri Lanka","requirement_id":2,"total_value":104000.0}

requirement_id: fabric_mill=2, trim_vendor=4, dye_house=5
total_value: trim_vendor = qty*15.0, all others = qty*260.0

CRITICAL: Output ONLY valid JSON. No markdown, no code fences, no explanations."""



def gather_requirements(conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Multi-turn requirements gathering using Groq LLM.

    Args:
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} messages

    Returns:
        dict with "status": "needs_more_info" + "question",
        or "status": "ready" with all requirements fields.
    """
    # 1 & 2. Security Check & Privacy Masking on incoming user messages
    for msg in conversation_history:
        if msg["role"] == "user":
            if detect_prompt_injection(msg["content"]):
                return {"status": "needs_more_info", "question": "I detected a potentially unsafe request. How else can I assist you with procurement?"}
            msg["content"] = mask_pii(msg["content"])

    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        messages = [{"role": "system", "content": GATHER_SYSTEM_PROMPT}]
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            temperature=0,
            max_tokens=600,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)

        # Normalise: only allow 'needs_more_info' or 'ready'
        if result.get("status") not in ("needs_more_info", "ready"):
            question = result.get("question") or result.get("message") or "Could you provide more details?"
            result = {"status": "needs_more_info", "question": question}
            
        # 3. Responsible AI Check: Validate output if ready
        if result.get("status") == "ready":
            result = validate_output(result)

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
                elif "what colour or shade do you need" in msg_lower or "what shade name do you need" in msg_lower or "what base colour do you need" in msg_lower:
                    extracted = extract_color(next_user)
                    if extracted:
                        collected["color_base"] = extracted
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
        if "color_base" in collected:
            base = collected["color_base"]
            prompt = f"Please select the exact shade of {base}:"
            if context_switch_detected:
                prompt = "I can only assist with gathering procurement details right now. " + prompt
            return {"status": "needs_more_info", "question": prompt}
        else:
            prompt = "What base colour do you need? (e.g. White, Blue, Green, Red, Grey)"
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
        "color_base": collected.get("color_base", "Any"),
        "color_spec": collected.get("color_spec", "Any"),
        "compliance_keywords": collected.get("compliance_keywords", []),
        "destination": "Colombo, Sri Lanka",
        "requirement_id": collected.get("requirement_id", 2),
        "total_value": total,
    }


if __name__ == "__main__":
    # Test cases
    print(process_chat_message("I need 400 meters of organic cotton"))
    print(process_chat_message("I need to order from EcoWeave Bangladesh"))
    print(process_chat_message("We are low on accessories, buy 1200 YKK zippers"))
