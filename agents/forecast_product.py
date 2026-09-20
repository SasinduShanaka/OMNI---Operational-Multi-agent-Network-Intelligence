"""Conservative product-name resolution for natural-language forecast requests."""
import re
import unicodedata

REQUEST_WORDS = set("""a an the please can could would you i me we our my us want need
give show tell say get provide share check know help kindly thanks thank
generate calculate estimate forecast forecasts forecasting forcast
fore cast predict prediction predictions predicted demand demands demad sales expected future outlook
for of in on at to from about with is are be will what how much many do does and
next this coming upcoming month months monthly year years period periods
product products item items all every overall total entire catalog catalogue
report reports download export pdf named called only just s""".split())
PLURALS = {"shirts": "shirt", "polos": "polo", "hoodies": "hoodie",
           "jackets": "jacket", "trousers": "trouser",
           "tshirts": "tshirt", "tee": "tshirt", "tees": "tshirt",
           "tops": "top", "pants": "pant", "sports": "sport",
           "womens": "women", "woman": "women", "gray": "grey"}


def tokens(text):
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"['\u2019]s\b", "", text)
    text = re.sub(r"\bt[\s-]*shirts?\b", "tshirt", text)
    words = {PLURALS.get(word, word) for word in re.findall(r"[a-z0-9]+", text)}
    # 'Polo shirt' and 'polo' describe the same garment, without dropping colors.
    if "polo" in words:
        words.discard("shirt")
    return words


def resolve_forecast_product(request, products):
    skus = list(dict.fromkeys(re.findall(r"\bGAR-\d{3}\b", request.upper())))
    if len(skus) == 1:
        return {"status": "matched", "sku": skus[0]}
    if len(skus) > 1:
        return {"status": "ambiguous", "message": "Please choose one product code, or explicitly ask for all products."}

    terms = tokens(request) - REQUEST_WORDS
    if not terms:
        if re.search(r"\b(all|every|entire|overall|total)\b", request, re.IGNORECASE):
            return {"status": "all"}
        return {"status": "needs_information", "message": "Which product should I forecast? Give its name or code (for example Black Polo or GAR-001), or ask for all products."}

    matches = {product["sku"]: product for product in products
               if terms.issubset(tokens(product.get("product_name") or ""))}
    if len(matches) == 1:
        return {"status": "matched", "sku": next(iter(matches))}
    if matches:
        choices = ", ".join(f"{item['product_name']} ({item['sku']})" for item in matches.values())
        return {"status": "ambiguous", "message": f"That name matches more than one product: {choices}. Please specify the full product name or code."}
    return {"status": "not_found", "message": "I could not find a unique forecast product matching that name. Please provide its full product name or code (for example GAR-001). I have not forecast other products."}
