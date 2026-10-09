"""Offline unit tests for tool input validation and safe routing configuration."""
from __future__ import annotations

import unittest
from pydantic import ValidationError

from .schemas import validate_tool_arguments, TOOL_ARGUMENT_MODELS
from .tools import AVAILABLE_TOOLS
from .agent import TOOL_SPECS


class ToolSchemaTests(unittest.TestCase):
    def test_tool_registry_and_schema_names_match(self):
        schema_names = {item["function"]["name"] for item in TOOL_SPECS}
        self.assertEqual(schema_names, set(AVAILABLE_TOOLS))
        self.assertEqual(set(TOOL_ARGUMENT_MODELS), set(AVAILABLE_TOOLS))

    def test_marketing_date_arguments_validate(self):
        result = validate_tool_arguments(
            "get_website_performance",
            {"start_date": "2026-09-01", "end_date": "2026-09-30", "tenant_id": "TENANT001"},
        )
        self.assertEqual(result["start_date"], "2026-09-01")
        self.assertEqual(result["end_date"], "2026-09-30")
        self.assertEqual(result["tenant_id"], "TENANT001")

    def test_bad_date_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_tool_arguments(
                "get_website_performance",
                {"start_date": "September", "end_date": "2026-09-30"},
            )

    def test_partial_period_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_tool_arguments("get_marketing_funnel", {"start_date": "2026-09-01"})

    def test_invalid_attribution_model_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_tool_arguments("get_attribution_performance", {"model_type": "random_model"})

    def test_historical_year_is_bounded(self):
        with self.assertRaises(ValidationError):
            validate_tool_arguments("get_historical_booking_performance", {"year": 2026})

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool_arguments("run_arbitrary_sql", {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
