from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compose_result.py"
SPEC = importlib.util.spec_from_file_location("compose_result", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CompositionError = MODULE.CompositionError
compose_result = MODULE.compose_result


CARD_GROUPS = [
    (
        "account_overview",
        [
            "ACC-01",
            "ACC-02",
            "ACC-03",
            "ACC-04",
            "ACC-05",
            "ACC-06",
            "ACC-07",
            "ACC-08",
            "ACC-09",
            "ACC-10",
            "ACC-19",
        ],
    ),
    ("holding_structure", ["ACC-11", "ACC-12"]),
    ("return_performance", ["ACC-13-A", "ACC-13-B", "ACC-14"]),
    ("return_attribution", ["ACC-15"]),
    ("watchlist_valuation", ["ACC-18"]),
]


def section_item(section_type: str, card_id: str | None = None) -> dict:
    item = {
        "section": {
            "type": section_type,
            "title": f"{section_type} 标题",
            "narrative": f"{section_type} 内容",
        }
    }
    if card_id is not None:
        item["card"] = {
            "cardId": card_id,
            "dataMode": "deferred",
            "data": {},
        }
    return item


def payload_for(
    business_items: list[dict],
    intent: str,
    follow_up: list[str] | None = None,
) -> dict:
    return {
        "scene": "问账户",
        "primaryAccountIntent": intent,
        "items": [
            section_item("summary"),
            *business_items,
            section_item("conclusion"),
        ],
        "followUp": follow_up or [],
    }


class ComposeResultTests(unittest.TestCase):
    def test_accepts_all_18_cards_in_fixed_business_order(self) -> None:
        business_items = [
            section_item(section_type, card_id)
            for section_type, card_ids in CARD_GROUPS
            for card_id in card_ids
        ]

        result = compose_result(payload_for(business_items, "account_overview"))

        self.assertEqual(
            set(result),
            {
                "scene",
                "primaryAccountIntent",
                "sections",
                "cards",
                "followUp",
            },
        )
        self.assertEqual(len(result["cards"]), 18)
        self.assertEqual(
            [card["cardId"] for card in result["cards"]],
            [card_id for _, card_ids in CARD_GROUPS for card_id in card_ids],
        )
        self.assertTrue(
            all(card["dataMode"] == "deferred" for card in result["cards"])
        )
        self.assertTrue(all(card["data"] == {} for card in result["cards"]))
        for section in result["sections"][1:-1]:
            self.assertIn("cardId", section)

    def test_accepts_watchlist_only_template(self) -> None:
        result = compose_result(
            payload_for(
                [section_item("watchlist_valuation", "ACC-18")],
                "watchlist_valuation",
            )
        )

        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "watchlist_valuation", "conclusion"],
        )

    def test_deduplicates_and_limits_follow_up(self) -> None:
        result = compose_result(
            payload_for(
                [section_item("account_overview", "ACC-01")],
                "account_overview",
                ["一", "一", "二", "三", "四"],
            )
        )

        self.assertEqual(result["followUp"], ["一", "二", "三"])

    def test_rejects_inline_and_nonempty_card_data(self) -> None:
        inline = payload_for(
            [section_item("account_overview", "ACC-01")], "account_overview"
        )
        inline["items"][1]["card"]["dataMode"] = "inline"

        with self.assertRaisesRegex(CompositionError, "must be deferred"):
            compose_result(inline)

        populated = payload_for(
            [section_item("account_overview", "ACC-01")], "account_overview"
        )
        populated["items"][1]["card"]["data"] = {"amount": 1}

        with self.assertRaisesRegex(CompositionError, "must be empty"):
            compose_result(populated)

    def test_rejects_unknown_card_and_wrong_section_mapping(self) -> None:
        unknown = payload_for(
            [section_item("return_attribution", "ACC-16")],
            "return_attribution",
        )
        with self.assertRaisesRegex(CompositionError, "unsupported"):
            compose_result(unknown)

        wrong_mapping = payload_for(
            [section_item("account_overview", "ACC-18")],
            "account_overview",
        )
        with self.assertRaisesRegex(CompositionError, "requires section.type"):
            compose_result(wrong_mapping)

    def test_rejects_business_order_violation(self) -> None:
        payload = payload_for(
            [
                section_item("watchlist_valuation", "ACC-18"),
                section_item("account_overview", "ACC-01"),
            ],
            "watchlist_valuation",
        )

        with self.assertRaisesRegex(CompositionError, "fixed section order"):
            compose_result(payload)

    def test_rejects_missing_or_duplicate_boundary_sections(self) -> None:
        missing_summary = payload_for(
            [
                section_item("account_overview", "ACC-01"),
                section_item("account_overview", "ACC-02"),
            ],
            "account_overview",
        )
        missing_summary["items"].pop(0)
        with self.assertRaisesRegex(CompositionError, "first section"):
            compose_result(missing_summary)

        duplicate_summary = payload_for(
            [section_item("account_overview", "ACC-01")],
            "account_overview",
        )
        duplicate_summary["items"].insert(1, section_item("summary"))
        with self.assertRaisesRegex(CompositionError, "exactly one summary"):
            compose_result(duplicate_summary)

        missing_conclusion = payload_for(
            [
                section_item("account_overview", "ACC-01"),
                section_item("account_overview", "ACC-02"),
            ],
            "account_overview",
        )
        missing_conclusion["items"].pop()
        with self.assertRaisesRegex(CompositionError, "last section"):
            compose_result(missing_conclusion)

    def test_rejects_duplicate_card(self) -> None:
        duplicate = payload_for(
            [
                section_item("account_overview", "ACC-01"),
                section_item("account_overview", "ACC-01"),
            ],
            "account_overview",
        )
        with self.assertRaisesRegex(CompositionError, "duplicate cardId"):
            compose_result(duplicate)

    def test_rejects_final_response_fields(self) -> None:
        payload = payload_for(
            [section_item("account_overview", "ACC-01")],
            "account_overview",
        )
        payload["version"] = "2.2"
        payload["meta"] = {"scene": "问账户"}
        payload["risk_warning"] = "不属于账户域局部结果"

        with self.assertRaisesRegex(CompositionError, "unsupported fields"):
            compose_result(payload)

    def test_rejects_primary_intent_not_present_in_business_sections(self) -> None:
        payload = payload_for(
            [section_item("account_overview", "ACC-01")],
            "watchlist_valuation",
        )

        with self.assertRaisesRegex(CompositionError, "must match"):
            compose_result(payload)

    def test_rejects_wrong_scene(self) -> None:
        payload = payload_for(
            [section_item("account_overview", "ACC-01")],
            "account_overview",
        )
        payload["scene"] = "问基金"

        with self.assertRaisesRegex(CompositionError, "scene must be 问账户"):
            compose_result(payload)

    def test_rejects_extra_fields_and_empty_narrative(self) -> None:
        extra = payload_for(
            [section_item("account_overview", "ACC-01")],
            "account_overview",
        )
        extra["items"][1]["section"]["content"] = "旧协议字段"
        with self.assertRaisesRegex(CompositionError, "unsupported fields"):
            compose_result(extra)

        empty_narrative = copy.deepcopy(extra)
        del empty_narrative["items"][1]["section"]["content"]
        empty_narrative["items"][1]["section"]["narrative"] = ""
        with self.assertRaisesRegex(CompositionError, "must not be empty"):
            compose_result(empty_narrative)


if __name__ == "__main__":
    unittest.main()
