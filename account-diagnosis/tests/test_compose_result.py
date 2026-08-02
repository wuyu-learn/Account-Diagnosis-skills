from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "compose_result.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("compose_result", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CompositionError = MODULE.CompositionError
compose_result = MODULE.compose_result
CARD_SPECS = MODULE.CARD_SPECS


def business_item(card_id: str, data: dict | None = None) -> dict:
    spec = CARD_SPECS[card_id]
    return {
        "section": {
            "type": spec["sectionType"],
            "title": spec["title"],
            "narrative": spec["narrative"],
        },
        "card": {
            "cardId": card_id,
            "dataMode": "deferred",
            "data": data if data is not None else {},
        },
    }


def payload_for(
    business_items: list[dict],
    intent: str,
    *,
    complexity: str = "simple",
    include_conclusion: bool | None = None,
    follow_up: list[str] | None = None,
) -> dict:
    payload = {
        "scene": "问账户",
        "taskComplexity": complexity,
        "primaryAccountIntent": intent,
        "businessItems": business_items,
        "summary": {"title": "回答摘要", "narrative": "基于真实数据的回答。"},
        "followUp": follow_up or [],
    }
    should_include = complexity == "complex" if include_conclusion is None else include_conclusion
    if should_include:
        payload["conclusion"] = {
            "title": "综合结论",
            "narrative": "基于同一批证据形成的综合判断。",
        }
    return payload


