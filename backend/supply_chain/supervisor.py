import os
import sys
from typing import Literal, Optional
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
# Output Schema
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
# LLM Router Agent
# ------------------------------------------------------------------

def process_chat_message(user_message: str) -> SupervisorDecision:
    """
    Uses ChatGroq to parse the user's natural language intent.
    Routes between Scenario A (Targeted) and Scenario B (Autonomous).
    """
    if ChatGroq is None:
        return _deterministic_decision(user_message)

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
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


def _deterministic_decision(user_message: str) -> SupervisorDecision:
    text = user_message.lower()
    qty_match = __import__("re").search(r"(\d[\d,]*)", user_message)
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

if __name__ == "__main__":
    # Test cases
    print(process_chat_message("I need 400 meters of organic cotton"))
    print(process_chat_message("I need to order from EcoWeave Bangladesh"))
    print(process_chat_message("We are low on accessories, buy 1200 YKK zippers"))
