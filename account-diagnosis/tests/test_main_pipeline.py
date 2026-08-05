from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "main_pipeline.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("main_pipeline", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


DIAGNOSTIC = MODULE.DIAGNOSTIC
SUMMARY_ONLY = MODULE.SUMMARY_ONLY
MainPipelineError = MODULE.MainPipelineError
classify_response_mode = MODULE.classify_response_mode
finalize = MODULE.finalize
prepare = MODULE.prepare


def route(query: str) -> dict:
    return prepare(query)["routeExtract"]


def plan(
    intent: str,
    query: str,
    cards: list[dict],
    extra_scenes: list[dict] | None = None,
) -> dict:
    scenes = [{"intent": intent, "weight": 0.95, "subQuery": query}]
    if extra_scenes:
        scenes.extend(extra_scenes)
    return {
        "primaryAccountIntent": intent,
        "accountScenes": scenes,
        "cardPlans": cards,
    }


def final_payload(query: str, account_plan: dict, *, diagnostic: bool = False) -> dict:
    text = {"summaryNarrative": "基于本次已校验证据的直接回答。"}
    if diagnostic:
        text["conclusionNarrative"] = "基于同一批证据形成关系判断，并说明数据边界。"
    return {"routeExtract": route(query), "plan": account_plan, "text": text}


class ResponseModeTests(unittest.TestCase):
    def test_default_account_questions_are_summary_only(self) -> None:
        for query in (
            "我的账户怎么样",
            "我的基金账户怎么样",
            "哪些产品拖累了收益",
            "我买了什么，今年赚了多少",
            "今年收益多少，哪些产品在拖累",
        ):
            with self.subTest(query=query):
                self.assertEqual(classify_response_mode(route(query)), SUMMARY_ONLY)

    def test_explicit_diagnosis_reason_and_relation_are_diagnostic(self) -> None:
        for query in (
            "给我的账户做一次诊断",
            "帮我做账户体检",
            "全面分析账户并找出主要问题",
            "为什么我的账户今年收益不好",
            "是什么原因导致账户回撤",
            "我的重仓产品是不是主要拖累",
            "持仓结构与收益有什么关系",
        ):
            with self.subTest(query=query):
                self.assertEqual(classify_response_mode(route(query)), DIAGNOSTIC)

    def test_watchlist_is_always_summary_only(self) -> None:
        query_route = route("为什么我的自选基金今天跌了")
        self.assertEqual(
            classify_response_mode(query_route, "watchlist_valuation"),
            SUMMARY_ONLY,
        )

    def test_prepare_routes_test_prefix_without_changing_test_plan(self) -> None:
        result = prepare("问账户：全部卡片测试")
        self.assertTrue(result["testMode"])
        self.assertNotIn("responseMode", result)


class MainPipelineFinalizeTests(unittest.TestCase):
    def test_summary_only_builds_final_json_without_conclusion(self) -> None:
        query = "我今年收益怎么样"
        account_plan = plan(
            "return_performance",
            query,
            [{"cardId": "ACC-13-A", "params": {}}],
        )
        result = finalize(final_payload(query, account_plan))
        self.assertEqual(result["meta"]["intent"], "return_performance")
        self.assertEqual(
            [section["type"] for section in result["sections"]],
            ["summary", "return_performance"],
        )
        self.assertEqual(result["sections"][0]["title"], "回答摘要")
        self.assertEqual(result["followUp"], [])

    def test_diagnostic_builds_summary_and_conclusion_in_one_finalize(self) -> None:
        query = "我的重仓产品是不是主要拖累"
        account_plan = plan(
            "holding_structure",
            query,
            [
                {"cardId": "ACC-11", "params": {}},
                {"cardId": "ACC-15", "params": {"dateType": "N"}},
            ],
            [
                {
                    "intent": "return_attribution",
                    "weight": 0.9,
                    "subQuery": "确认主要拖累",
                }
            ],
        )
        result = finalize(final_payload(query, account_plan, diagnostic=True))
        self.assertEqual(result["sections"][0]["title"], "账户诊断摘要")
        self.assertEqual(result["sections"][-1]["type"], "conclusion")

    def test_summary_only_rejects_conclusion_and_diagnostic_requires_it(self) -> None:
        summary_query = "我的账户怎么样"
        summary_plan = plan(
            "account_overview", summary_query, [{"cardId": "ACC-01", "params": {}}]
        )
        bad_summary = final_payload(summary_query, summary_plan)
        bad_summary["text"]["conclusionNarrative"] = "不允许的结论"
        with self.assertRaisesRegex(MainPipelineError, "must not include"):
            finalize(bad_summary)

        diagnostic_query = "为什么我的账户收益不好"
        diagnostic_plan = plan(
            "return_performance",
            diagnostic_query,
            [
                {"cardId": "ACC-13-A", "params": {}},
                {"cardId": "ACC-15", "params": {"dateType": "N"}},
            ],
            [
                {
                    "intent": "return_attribution",
                    "weight": 0.9,
                    "subQuery": "收益原因",
                }
            ],
        )
        with self.assertRaisesRegex(MainPipelineError, "conclusionNarrative"):
            finalize(final_payload(diagnostic_query, diagnostic_plan))

    def test_model_cannot_override_code_owned_complexity(self) -> None:
        query = "我的账户怎么样"
        account_plan = plan(
            "account_overview", query, [{"cardId": "ACC-01", "params": {}}]
        )
        account_plan["taskComplexity"] = "complex"
        with self.assertRaisesRegex(MainPipelineError, "complexity is code-owned"):
            finalize(final_payload(query, account_plan))

    def test_unique_share_candidate_is_injected_and_ambiguous_is_not(self) -> None:
        query = "查看指定基金定投计划的某笔份额"
        account_plan = plan(
            "account_overview", query, [{"cardId": "ACC-03", "params": {}}]
        )
        unique = final_payload(query, account_plan)
        unique["shareBindings"] = [
            {
                "cardId": "ACC-03",
                "productId": "P1",
                "balanceSerialNo": "S1",
                "uri": "U1",
            }
        ]
        result = finalize(unique)
        self.assertEqual(
            result["cards"][0]["data"],
            {"productId": "P1", "balanceSerialNo": "S1", "uri": "U1"},
        )

        ambiguous = final_payload(query, account_plan)
        ambiguous["shareBindings"] = [
            {"cardId": "ACC-03", "balanceSerialNo": "S1", "uri": "U1"},
            {"cardId": "ACC-03", "balanceSerialNo": "S2", "uri": "U2"},
        ]
        result = finalize(ambiguous)
        self.assertEqual(result["cards"][0]["data"], {})

    def test_test_input_is_rejected_by_normal_finalize(self) -> None:
        query = "问账户：ACC-01测试"
        account_plan = plan(
            "account_overview", query, [{"cardId": "ACC-01", "params": {}}]
        )
        with self.assertRaisesRegex(MainPipelineError, "existing test-mode path"):
            finalize(final_payload(query, account_plan))


if __name__ == "__main__":
    unittest.main()
