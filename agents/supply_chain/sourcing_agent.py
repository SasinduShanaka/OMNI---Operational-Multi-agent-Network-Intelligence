"""
sourcing_agent.py — Agent 1: Sourcing & RAG Compliance
Searches the ERP for suppliers via MCP, then checks each one for
ethical/organic compliance using the local ChromaDB vector store.
"""

import asyncio
import os
import sys

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAG_DIR  = os.path.join(BASE_DIR, "knowledge", "supply_chain", "rag")
MCP_DIR  = os.path.join(BASE_DIR, "backend", "mcp", "supply_chain")

sys.path.insert(0, RAG_DIR)
sys.path.insert(0, MCP_DIR)

ERP_SERVER = os.path.join(MCP_DIR, "erp_server.py")


def select_best_supplier(suppliers: list[dict]) -> dict | None:
    """Rank documented suppliers without using country as a decision factor."""
    eligible = [supplier for supplier in suppliers
                if isinstance(supplier.get("rating"), (int, float))
                and isinstance(supplier.get("lead_time_days"), (int, float))]
    if not eligible:
        return None
    return max(eligible, key=lambda supplier: (supplier["rating"], -supplier["lead_time_days"],
                                                -supplier["supplier_id"]))


# ------------------------------------------------------------------
# Agent 1 — Main function
# ------------------------------------------------------------------

async def run_sourcing_agent(
    material_type: str,
    requirement_id: int,
    compliance_keywords: list[str] | None = None,
    targeted_supplier: str | None = None,
) -> dict | None:
    """
    Find the best compliant supplier for a given material type.

    Scenario A (targeted): if targeted_supplier is set, skip DB search —
    look that supplier up directly and run a RAG compliance check on them only.

    Scenario B (autonomous): search ERP for all suppliers of the material_type,
    run RAG compliance check on each, and return the highest-rated compliant one.

    Args:
        material_type:       Category to search (e.g. 'fabric_mill').
        requirement_id:      ID from production_plan table.
        compliance_keywords: Keywords that MUST appear in the supplier's
                             PDF contract (e.g. ['Organic Cotton', 'Child-Labor Free']).
        targeted_supplier:   (Scenario A) Specific supplier name chosen by the user.

    Returns:
        dict with supplier_id, supplier_name, compliance_proof, rating
        or None if no compliant supplier is found.
    """
    from fastmcp import Client
    from knowledge.supply_chain.rag.chroma_setup import check_supplier_compliance

    if compliance_keywords is None:
        compliance_keywords = ["Organic Cotton", "Child-Labor Free"]

    print(f"\n[Agent 1 - Sourcing] Mode: {'TARGETED -> ' + targeted_supplier if targeted_supplier else 'AUTONOMOUS'}")
    print(f"  Material type: {material_type}")
    print(f"  Compliance requirements: {compliance_keywords}")

    # ------------------------------------------------------------------
    # Step 1: Get supplier list
    # ------------------------------------------------------------------
    try:
        async with Client(ERP_SERVER) as erp:
            result = await erp.call_tool(
                "search_suppliers",
                {"material_type": material_type}
            )

        all_suppliers = result.data if hasattr(result, "data") else result
        if isinstance(all_suppliers, dict) and "result" in all_suppliers:
            all_suppliers = all_suppliers["result"]
    except Exception as error:
        print(f"  [Agent 1] ERP MCP unavailable: {error}")
        raise RuntimeError("Supplier lookup is unavailable. Check the ERP MCP server.") from error

    if not all_suppliers:
        print(f"  [Agent 1] No suppliers found for '{material_type}'.")
        return None

    # Scenario A: filter to only the named supplier
    if targeted_supplier:
        suppliers = [
            s for s in all_suppliers
            if targeted_supplier.lower() in s.get("name", "").lower()
        ]
        if not suppliers:
            print(f"  [Agent 1] Named supplier '{targeted_supplier}' not found in ERP.")
            return None
    else:
        suppliers = all_suppliers

    # ------------------------------------------------------------------
    # Step 2: RAG compliance check on each candidate
    # ------------------------------------------------------------------

    # Skip RAG entirely if no compliance keywords provided — saves ~60s
    if not compliance_keywords:
        print("  [Agent 1] No compliance keywords required — skipping RAG check.")
        best = select_best_supplier(suppliers)
        if best is None:
            return None
        print(f"\n  [Agent 1] Best supplier (no compliance filter): {best['name']} (rating={best.get('rating', 0)})")
        return {
            "supplier_id":      best["supplier_id"],
            "supplier_name":    best["name"],
            "country":          best.get("country", ""),
            "lead_time_days":   best.get("lead_time_days", 21),
            "rating":           best.get("rating", 0),
            "requirement_id":   requirement_id,
            "compliance_proof": "No compliance check required.",
            "selection_reason": "Highest available supplier rating; shortest lead time breaks ties. Compliance was not requested.",
        }

    print(f"  Checking {len(suppliers)} supplier(s) against PDF contracts via RAG...")
    compliant_suppliers = []

    for s in suppliers:
        name = s.get("name", "Unknown")
        print(f"  Checking compliance for: {name}")

        try:
            check = check_supplier_compliance(name, compliance_keywords)
            if check["compliant"]:
                print(f"    COMPLIANT - matched: {check['matched_keywords']}")
                compliant_suppliers.append({
                    **s,
                    "compliance_proof": check["proof_excerpt"],
                    "matched_keywords": check["matched_keywords"],
                })
            else:
                print(f"    NON-COMPLIANT - missing: {check['missing_keywords']}")
        except Exception as e:
            print(f"    [Warning] RAG unavailable for {name}: {e}")
            # Missing or inaccessible evidence must never be treated as compliance.
            raise RuntimeError(
                "Supplier compliance is unverified. Restore the contract index and request human review."
            ) from e

    # ------------------------------------------------------------------
    # Step 3: Return best compliant supplier (highest rating)
    # ------------------------------------------------------------------
    if not compliant_suppliers:
        print("\n  [Agent 1] No compliant suppliers found. Cannot proceed.")
        return None

    best = select_best_supplier(compliant_suppliers)
    if best is None:
        print("  Supplier ratings or lead times are incomplete. Human review is required.")
        return None

    print(f"\n  [Agent 1] Best compliant supplier: {best['name']} (rating={best['rating']})")
    print(f"  Compliance proof: \"{best['compliance_proof'][:120]}...\"")

    return {
        "supplier_id":      best["supplier_id"],
        "supplier_name":    best["name"],
        "country":          best.get("country", ""),
        "lead_time_days":   best.get("lead_time_days", 21),
        "rating":           best.get("rating", 0),
        "requirement_id":   requirement_id,
        "compliance_proof": best["compliance_proof"],
        "selection_reason": "Verified contract terms, then highest available supplier rating; shortest lead time breaks ties. Country was not used.",
    }


if __name__ == "__main__":
    result = asyncio.run(
        run_sourcing_agent(
            material_type="fabric_mill",
            requirement_id=2,
            compliance_keywords=["Organic Cotton", "Child-Labor Free"]
        )
    )
    print("\n[Agent 1 Result]:", result)
