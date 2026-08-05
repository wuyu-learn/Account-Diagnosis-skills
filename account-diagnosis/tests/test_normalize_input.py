from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from normalize_input import normalize_input, NormalizeInputError  # noqa: E402


class NormalizeInputTests(unittest.TestCase):
    def test_strict_route_extract_is_preserved(self) -> None:
        payload = {
            "originalQuery": "我今年收益怎么样",
            "scenes": [
                {"scene": "问账户", "weight": 0.95, "subQuery": "我今年收益怎么样"}
            ],
            "entities": {
                "fund_names": ["汇添富短债债券A"],
                "fund_codes": ["006646"],
                "manager_names": [],
                "company_names": [],
                "market_subjects": [],
                "strategy_names": [],
            },
            "primaryScene": "问账户",
            "isMultiScene": False,
            "orchestration": None,
            "clarify": {"needed": False, "question": None},
        }
        result = normalize_input(payload)
        self.assertEqual(result, payload)

    def test_missing_original_query_is_derived_from_scenes(self) -> None:
        payload = {
            "scenes": [
                {"scene": "问账户", "weight": 0.9, "subQuery": "持仓添富短债债券A的定投计划的持仓明细"}
            ],
            "entities": {
                "funds": [{"name": "汇添富短债债券A", "code": "006646"}]
            },
            "primaryScene": "问账户",
            "isMultiScene": False,
        }
        result = normalize_input(payload)
        self.assertEqual(
            result["originalQuery"],
            "持仓添富短债债券A的定投计划的持仓明细",
        )
        self.assertEqual(result["entities"]["fund_names"], ["汇添富短债债券A"])
        self.assertEqual(result["entities"]["fund_codes"], ["006646"])
        self.assertEqual(result["clarify"], {"needed": False, "question": None})
        self.assertIsNone(result["orchestration"])

    def test_entities_variant_fund_array_is_normalized(self) -> None:
        payload = {
            "originalQuery": "我持有的基金怎么样",
            "scenes": [{"scene": "问账户", "subQuery": "我持有的基金怎么样"}],
            "entities": {
                "funds": [
                    {"name": "基金A", "code": "000001"},
                    {"name": "基金B"},
                ]
            },
        }
        result = normalize_input(payload)
        self.assertEqual(result["entities"]["fund_names"], ["基金A", "基金B"])
        self.assertEqual(result["entities"]["fund_codes"], ["000001"])

    def test_plain_text_becomes_default_account_scene(self) -> None:
        result = normalize_input("我今年收益怎么样")
        self.assertEqual(result["originalQuery"], "我今年收益怎么样")
        self.assertEqual(len(result["scenes"]), 1)
        self.assertEqual(result["scenes"][0]["scene"], "问账户")
        self.assertEqual(result["scenes"][0]["subQuery"], "我今年收益怎么样")
        self.assertEqual(result["primaryScene"], "问账户")
        self.assertFalse(result["isMultiScene"])

    def test_json_string_is_parsed_and_normalized(self) -> None:
        raw_text = '{"scenes":[{"scene":"问账户","subQuery":"我的账户怎么样"}]}'
        result = normalize_input(raw_text)
        self.assertEqual(result["originalQuery"], "我的账户怎么样")
        self.assertEqual(result["scenes"][0]["subQuery"], "我的账户怎么样")

    def test_empty_input_raises(self) -> None:
        with self.assertRaises(NormalizeInputError):
            normalize_input("")

    def test_none_input_raises(self) -> None:
        with self.assertRaises(NormalizeInputError):
            normalize_input(None)

    def test_no_account_scene_raises(self) -> None:
        payload = {
            "originalQuery": "今天市场怎么样",
            "scenes": [{"scene": "问市场", "subQuery": "今天市场怎么样"}],
        }
        with self.assertRaises(NormalizeInputError):
            normalize_input(payload)

    def test_missing_scenes_generates_default_from_original_query(self) -> None:
        payload = {"originalQuery": "我的账户有多少钱"}
        result = normalize_input(payload)
        self.assertEqual(result["scenes"][0]["scene"], "问账户")
        self.assertEqual(result["scenes"][0]["subQuery"], "我的账户有多少钱")

    def test_singular_entity_fields_are_normalized(self) -> None:
        payload = {
            "originalQuery": "测试",
            "scenes": [{"scene": "问账户", "subQuery": "测试"}],
            "entities": {
                "manager": "经理A",
                "company": "公司B",
                "strategy": "策略C",
                "market_subject": "主题D",
            },
        }
        result = normalize_input(payload)
        self.assertEqual(result["entities"]["manager_names"], ["经理A"])
        self.assertEqual(result["entities"]["company_names"], ["公司B"])
        self.assertEqual(result["entities"]["strategy_names"], ["策略C"])
        self.assertEqual(result["entities"]["market_subjects"], ["主题D"])

    def test_standard_and_variant_entities_are_merged(self) -> None:
        payload = {
            "originalQuery": "测试",
            "scenes": [{"scene": "问账户", "subQuery": "测试"}],
            "entities": {
                "fund_names": ["基金A"],
                "funds": [{"name": "基金B", "code": "000002"}],
            },
        }
        result = normalize_input(payload)
        self.assertEqual(result["entities"]["fund_names"], ["基金A", "基金B"])
        self.assertEqual(result["entities"]["fund_codes"], ["000002"])


if __name__ == "__main__":
    unittest.main()
