"""Domain-aware routing for contextual knowledge, never live operational data."""


DOMAIN_CORPORA = {
    "production_sop": "production_sops",
    "market_context": "market_context",
}

UNINDEXED_DOMAINS = {"inventory_policy", "forecast_documentation", "operations_policy",
                     "supplier_contract"}


def search_context(query: str, domain: str, k: int = 3) -> dict:
    """Search the matching indexed corpus or state that no such index exists."""
    corpus = DOMAIN_CORPORA.get(domain)
    if corpus is None:
        return {"status": "unavailable", "domain": domain, "passages": [],
                "message": "No indexed knowledge corpus exists for this domain; use verified tools or manual review."}
    from knowledge.retriever import search
    passages = search(query, corpus, k=k)
    return {"status": "success" if passages else "empty", "domain": domain,
            "corpus": corpus, "passages": passages,
            "evidence_type": "contextual_document"}
