import re
from typing import Dict, Any

def mask_pii(text: str) -> str:
    """
    Masks Personally Identifiable Information (PII) from text.
    Redacts phone numbers, email addresses, and credit card patterns.
    """
    if not text:
        return text
    
    # Mask Email
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    text = re.sub(email_pattern, '[REDACTED_EMAIL]', text)
    
    # Mask Phone Numbers (basic formats)
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)
    
    # Mask Credit Cards (13-19 digits, possibly separated by spaces or dashes)
    cc_pattern = r'\b(?:\d[ -]*?){13,19}\b'
    text = re.sub(cc_pattern, '[REDACTED_CREDIT_CARD]', text)
    
    return text


def detect_prompt_injection(text: str) -> bool:
    """
    Detects simple prompt injection and jailbreak attempts via keyword matching.
    Returns True if an injection attempt is detected.
    """
    if not text:
        return False
        
    text_lower = text.lower()
    
    injection_keywords = [
        "ignore all previous instructions",
        "ignore previous instructions",
        "system prompt",
        "jailbreak",
        "you are now",
        "disregard all",
        "bypass",
        "override",
        "output status: ready"
    ]
    
    for keyword in injection_keywords:
        if keyword in text_lower:
            return True
            
    return False


def validate_output(decision_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates LLM output to prevent hallucinated data (Responsible AI).
    Enforces minimum quantities and valid material types.
    """
    # Fix negative or zero quantities
    if "qty" in decision_data:
        try:
            qty = float(decision_data["qty"])
            if qty <= 0:
                decision_data["qty"] = 100 # Default safe fallback
        except (ValueError, TypeError):
            decision_data["qty"] = 100
            
    # Enforce valid material types
    valid_types = ["fabric_mill", "trim_vendor", "dye_house", "unknown"]
    if decision_data.get("material_type") not in valid_types:
        decision_data["material_type"] = "unknown"
        
    return decision_data


def validate_retrieval_query(category: str) -> bool:
    """
    Validates parameter for Information Retrieval to prevent manipulation.
    """
    valid_categories = ["fabric_mill", "trim_vendor", "dye_house"]
    return category in valid_categories
