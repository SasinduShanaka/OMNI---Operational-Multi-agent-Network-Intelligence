"""Conservative product-name resolution for natural-language forecast requests."""
import re
import unicodedata

REQUEST_WORDS = set("""a an the please can could would you i me we our my us want need
give show tell say get provide share check know help kindly thanks thank
generate calculate estimate forecast forecasts forecasting forcast
fore cast predict prediction predictions predicted demand demands demad sales expected future outlook
for of in on at to from about with is are be will what how much many do does and over during ahead
next this coming upcoming month months monthly year years period periods
product products item items all every overall total entire catalog catalogue
report reports download export pdf named called only just s
explain explanation trend trends confidence key driver drivers
assumption assumptions reason reasons accuracy accurate reliability reliable
model models method methodology details detail insight insights summary
increase increases increased impact effects fabric inventory capacity production scenario what if by""".split())
PLURALS = {"shirts": "shirt", "polos": "polo", "hoodies": "hoodie",
           "jackets": "jacket", "trousers": "trouser",
           "tshirts": "tshirt", "tee": "tshirt", "tees": "tshirt",
           "tops": "top", "pants": "pant", "sports": "sport",
           "womens": "women", "woman": "women", "gray": "grey"}


def tokens(text):
    text = unicodedata.normalize("NFKC", text)
    # Users commonly type catalog names as ClassicBlackPolo or
    # whiteCottonTShirt. Split those word boundaries before lowercasing.
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    text = text.lower()
    text = re.sub(r"['\u2019]s\b", "", text)
    text = re.sub(r"\bt[\s-]*shirts?\b", "tshirt", text)
    words = {PLURALS.get(word, word) for word in re.findall(r"[a-z0-9]+", text)}
    # 'Polo shirt' and 'polo' describe the same garment, without dropping colors.
    if "polo" in words:
        words.discard("shirt")
    return words


def product_tokens(name):
    words = tokens(name)
    # Expand catalog categories only: a shirt query includes these subtypes,
    # while a specific polo/T-shirt query still requires that subtype.
    if words & {"polo", "tshirt"}:
        words.add("shirt")
    return words


def resolve_forecast_product(request, products):
    if re.search(r'\bactual\b', request, re.IGNORECASE) and re.search(r'\b(compare|comparison|predicted|forecast|vs|versus)\b', request, re.IGNORECASE):
        if not re.search(r'\b(last|previous)\s+month\b', request, re.IGNORECASE):
            return {'status': 'needs_information', 'message': 'For a saved forecast comparison, specify last month and a product name or code.'}
        if re.search(r'\b(all|every|entire|overall|total)\s+(?:products?|items?|catalog(?:ue)?)\b', request, re.IGNORECASE):
            return {'status': 'all', 'mode': 'comparison'}
        cleaned = re.sub(r'\b(compare|comparison|actual|against|versus|vs|last|previous)\b', ' ', request, flags=re.IGNORECASE)
        selection = _resolve_product(cleaned, products)
        selection['mode'] = 'comparison'
        if selection['status'] == 'needs_information':
            selection['message'] = 'Which products should I compare? Select a product below or choose All products.'
        return selection
    numbers = dict(zip('one two three four five six seven eight nine ten eleven twelve'.split(), range(1, 13)))
    # A quarter is a three-month forecast horizon. Normalizing it here keeps
    # the same validation and period handling used for explicit month requests.
    request = re.sub(r'\b(next|this|coming|upcoming)\s+quarter\b', '3 months', request, flags=re.IGNORECASE)
    # Remove only a duration expression, preserving numbers in product names/codes.
    pattern = r'(?<!\w)([+-]?\d+(?:\.\d+)?|\w+)\s*[- ]\s*months?\b'
    horizons = []
    def duration(match):
        word = match[1].lower()
        if word in ('next', 'this', 'coming', 'upcoming'):
            return match[0]
        value = int(word) if word.isdigit() else numbers.get(word)
        if value is None or not 1 <= value <= 12:
            raise ValueError('Please specify a forecast horizon from 1 to 12 months.')
        horizons.append(value)
        return ' '
    try:
        cleaned = re.sub(pattern, duration, request, flags=re.IGNORECASE)
    except ValueError as error:
        return {'status': 'invalid_horizon', 'message': str(error)}
    if len(set(horizons)) > 1:
        return {'status': 'invalid_horizon', 'message': 'Please choose one forecast horizon, from 1 to 12 months.'}
    result = _resolve_product(cleaned, products)
    if horizons and horizons[0] != 1:
        result['periods'] = horizons[0]
    return result


def _resolve_product(request, products):
    # Accept the displayed code plus common input variants: gar001, GAR 001,
    # GAR_001 and mixed case. Internally all codes use GAR-###.
    skus = list(dict.fromkeys(
        f"GAR-{number}" for number in re.findall(r"\bgar[\s_-]*(\d{3})\b", request, re.IGNORECASE)
    ))
    if len(skus) == 1:
        return {"status": "matched", "sku": skus[0]}
    if len(skus) > 1:
        return {"status": "ambiguous", "message": "Please choose one product code, or explicitly ask for all products."}

    # Ranking questions are catalogue-wide analyses even when the user does
    # not explicitly say "all products".
    asks_for_ranking = re.search(
        r'\b(which|what|top)\b.*\b(products?|items?)\b.*\b(highest|lowest|top|most|least|growth)\b'
        r'|\b(highest|lowest|top|most|least)\b.*\b(products?|items?)\b'
        r'|\b(highest|lowest|top|most|least)\b.*\b(forecast(?:ed)?|demand)\b.*\b(growth|increase|decrease)\b',
        request,
        re.IGNORECASE,
    )
    if asks_for_ranking:
        if re.search(r'\b(growth|increase|decrease)\b', request, re.IGNORECASE):
            return {"status": "all", "mode": "growth_ranking"}
        has_highest = re.search(r'\b(highest|top|most)\b', request, re.IGNORECASE)
        has_lowest = re.search(r'\b(lowest|least)\b', request, re.IGNORECASE)
        return {
            "status": "all",
            "mode": "demand_ranking",
            "ranking": "both" if has_highest and has_lowest else "lowest" if has_lowest else "highest",
        }

    # "All products" is decisive even if the user appends an explanatory
    # question or a request for details after it.
    if re.search(r'\b(all|every|entire|overall|total)\s+(?:products?|items?|catalog(?:ue)?)\b', request, re.IGNORECASE):
        return {"status": "all"}

    terms = {term for term in tokens(request) - REQUEST_WORDS if not term.isdigit()}
    if not terms:
        if re.search(r"\b(all|every|entire|overall|total)\b", request, re.IGNORECASE):
            return {"status": "all"}
        return {"status": "needs_information", "message": "Which product should I forecast? Select a product below, or ask for all products.", "products": products}

    matches = {product["sku"]: product for product in products
               if terms.issubset(product_tokens(product.get("product_name") or ""))}
    if len(matches) == 1:
        return {"status": "matched", "sku": next(iter(matches))}
    if matches:
        choices = ", ".join(f"{item['product_name']} ({item['sku']})" for item in matches.values())
        return {"status": "ambiguous", "message": f"That name matches more than one product: {choices}. Select the product you want to forecast.", "products": list(matches.values())}
    return {"status": "not_found", "message": "I could not find a unique forecast product matching that name. Please provide its full product name or code (for example GAR-001). I have not forecast other products."}