class ComposeResultTests(unittest.TestCase):
    def test_simple_task_has_summary_and_no_conclusion(self) -> None:
        result = compose_result(
            payload_for([business_item("ACC-13-A")], "return_performance")
        )
        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "return_performance"],
        )
        self.assertNotIn("taskComplexity", result)
        self.assertEqual(
            set(result),
            {"version", "meta", "sections", "cards", "risk_warning", "followUp"},
        )

    def test_complex_task_requires_and_emits_one_conclusion(self) -> None:
        result = compose_result(
            payload_for(
                [
                    business_item("ACC-11"),
                    business_item("ACC-13-A"),
                    business_item("ACC-15", {"dateType": "Y0"}),
                ],
                "holding_structure",
                complexity="complex",
            )
        )
        self.assertEqual(result["sections"][0]["type"], "summary")
        self.assertEqual(result["sections"][-1]["type"], "conclusion")
        self.assertEqual(
            [section["type"] for section in result["sections"]].count("conclusion"),
            1,
        )

    def test_rejects_simple_conclusion_and_complex_missing_conclusion(self) -> None:
        simple = payload_for(
            [business_item("ACC-13-A")],
            "return_performance",
            include_conclusion=True,
        )
        with self.assertRaisesRegex(CompositionError, "must not include"):
            compose_result(simple)

        complex_payload = payload_for(
            [business_item("ACC-13-A")],
            "return_performance",
            complexity="complex",
            include_conclusion=False,
        )
        with self.assertRaisesRegex(CompositionError, "requires conclusion"):
            compose_result(complex_payload)

    def test_accepts_all_account_diagnosis_cards_in_fixed_order(self) -> None:
        ordered_card_ids = sorted(
            (card_id for card_id in CARD_SPECS if card_id != "ACC-18"),
            key=lambda card_id: MODULE.SECTION_ORDER[
                CARD_SPECS[card_id]["sectionType"]
            ],
        )
        items = [
            business_item(
                card_id, {"dateType": "Y1"} if card_id == "ACC-15" else None
            )
            for card_id in ordered_card_ids
        ]
        result = compose_result(payload_for(items, "account_overview"))
        self.assertEqual(len(result["cards"]), 17)
        self.assertTrue(
            all(card["dataMode"] == "deferred" for card in result["cards"])
        )

    def test_accepts_simple_watchlist_only(self) -> None:
        result = compose_result(
            payload_for([business_item("ACC-18")], "watchlist_valuation")
        )
        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "watchlist_valuation"],
        )

    def test_rejects_complex_watchlist_and_mixed_response_classes(self) -> None:
        complex_watchlist = payload_for(
            [business_item("ACC-18")],
            "watchlist_valuation",
            complexity="complex",
        )
        with self.assertRaisesRegex(CompositionError, "only supports simple"):
            compose_result(complex_watchlist)

        mixed = payload_for(
            [business_item("ACC-01"), business_item("ACC-18")],
            "account_overview",
        )
        with self.assertRaisesRegex(CompositionError, "must not be mixed"):
            compose_result(mixed)

    def test_deduplicates_and_limits_follow_up(self) -> None:
        result = compose_result(
            payload_for(
                [business_item("ACC-01")],
                "account_overview",
                follow_up=["一", "一", "二", "三", "四"],
            )
        )
        self.assertEqual(result["followUp"], ["一", "二", "三"])

    def test_rejects_tampered_fixed_section_text_and_order(self) -> None:
        tampered = payload_for([business_item("ACC-01")], "account_overview")
        tampered["businessItems"][0]["section"]["title"] = "LLM 改写标题"
        with self.assertRaisesRegex(CompositionError, "fixed card contract"):
            compose_result(tampered)

        wrong_order = payload_for(
            [business_item("ACC-13-A"), business_item("ACC-11")],
            "return_performance",
        )
        with self.assertRaisesRegex(CompositionError, "fixed section order"):
            compose_result(wrong_order)

    def test_rejects_duplicate_unknown_and_wrong_mapping(self) -> None:
        duplicate = payload_for(
            [business_item("ACC-01"), business_item("ACC-01")],
            "account_overview",
        )
        with self.assertRaisesRegex(CompositionError, "duplicate cardId"):
            compose_result(duplicate)

        unknown = payload_for([business_item("ACC-01")], "account_overview")
        unknown["businessItems"][0]["card"]["cardId"] = "ACC-16"
        with self.assertRaisesRegex(CompositionError, "unsupported"):
            compose_result(unknown)

        wrong_mapping = payload_for([business_item("ACC-01")], "account_overview")
        wrong_mapping["businessItems"][0]["section"]["type"] = "holding_structure"
        with self.assertRaisesRegex(CompositionError, "requires section.type"):
            compose_result(wrong_mapping)

    def test_rejects_invalid_card_data(self) -> None:
        default_card = payload_for(
            [business_item("ACC-01", {"amount": "1"})], "account_overview"
        )
        with self.assertRaisesRegex(CompositionError, "must be empty"):
            compose_result(default_card)

        identity = payload_for(
            [business_item("ACC-15", {"dateType": "Y1", "custNo": "C1"})],
            "return_attribution",
        )
        with self.assertRaisesRegex(CompositionError, "identity param"):
            compose_result(identity)

        missing = payload_for(
            [business_item("ACC-15")], "return_attribution"
        )
        with self.assertRaisesRegex(CompositionError, "missing required"):
            compose_result(missing)

        invalid = payload_for(
            [business_item("ACC-15", {"dateType": "YEAR"})],
            "return_attribution",
        )
        with self.assertRaisesRegex(CompositionError, "dateType is unsupported"):
            compose_result(invalid)

    def test_accepts_allowed_optional_card_params(self) -> None:
        result = compose_result(
            payload_for(
                [business_item("ACC-19", {"productId": "P001"})],
                "account_overview",
            )
        )
        self.assertEqual(result["cards"][0]["data"], {"productId": "P001"})

        result = compose_result(
            payload_for(
                [business_item("ACC-03", {"serialNo": "S1", "uri": "U1"})],
                "account_overview",
            )
        )
        self.assertEqual(
            result["cards"][0]["data"], {"serialNo": "S1", "uri": "U1"}
        )

    def test_rejects_final_or_internal_fields_as_input(self) -> None:
        payload = payload_for([business_item("ACC-01")], "account_overview")
        payload["version"] = "2.2"
        payload["originalQuery"] = "不应进入最终编排"
        payload["cardPlans"] = []
        with self.assertRaisesRegex(CompositionError, "unsupported fields"):
            compose_result(payload)

    def test_rejects_primary_intent_not_present_and_wrong_scene(self) -> None:
        mismatch = payload_for(
            [business_item("ACC-01")], "holding_structure"
        )
        with self.assertRaisesRegex(CompositionError, "must match"):
            compose_result(mismatch)

        wrong_scene = payload_for(
            [business_item("ACC-01")], "account_overview"
        )
        wrong_scene["scene"] = "问基金"
        with self.assertRaisesRegex(CompositionError, "scene must be 问账户"):
            compose_result(wrong_scene)

    def test_rejects_llm_extra_section_fields_and_empty_text(self) -> None:
        extra = payload_for([business_item("ACC-01")], "account_overview")
        extra["summary"]["type"] = "summary"
        with self.assertRaisesRegex(CompositionError, "unsupported fields"):
            compose_result(extra)

        empty = copy.deepcopy(extra)
        del empty["summary"]["type"]
        empty["summary"]["narrative"] = ""
        with self.assertRaisesRegex(CompositionError, "must be a non-empty"):
            compose_result(empty)


if __name__ == "__main__":
    unittest.main()
