from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from build_result_skeleton import build_result_skeleton  # noqa: E402
from compose_result import compose_result  # noqa: E402
from normalize_input import normalize_input  # noqa: E402


def route_plan(complexity: str) -> dict:
    return {
        "taskComplexity": complexity,
        "complexityReason": (
            "用户要求跨持仓、收益和归因形成账户判断"
            if complexity == "complex"
            else "用户只询问本年收益"
        ),
        "primaryAccountIntent": (
            "holding_structure" if complexity == "complex" else "return_performance"
        ),
        "accountScenes": (
            [
                {
                    "intent": "holding_structure",
                    "weight": 0.95,
                    "subQuery": "分析账户持仓结构",
                },
                {
                    "intent": "return_performance",
                    "weight": 0.9,
                    "subQuery": "分析收益和回撤",
                },
                {
                    "intent": "return_attribution",
                    "weight": 0.85,
                    "subQuery": "定位主要贡献和拖累",
                },
            ]
            if complexity == "complex"
            else [
                {
                    "intent": "return_performance",
                    "weight": 0.95,
                    "subQuery": "我今年收益怎么样",
                }
            ]
        ),
        "cardPlans": (
            [
                {"cardId": "ACC-12", "params": {}},
                {"cardId": "ACC-13-A", "params": {}},
                {"cardId": "ACC-15", "params": {"dateType": "Y0"}},
            ]
            if complexity == "complex"
            else [{"cardId": "ACC-13-A", "params": {}}]
        ),
    }


