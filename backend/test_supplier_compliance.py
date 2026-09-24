"""The sourcing agent must not draft orders from unverified contracts."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agents.supply_chain.sourcing_agent import run_sourcing_agent, select_best_supplier


class FakeErpClient:
    def __init__(self, suppliers):
        self.suppliers = suppliers

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def call_tool(self, *_):
        return SimpleNamespace(data=self.suppliers)


class SupplierComplianceTests(unittest.TestCase):
    supplier = [{"supplier_id": 4, "name": "EcoWeave Bangladesh", "country": "Bangladesh",
                 "rating": 4.5, "lead_time_days": 12}]

    def test_country_does_not_change_supplier_ranking(self):
        first = {"supplier_id": 1, "country": "Bangladesh", "rating": 4.8, "lead_time_days": 10}
        second = {"supplier_id": 2, "country": "Sri Lanka", "rating": 4.2, "lead_time_days": 8}
        self.assertEqual(select_best_supplier([first, second])["supplier_id"], 1)
        self.assertEqual(select_best_supplier([{**first, "country": "Sri Lanka"},
                                               {**second, "country": "Bangladesh"}])["supplier_id"], 1)
        self.assertIsNone(select_best_supplier([{**first, "rating": None}]))

    def run_source(self, check):
        with patch("fastmcp.Client", return_value=FakeErpClient(self.supplier)), \
             patch("knowledge.supply_chain.rag.chroma_setup.check_supplier_compliance", side_effect=check):
            return asyncio.run(run_sourcing_agent("fabric_mill", 2, ["Organic Cotton"]))

    def test_verified_supplier_has_evidence_and_selection_reason(self):
        result = self.run_source(lambda *_: {"compliant": True, "matched_keywords": ["Organic Cotton"],
                                             "proof_excerpt": "Organic Cotton certified."})
        self.assertEqual(result["supplier_id"], 4)
        self.assertIn("Organic Cotton", result["compliance_proof"])
        self.assertIn("rating", result["selection_reason"])

    def test_missing_compliance_terms_cannot_be_selected(self):
        result = self.run_source(lambda *_: {"compliant": False, "missing_keywords": ["Organic Cotton"],
                                             "proof_excerpt": ""})
        self.assertIsNone(result)

    def test_unavailable_index_blocks_sourcing(self):
        with self.assertRaisesRegex(RuntimeError, "compliance is unverified"):
            self.run_source(lambda *_: (_ for _ in ()).throw(RuntimeError("collection missing")))


if __name__ == "__main__":
    unittest.main()
