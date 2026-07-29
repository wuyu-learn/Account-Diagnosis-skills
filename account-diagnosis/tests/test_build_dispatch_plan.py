from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_dispatch_plan.py"
)
SPEC = importlib.util.spec_from_file_location("build_dispatch_plan", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

DispatchError = MODULE.DispatchError
build_dispatch_plan = MODULE.build_dispatch_plan


class BuildDispatchPlanTests(unittest.TestCase):
    def test_builds_calls_for_all_account_intents_in_route_order(self) -> None:
        intents = [
            "watchlist_valuation",
            "account_overview",
            "holding_structure",
            "return_performance",
            "return_attribution",
        ]
        payload = {
            "accountIntentResult": {
                "accountScenes": [
                    {
                        "intent": intent,
                        "weight": 1 - index * 0.1,
                        "subQuery": f"问题 {index}",
                    }
                    for index, intent in enumerate(intents)
                ],
                "primaryAccountIntent": "watchlist_valuation",
                "isMultiAccountIntent": True,
            },
            "entities": {"fund_codes": ["000001"]},
        }

        result = build_dispatch_plan(payload)

        self.assertEqual(
            [call["input"]["intent"] for call in result["calls"]], intents
        )
        self.assertEqual(
            [call["order"] for call in result["calls"]], list(range(len(intents)))
        )
        self.assertEqual(result["primaryAccountIntent"], "watchlist_valuation")
        self.assertTrue(result["isMultiAccountIntent"])
        self.assertTrue(
            all("requestContext" not in call["input"] for call in result["calls"])
        )
        self.assertEqual(
            result["calls"][0]["input"]["entities"],
            {"fund_codes": ["000001"]},
        )

    def test_rejects_unknown_intent(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [
                    {
                        "intent": "unknown",
                        "weight": 1,
                        "subQuery": "未知问题",
                    }
                ],
                "primaryAccountIntent": "unknown",
                "isMultiAccountIntent": False,
            }
        }

        with self.assertRaisesRegex(DispatchError, "unsupported intent"):
            build_dispatch_plan(payload)

    def test_primary_intent_must_match_first_scene(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [
                    {
                        "intent": "holding_structure",
                        "weight": 0.8,
                        "subQuery": "我持有哪些产品",
                    }
                ],
                "primaryAccountIntent": "account_overview",
                "isMultiAccountIntent": False,
            }
        }

        with self.assertRaisesRegex(DispatchError, "must equal the first"):
            build_dispatch_plan(payload)

    def test_empty_route_produces_empty_plan(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [],
                "primaryAccountIntent": None,
                "isMultiAccountIntent": False,
            }
        }

        result = build_dispatch_plan(payload)

        self.assertEqual(result["calls"], [])
        self.assertIsNone(result["primaryAccountIntent"])
        self.assertFalse(result["isMultiAccountIntent"])

    def test_rejects_request_context_in_dispatch_input(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [],
                "primaryAccountIntent": None,
                "isMultiAccountIntent": False,
            },
            "requestContext": {"custNo": "must-not-enter-card-routing"},
        }

        with self.assertRaisesRegex(DispatchError, "unsupported fields"):
            build_dispatch_plan(payload)

    def test_filters_unknown_and_identity_like_entity_fields(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [
                    {
                        "intent": "account_overview",
                        "weight": 1,
                        "subQuery": "这只基金怎么样",
                    }
                ],
                "primaryAccountIntent": "account_overview",
                "isMultiAccountIntent": False,
            },
            "entities": {
                "fund_names": ["示例基金"],
                "custNo": "must-not-leak",
                "sessionId": "must-not-leak",
                "unknown": ["must-not-leak"],
            },
        }

        result = build_dispatch_plan(payload)

        self.assertEqual(
            result["calls"][0]["input"]["entities"],
            {"fund_names": ["示例基金"]},
        )

    def test_rejects_object_nested_in_allowed_entity_array(self) -> None:
        payload = {
            "accountIntentResult": {
                "accountScenes": [],
                "primaryAccountIntent": None,
                "isMultiAccountIntent": False,
            },
            "entities": {
                "fund_names": [
                    {"custNo": "must-not-leak", "sessionId": "must-not-leak"}
                ]
            },
        }

        with self.assertRaisesRegex(DispatchError, "must be a non-empty string"):
            build_dispatch_plan(payload)


if __name__ == "__main__":
    unittest.main()
