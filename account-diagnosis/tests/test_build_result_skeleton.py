from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "build_result_skeleton.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("build_result_skeleton", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SkeletonError = MODULE.SkeletonError
build_result_skeleton = MODULE.build_result_skeleton


def plan(
    card_plans: list[dict],
    *,
    complexity: str = "simple",
    primary_intent: str = "return_performance",
    account_scenes: list[dict] | None = None,
) -> dict:
    scenes = account_scenes or [
        {
            "intent": primary_intent,
            "weight": 0.95,
            "subQuery": "示例问题",
        }
    ]
    return {
        "taskComplexity": complexity,
        "complexityReason": "测试复杂度原因",
        "primaryAccountIntent": primary_intent,
        "accountScenes": scenes,
        "cardPlans": card_plans,
    }


class BuildResultSkeletonTests(unittest.TestCase):
    def test_builds_fixed_sections_cards_and_business_order(self) -> None:
        result = build_result_skeleton(
            plan(
                [
                    {"cardId": "ACC-15", "params": {"dateType": "Y0"}},
                    {"cardId": "ACC-13-A", "params": {}},
                    {"cardId": "ACC-11", "params": {}},
                ],
                complexity="complex",
                primary_intent="holding_structure",
                account_scenes=[
                    {
                        "intent": "holding_structure",
                        "weight": 0.95,
                        "subQuery": "分析持仓和收益来源",
                    },
                    {
                        "intent": "return_performance",
                        "weight": 0.9,
                        "subQuery": "收益表现",
                    },
                    {
                        "intent": "return_attribution",
                        "weight": 0.85,
                        "subQuery": "收益来源",
                    },
                ],
            )
        )

        self.assertEqual(result["taskComplexity"], "complex")
        self.assertEqual(
            [item["card"]["cardId"] for item in result["businessItems"]],
            ["ACC-11", "ACC-13-A", "ACC-15"],
        )
        self.assertEqual(
            [item["section"]["type"] for item in result["businessItems"]],
            ["holding_structure", "return_performance", "return_attribution"],
        )
        self.assertTrue(
            all(
                item["card"]["dataMode"] == "deferred"
                for item in result["businessItems"]
            )
        )
        self.assertEqual(
            result["businessItems"][-1]["card"]["data"], {"dateType": "Y0"}
        )

    def test_accepts_all_account_diagnosis_cards_and_watchlist_separately(self) -> None:
        card_ids = [card_id for card_id in MODULE.CARD_SPECS if card_id != "ACC-18"]
        card_plans = [
            {
                "cardId": card_id,
                "params": {"dateType": "Y1"} if card_id == "ACC-15" else {},
            }
            for card_id in card_ids
        ]
        result = build_result_skeleton(
            plan(
                card_plans,
                primary_intent="account_overview",
                account_scenes=[
                    {
                        "intent": "account_overview",
                        "weight": 0.95,
                        "subQuery": "账户总览",
                    },
                    {
                        "intent": "holding_structure",
                        "weight": 0.9,
                        "subQuery": "持仓结构",
                    },
                    {
                        "intent": "return_performance",
                        "weight": 0.85,
                        "subQuery": "收益表现",
                    },
                    {
                        "intent": "return_attribution",
                        "weight": 0.8,
                        "subQuery": "收益归因",
                    },
                ],
            )
        )
        self.assertEqual(len(result["businessItems"]), 17)

        watchlist = build_result_skeleton(
            plan(
                [{"cardId": "ACC-18", "params": {}}],
                primary_intent="watchlist_valuation",
            )
        )
        self.assertEqual(
            watchlist["businessItems"][0]["section"]["type"],
            "watchlist_valuation",
        )

    def test_maps_only_allowed_business_params(self) -> None:
        result = build_result_skeleton(
            plan(
                [{"cardId": "ACC-19", "params": {"productId": "P001"}}],
                primary_intent="account_overview",
            )
        )
        self.assertEqual(
            result["businessItems"][0]["card"]["data"], {"productId": "P001"}
        )

    def test_rejects_llm_owned_card_structure_fields(self) -> None:
        payload = plan(
            [
                {
                    "cardId": "ACC-13-A",
                    "params": {},
                    "dataMode": "deferred",
                }
            ]
        )
        with self.assertRaisesRegex(SkeletonError, "unsupported fields"):
            build_result_skeleton(payload)

    def test_rejects_missing_or_invalid_attribution_date_type(self) -> None:
        missing = plan(
            [{"cardId": "ACC-15", "params": {}}],
            primary_intent="return_attribution",
        )
        with self.assertRaisesRegex(SkeletonError, "missing required"):
            build_result_skeleton(missing)

        invalid = plan(
            [{"cardId": "ACC-15", "params": {"dateType": "YEAR"}}],
            primary_intent="return_attribution",
        )
        with self.assertRaisesRegex(SkeletonError, "dateType is unsupported"):
            build_result_skeleton(invalid)

    def test_rejects_identity_unknown_params_and_duplicate_cards(self) -> None:
        identity = plan(
            [{"cardId": "ACC-19", "params": {"custNo": "C1"}}],
            primary_intent="account_overview",
        )
        with self.assertRaisesRegex(SkeletonError, "identity param"):
            build_result_skeleton(identity)

        unknown = plan(
            [{"cardId": "ACC-13-A", "params": {"period": "Y1"}}]
        )
        with self.assertRaisesRegex(SkeletonError, "must be empty"):
            build_result_skeleton(unknown)

        duplicate = plan(
            [
                {"cardId": "ACC-13-A", "params": {}},
                {"cardId": "ACC-13-A", "params": {}},
            ]
        )
        with self.assertRaisesRegex(SkeletonError, "duplicate cardId"):
            build_result_skeleton(duplicate)

    def test_rejects_mixed_response_classes(self) -> None:
        payload = plan(
            [
                {"cardId": "ACC-01", "params": {}},
                {"cardId": "ACC-18", "params": {}},
            ],
            primary_intent="account_overview",
        )
        with self.assertRaisesRegex(SkeletonError, "must not be mixed"):
            build_result_skeleton(payload)

    def test_rejects_complex_watchlist_task(self) -> None:
        payload = plan(
            [{"cardId": "ACC-18", "params": {}}],
            complexity="complex",
            primary_intent="watchlist_valuation",
        )
        with self.assertRaisesRegex(SkeletonError, "only supports simple"):
            build_result_skeleton(payload)

    def test_rejects_primary_intent_without_matching_card(self) -> None:
        payload = plan(
            [{"cardId": "ACC-13-A", "params": {}}],
            primary_intent="holding_structure",
        )
        with self.assertRaisesRegex(SkeletonError, "must match"):
            build_result_skeleton(payload)

    def test_rejects_undeclared_card_intent_and_unsorted_scenes(self) -> None:
        undeclared = plan(
            [
                {"cardId": "ACC-13-A", "params": {}},
                {"cardId": "ACC-15", "params": {"dateType": "Y0"}},
            ]
        )
        with self.assertRaisesRegex(SkeletonError, "declared accountScenes"):
            build_result_skeleton(undeclared)

        unsorted = plan(
            [{"cardId": "ACC-13-A", "params": {}}],
            account_scenes=[
                {
                    "intent": "return_performance",
                    "weight": 0.6,
                    "subQuery": "收益表现",
                },
                {
                    "intent": "return_attribution",
                    "weight": 0.8,
                    "subQuery": "收益来源",
                },
            ],
        )
        with self.assertRaisesRegex(SkeletonError, "weight descending"):
            build_result_skeleton(unsorted)

    def test_same_card_combination_supports_simple_and_complex(self) -> None:
        card_plans = [
            {"cardId": "ACC-11", "params": {}},
            {"cardId": "ACC-15", "params": {"dateType": "N"}},
        ]
        scenes = [
            {
                "intent": "holding_structure",
                "weight": 0.95,
                "subQuery": "查看持仓",
            },
            {
                "intent": "return_attribution",
                "weight": 0.9,
                "subQuery": "查看拖累",
            },
        ]

        simple = build_result_skeleton(
            plan(
                card_plans,
                complexity="simple",
                primary_intent="holding_structure",
                account_scenes=scenes,
            )
        )
        complex_result = build_result_skeleton(
            plan(
                card_plans,
                complexity="complex",
                primary_intent="holding_structure",
                account_scenes=scenes,
            )
        )

        self.assertEqual(simple["businessItems"], complex_result["businessItems"])


if __name__ == "__main__":
    unittest.main()