class AccountPipelineTests(unittest.TestCase):
    def compose(self, complexity: str) -> dict:
        skeleton = build_result_skeleton(route_plan(complexity))
        payload = {
            "scene": "问账户",
            "taskComplexity": skeleton["taskComplexity"],
            "primaryAccountIntent": skeleton["primaryAccountIntent"],
            "businessItems": skeleton["businessItems"],
            "summary": {
                "title": "账户诊断摘要" if complexity == "complex" else "回答摘要",
                "narrative": (
                    "本次证据显示头部持仓与主要收益拖累重合，是当前第一优先级发现。"
                    if complexity == "complex"
                    else "基于本次已校验证据的直接回答。"
                ),
            },
            "followUp": [],
        }
        if complexity == "complex":
            payload["conclusion"] = {
                "title": "综合结论",
                "narrative": (
                    "头部持仓与主要拖累重合，应优先关注；缺少 KYC 时不形成调仓建议。"
                ),
            }
        return compose_result(payload)

    def test_simple_pipeline_keeps_fixed_output_without_conclusion(self) -> None:
        result = self.compose("simple")
        self.assertEqual(
            set(result),
            {"version", "meta", "sections", "cards", "risk_warning", "followUp"},
        )
        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "return_performance"],
        )
        self.assertEqual(result["cards"][0]["cardId"], "ACC-13-A")

    def test_complex_pipeline_adds_one_conclusion_last(self) -> None:
        result = self.compose("complex")
        section_types = [section["type"] for section in result["sections"]]
        self.assertEqual(
            section_types,
            [
                "summary",
                "holding_structure",
                "return_performance",
                "return_attribution",
                "conclusion",
            ],
        )
        self.assertEqual(section_types.count("conclusion"), 1)
        self.assertEqual(result["cards"][-1]["data"], {"dateType": "Y0"})

    def test_full_diagnosis_default_combination_keeps_fixed_output(self) -> None:
        plan = {
            "taskComplexity": "complex",
            "complexityReason": "用户要求完整账户诊断",
            "primaryAccountIntent": "account_overview",
            "accountScenes": [
                {
                    "intent": "account_overview",
                    "weight": 0.95,
                    "subQuery": "诊断账户整体情况",
                },
                {
                    "intent": "holding_structure",
                    "weight": 0.9,
                    "subQuery": "诊断持仓和资产结构",
                },
                {
                    "intent": "return_performance",
                    "weight": 0.85,
                    "subQuery": "诊断收益表现",
                },
                {
                    "intent": "return_attribution",
                    "weight": 0.8,
                    "subQuery": "诊断收益来源",
                },
            ],
            "cardPlans": [
                {"cardId": "ACC-01", "params": {}},
                {"cardId": "ACC-11", "params": {}},
                {"cardId": "ACC-12", "params": {}},
                {"cardId": "ACC-13-A", "params": {}},
                {"cardId": "ACC-15", "params": {"dateType": "N"}},
            ],
        }
        skeleton = build_result_skeleton(plan)
        result = compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "complex",
                "primaryAccountIntent": "account_overview",
                "businessItems": skeleton["businessItems"],
                "summary": {
                    "title": "账户诊断摘要",
                    "narrative": "基于已校验证据形成账户诊断摘要。",
                },
                "conclusion": {
                    "title": "综合结论",
                    "narrative": "基于同一批证据形成关系判断和优先级。",
                },
                "followUp": [],
            }
        )

        self.assertEqual(
            [card["cardId"] for card in result["cards"]],
            ["ACC-01", "ACC-11", "ACC-12", "ACC-13-A", "ACC-15"],
        )
        self.assertEqual(
            [section["type"] for section in result["sections"]],
            [
                "summary",
                "account_overview",
                "holding_structure",
                "holding_structure",
                "return_performance",
                "return_attribution",
                "conclusion",
            ],
        )

    def test_end_to_end_with_variant_input_and_missing_original_query(self) -> None:
        """Upstream sends a variant JSON without originalQuery."""
        upstream = {
            "scenes": [
                {
                    "scene": "问账户",
                    "weight": 0.9,
                    "subQuery": "持仓添富短债债券A的定投计划的持仓明细",
                }
            ],
            "entities": {"funds": [{"name": "汇添富短债债券A", "code": "006646"}]},
            "primaryScene": "问账户",
            "isMultiScene": False,
            "orchestration": None,
            "clarify": {"needed": False, "question": None},
        }
        route_extract = normalize_input(upstream)
        self.assertEqual(
            route_extract["originalQuery"],
            "持仓添富短债债券A的定投计划的持仓明细",
        )
        self.assertEqual(
            route_extract["entities"]["fund_names"],
            ["汇添富短债债券A"],
        )
        self.assertEqual(
            route_extract["entities"]["fund_codes"],
            ["006646"],
        )

        plan = {
            "taskComplexity": "simple",
            "complexityReason": "用户只询问指定产品的份额明细",
            "primaryAccountIntent": "account_overview",
            "accountScenes": [
                {
                    "intent": "account_overview",
                    "weight": 0.9,
                    "subQuery": "持仓添富短债债券A的定投计划的持仓明细",
                }
            ],
            "cardPlans": [{"cardId": "ACC-19", "params": {"productId": "006646"}}],
        }
        skeleton = build_result_skeleton(plan)
        result = compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "simple",
                "primaryAccountIntent": "account_overview",
                "businessItems": skeleton["businessItems"],
                "summary": {
                    "title": "产品份额明细",
                    "narrative": "基于已校验证据的直接回答。",
                },
                "followUp": [],
            }
        )

        self.assertEqual(
            set(result),
            {"version", "meta", "sections", "cards", "risk_warning", "followUp"},
        )
        self.assertEqual(result["cards"][0]["cardId"], "ACC-19")
        self.assertEqual(result["cards"][0]["data"], {"productId": "006646"})
        self.assertNotIn("conclusion", [s["type"] for s in result["sections"]])

    def test_end_to_end_with_plain_text_input(self) -> None:
        """Upstream sends a plain text question instead of JSON."""
        route_extract = normalize_input("我今年收益怎么样")
        self.assertEqual(route_extract["originalQuery"], "我今年收益怎么样")
        self.assertEqual(route_extract["scenes"][0]["scene"], "问账户")

        plan = {
            "taskComplexity": "simple",
            "complexityReason": "用户只询问本年收益",
            "primaryAccountIntent": "return_performance",
            "accountScenes": [
                {
                    "intent": "return_performance",
                    "weight": 0.95,
                    "subQuery": "我今年收益怎么样",
                }
            ],
            "cardPlans": [{"cardId": "ACC-13-A", "params": {}}],
        }
        skeleton = build_result_skeleton(plan)
        result = compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "simple",
                "primaryAccountIntent": "return_performance",
                "businessItems": skeleton["businessItems"],
                "summary": {
                    "title": "今年收益概况",
                    "narrative": "基于已校验证据的直接回答。",
                },
                "followUp": [],
            }
        )

        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "return_performance"],
        )
        self.assertEqual(result["cards"][0]["cardId"], "ACC-13-A")


if __name__ == "__main__":
    unittest.main()
