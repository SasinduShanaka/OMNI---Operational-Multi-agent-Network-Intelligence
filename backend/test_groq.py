"""Offline LLM readiness check; no provider call during automated tests."""

import unittest
from unittest.mock import patch

from backend import readiness


class LanguageModelConfigurationTests(unittest.TestCase):
    def test_missing_key_is_reported_without_contacting_provider(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}), \
             patch("backend.supply_chain.email_service.email_configuration_status", return_value={"status": "needs_attention"}):
            result = readiness.system_readiness()
        model = next(check for check in result["checks"] if check["name"] == "Language model")
        self.assertEqual(model["status"], "needs_attention")


if __name__ == "__main__":
    unittest.main()
