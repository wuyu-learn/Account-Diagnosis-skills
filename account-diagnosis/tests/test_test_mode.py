from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEST_MODE_DIR = SCRIPTS_DIR / "test_mode"
sys.path.insert(0, str(TEST_MODE_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TEST_MODE_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


interceptor = _load("interceptor")
enrich_test_cards = _load("enrich_test_cards")
from account_contract import CARD_SPECS  # noqa: E402

# Import shared skeleton/composer used by the normal pipeline.
shared_spec = importlib.util.spec_from_file_location(
    "build_result_skeleton", SCRIPTS_DIR / "build_result_skeleton.py"
)
assert shared_spec is not None and shared_spec.loader is not None
build_result_skeleton = importlib.util.module_from_spec(shared_spec)
shared_spec.loader.exec_module(build_result_skeleton)

compose_spec = importlib.util.spec_from_file_location(
    "compose_result", SCRIPTS_DIR / "compose_result.py"
)
assert compose_spec is not None and compose_spec.loader is not None
compose_result = importlib.util.module_from_spec(compose_spec)
compose_spec.loader.exec_module(compose_result)


def business_item(card_id: str, data: dict) -> dict:
    spec = CARD_SPECS[card_id]
    return {
        "section": {
            "type": spec["sectionType"],
            "title": spec["title"],
            "narrative": spec["narrative"],
        },
        "card": {"cardId": card_id, "dataMode": "deferred", "data": data},
    }


class InterceptorTests(unittest.TestCase):
    def test_detects_keyword_in_original_query(self) -> None:
        self.assertTrue(interceptor.is_test_mode({"originalQuery": "问账户：全部卡片测试"}))

    def test_detects_keyword_in_subquery(self) -> None:
        route = {
            "originalQuery": "别的",
            "scenes": [{"scene": "问账户", "weight": 1.0, "subQuery": "问账户：全部卡片测试"}],
        }
        self.assertTrue(interceptor.is_test_mode(route))

    def test_short_keyword_under_account_scene_triggers(self) -> None:
        """subQuery='问账户：全部卡片测试' under 问账户 scene should trigger test mode."""
        route = {
            "originalQuery": "问账户：全部卡片测试",
            "scenes": [{"scene": "问账户", "weight": 1.0, "subQuery": "问账户：全部卡片测试"}],
        }
        self.assertTrue(interceptor.is_test_mode(route))

    def test_non_keyword_input_is_not_test_mode(self) -> None:
        self.assertFalse(interceptor.is_test_mode({"originalQuery": "我今年收益怎么样"}))

    # -- single-card test mode --

    def test_parses_single_card_keyword(self) -> None:
        self.assertEqual(
            interceptor.parse_single_card_test({"originalQuery": "问账户：ACC-01测试"}),
            ["ACC-01"],
        )

    def test_parses_multiple_cards_comma_separated(self) -> None:
        self.assertEqual(
            interceptor.parse_single_card_test({"originalQuery": "问账户：ACC-01,ACC-11测试"}),
            ["ACC-01", "ACC-11"],
        )

    def test_parses_card_keyword_in_subquery(self) -> None:
        route = {
            "originalQuery": "别的",
            "scenes": [{"scene": "问账户", "subQuery": "问账户：ACC-13-A测试"}],
        }
        self.assertEqual(
            interceptor.parse_single_card_test(route),
            ["ACC-13-A"],
        )

    def test_invalid_card_id_returns_none(self) -> None:
        self.assertIsNone(
            interceptor.parse_single_card_test({"originalQuery": "问账户：ACC-99测试"}),
        )

    def test_card_id_without_test_keyword_returns_card_id(self) -> None:
        """单卡测试不需要带'测试'字样，'问账户：ACC-01'即可提取。"""
        self.assertEqual(
            interceptor.parse_single_card_test({"originalQuery": "问账户：ACC-01"}),
            ["ACC-01"],
        )

    def test_card_id_without_account_prefix_returns_none(self) -> None:
        """单卡测试也必须以'问账户：'开头。"""
        self.assertIsNone(
            interceptor.parse_single_card_test({"originalQuery": "ACC-01测试"}),
        )

    def test_full_keyword_takes_precedence_over_single(self) -> None:
        """Full-card keyword should be detected by is_test_mode."""
        route = {"originalQuery": "问账户：全部卡片测试"}
        self.assertTrue(interceptor.is_test_mode(route))
        self.assertIsNone(interceptor.parse_single_card_test(route))

    def test_fuzzy_natural_language_still_has_test_prefix(self) -> None:
        """自然语言变体仍以'问账户：'开头即命中测试模式入口。"""
        route = {"originalQuery": "问账户：测一下全部卡片"}
        self.assertTrue(interceptor.is_test_mode(route))
        self.assertEqual(interceptor.detect_test_mode(route), {"testMode": True})

    def test_fuzzy_card_test_has_test_prefix(self) -> None:
        """仅说'问账户：卡片测试'也命中测试模式入口（agent 决定全量）。"""
        route = {"originalQuery": "问账户：卡片测试"}
        self.assertTrue(interceptor.is_test_mode(route))
        self.assertEqual(interceptor.detect_test_mode(route), {"testMode": True})

    def test_fuzzy_single_card_natural_language(self) -> None:
        """'问账户：测试一下 ACC-19'可提取单卡卡号。"""
        route = {"originalQuery": "问账户：测试一下 ACC-19"}
        self.assertTrue(interceptor.is_test_mode(route))
        self.assertEqual(interceptor.parse_single_card_test(route), ["ACC-19"])

    def test_plain_test_word_with_prefix_is_test_mode(self) -> None:
        """只要以'问账户：'开头就交给 agent 判断，不再由脚本拦截。"""
        route = {"originalQuery": "问账户：测试"}
        self.assertTrue(interceptor.is_test_mode(route))
        self.assertEqual(interceptor.detect_test_mode(route), {"testMode": True})
        self.assertIsNone(interceptor.parse_single_card_test(route))
        self.assertFalse(interceptor.is_full_test_keyword(route))

    def test_single_card_plan_shape(self) -> None:
        plan = interceptor.build_test_plan(["ACC-01"])
        self.assertEqual(plan["taskComplexity"], "simple")
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        self.assertEqual(plan["accountScenes"][0]["intent"], "account_test")
        self.assertEqual(plan["accountScenes"][1]["intent"], "account_overview")
        self.assertEqual(plan["cardPlans"], [{"cardId": "ACC-01", "params": {}}])

    def test_single_card_acc15_has_date_type(self) -> None:
        plan = interceptor.build_test_plan(["ACC-15"])
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        self.assertEqual(plan["accountScenes"][0]["intent"], "account_test")
        self.assertEqual(plan["accountScenes"][1]["intent"], "return_attribution")
        self.assertEqual(plan["cardPlans"], [{"cardId": "ACC-15", "params": {"dateType": "N"}}])

    def test_multi_card_plan_covers_multiple_intents(self) -> None:
        plan = interceptor.build_test_plan(["ACC-01", "ACC-11"])
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        intents = [s["intent"] for s in plan["accountScenes"]]
        self.assertEqual(intents[0], "account_test")
        self.assertIn("account_overview", intents)
        self.assertIn("holding_structure", intents)
        self.assertEqual(len(plan["cardPlans"]), 2)

    def test_fixed_plan_shape(self) -> None:
        plan = interceptor.build_test_plan()
        self.assertEqual(plan["taskComplexity"], "simple")
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        self.assertEqual(plan["accountScenes"][0]["intent"], "account_test")
        self.assertEqual(len(plan["accountScenes"]), 6)
        acc19 = [c for c in plan["cardPlans"] if c["cardId"] == "ACC-19"]
        self.assertEqual(len(acc19), 1)
        self.assertEqual(acc19[0]["params"], {})
        self.assertIn({"cardId": "ACC-18", "params": {}}, plan["cardPlans"])
        acc15 = [c for c in plan["cardPlans"] if c["cardId"] == "ACC-15"][0]
        self.assertEqual(acc15["params"], {"dateType": "N"})


class BuildResultSkeletonTests(unittest.TestCase):
    def test_builds_from_fixed_plan_with_mixed_cards(self) -> None:
        skeleton = build_result_skeleton.build_result_skeleton(
            interceptor.build_test_plan()
        )
        self.assertEqual(
            set(skeleton),
            {"taskComplexity", "complexityReason", "primaryAccountIntent", "businessItems"},
        )
        ids = [it["card"]["cardId"] for it in skeleton["businessItems"]]
        self.assertEqual(ids.count("ACC-19"), 1)
        self.assertIn("ACC-18", ids)  # diagnosis + watchlist mixing allowed under account_test

        overview = [
            it["card"]["cardId"]
            for it in skeleton["businessItems"]
            if it["section"]["type"] == "account_overview"
        ]
        self.assertEqual(overview, [f"ACC-0{n}" for n in range(1, 10)] + ["ACC-10", "ACC-19"])

    def test_rejects_duplicate_card_id(self) -> None:
        plan = {
            "taskComplexity": "simple",
            "complexityReason": "dup",
            "primaryAccountIntent": "account_test",
            "accountScenes": [
                {"intent": "account_test", "weight": 1.0, "subQuery": "x"},
                {"intent": "account_overview", "weight": 0.9, "subQuery": "x"},
            ],
            "cardPlans": [
                {"cardId": "ACC-19", "params": {}},
                {"cardId": "ACC-19", "params": {}},
            ],
        }
        with self.assertRaisesRegex(build_result_skeleton.SkeletonError, "duplicate cardId"):
            build_result_skeleton.build_result_skeleton(plan)

    def test_rejects_identity_param(self) -> None:
        plan = {
            "taskComplexity": "simple",
            "complexityReason": "x",
            "primaryAccountIntent": "account_test",
            "accountScenes": [
                {"intent": "account_test", "weight": 1.0, "subQuery": "x"},
                {"intent": "account_overview", "weight": 0.9, "subQuery": "x"},
            ],
            "cardPlans": [{"cardId": "ACC-01", "params": {"custNo": "C1"}}],
        }
        with self.assertRaisesRegex(build_result_skeleton.SkeletonError, "identity param"):
            build_result_skeleton.build_result_skeleton(plan)

    def test_rejects_unknown_param_on_acc19(self) -> None:
        plan = {
            "taskComplexity": "simple",
            "complexityReason": "x",
            "primaryAccountIntent": "account_test",
            "accountScenes": [
                {"intent": "account_test", "weight": 1.0, "subQuery": "x"},
                {"intent": "account_overview", "weight": 0.9, "subQuery": "x"},
            ],
            "cardPlans": [{"cardId": "ACC-19", "params": {"大类": "基金", "bogus": "x"}}],
        }
        with self.assertRaisesRegex(build_result_skeleton.SkeletonError, "only allows"):
            build_result_skeleton.build_result_skeleton(plan)


class EnrichTestCardsTests(unittest.TestCase):
    def _skeleton_items(self) -> list[dict]:
        return build_result_skeleton.build_result_skeleton(
            interceptor.build_test_plan()
        )["businessItems"]

    def test_picks_share_item_from_holding_per_category(self) -> None:
        """份额级卡片从 queryHoldingDetail 该大类的产品项挑标识 (productId/balanceSerialNo/uri)。"""
        holding_detail = {"categoryList": [
            {"categoryCode": "1", "classifyName": "公募基金", "itemList": [
                {"fundId": "F1", "serialNo": "s1", "uri": "u1"},
                {"fundId": "F2", "serialNo": "s2", "uri": "u2"},
            ]},
            {"categoryCode": "6", "classifyName": "投顾", "itemList": [
                {"fundId": "A1", "serialNo": "s4", "uri": "u4"},
            ]},
            {"categoryCode": "0", "classifyName": "货币", "itemList": []},
            {"categoryCode": "4", "classifyName": "资管", "itemList": []},
        ]}
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": self._skeleton_items(),
                "holdingDetail": holding_detail,
                "seed": 42,
            }
        )
        # ACC-03 = 公募(categoryCode=1) → F1/F2 产品项
        acc03 = [it for it in result["businessItems"] if it["card"]["cardId"] == "ACC-03"][0]
        self.assertIn(acc03["card"]["data"]["productId"], {"F1", "F2"})
        self.assertIn(acc03["card"]["data"]["balanceSerialNo"], {"s1", "s2"})
        # 货币大类无产品项 → ACC-08 空
        acc08 = [it for it in result["businessItems"] if it["card"]["cardId"] == "ACC-08"][0]
        self.assertEqual(acc08["card"]["data"], {})

    def test_acc19_stays_empty_when_no_products(self) -> None:
        """ACC-19: 完全无产品时卡片保留、data 为空。"""
        items = [business_item("ACC-19", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": []},
                "seed": 1,
            }
        )
        acc19 = result["businessItems"][0]
        self.assertEqual(acc19["card"]["data"], {})

    def test_acc19_prefers_multi_channel_fund_id(self) -> None:
        """ACC-19: 优先挑多渠道 fundId（同 fundId 不同 serialNo ≥2）。"""
        items = [business_item("ACC-19", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金", "itemList": [
                        {"fundId": "F1", "serialNo": "s1", "uri": "u1"},
                        {"fundId": "F1", "serialNo": "s2", "uri": "u2"},
                        {"fundId": "F2", "serialNo": "s3", "uri": "u3"},
                    ]},
                ]},
                "seed": 1,
            }
        )
        acc19 = result["businessItems"][0]
        self.assertEqual(acc19["card"]["data"], {"productId": "F1"})

    def test_acc19_falls_back_to_any_fund_id(self) -> None:
        """ACC-19: 无多渠道时在任意 fundId 中随机挑选。"""
        items = [business_item("ACC-19", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金", "itemList": [
                        {"fundId": "F1", "serialNo": "s1", "uri": "u1"},
                        {"fundId": "F2", "serialNo": "s2", "uri": "u2"},
                    ]},
                ]},
                "seed": 1,
            }
        )
        acc19 = result["businessItems"][0]
        self.assertIn(acc19["card"]["data"]["productId"], {"F1", "F2"})

    def test_share_card_without_holdings_stays_empty(self) -> None:
        items = [
            business_item("ACC-08", {}),  # 货币 share card, 货币 大类无持仓
        ]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金",
                     "itemList": [{"fundId": "F1", "serialNo": "s1", "uri": "u1"}]},
                ]},
                "seed": 1,
            }
        )
        acc08 = [it for it in result["businessItems"] if it["card"]["cardId"] == "ACC-08"][0]
        self.assertEqual(acc08["card"]["data"], {})  # 货币 大类无产品项 → retained, not filled

    def test_reads_lists_under_body_wrapper(self) -> None:
        """Real MCP wraps payloads under ``body``; enrich reads categoryList there."""
        items = [business_item("ACC-03", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"returnCode": 0, "body": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金",
                     "itemList": [{"fundId": "F1", "serialNo": "s1", "uri": "u1"}]},
                ]}},
                "seed": 1,
            }
        )
        acc03 = result["businessItems"][0]
        self.assertEqual(acc03["card"]["data"]["productId"], "F1")  # read through body

    def test_tolerates_null_uri_on_share(self) -> None:
        """产品项 uri 可能为 null；挑到时填 balanceSerialNo、不填 uri，不崩。"""
        items = [business_item("ACC-03", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金",
                     "itemList": [{"fundId": "F1", "serialNo": "s1", "uri": None}]},
                ]},
                "seed": 1,
            }
        )
        acc03 = result["businessItems"][0]
        # uri 缺 → 不填 uri；productId/balanceSerialNo 照填
        self.assertEqual(acc03["card"]["data"], {"productId": "F1", "balanceSerialNo": "s1"})

    def test_prefers_three_field_complete_share(self) -> None:
        """大类里有三字段齐全的和缺 uri 的产品项，优先挑三字段齐全的。"""
        items = [business_item("ACC-03", {})]
        result = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": items,
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金", "itemList": [
                        {"fundId": "F1", "serialNo": "s_no_uri", "uri": None},
                        {"fundId": "F2", "serialNo": "s_full", "uri": "u_full"},
                    ]},
                ]},
                "seed": 1,
            }
        )
        acc03 = result["businessItems"][0]
        # 优先挑三字段齐全的 F2，三个字段都填上
        self.assertEqual(
            acc03["card"]["data"],
            {"productId": "F2", "balanceSerialNo": "s_full", "uri": "u_full"},
        )


class ComposeResultTests(unittest.TestCase):
    def _payload(self, business_items: list[dict]) -> dict:
        return {
            "scene": "问账户",
            "taskComplexity": "simple",
            "primaryAccountIntent": "account_test",
            "businessItems": business_items,
            "summary": {"title": "卡片测试", "narrative": "这是全部卡片测试。"},
            "followUp": [],
        }

    def test_emits_six_top_level_keys(self) -> None:
        items = [
            business_item("ACC-19", {"productId": "F1"}),
            business_item("ACC-18", {}),
        ]
        result = compose_result.compose_result(self._payload(items))
        self.assertEqual(
            set(result), {"version", "meta", "sections", "cards", "risk_warning", "followUp"}
        )
        self.assertEqual(result["version"], "2.2")
        self.assertEqual(result["meta"], {"scene": "问账户", "intent": "account_test"})

    def test_allows_diagnosis_and_watchlist_mixing_for_account_test(self) -> None:
        items = [
            business_item("ACC-19", {"productId": "F1"}),
            business_item("ACC-18", {}),
        ]
        result = compose_result.compose_result(self._payload(items))
        ids = [c["cardId"] for c in result["cards"]]
        self.assertIn("ACC-19", ids)
        self.assertIn("ACC-18", ids)

    def test_accepts_single_acc19_with_string_product_id(self) -> None:
        items = [
            business_item("ACC-19", {"productId": "F1"}),
            business_item("ACC-18", {}),
        ]
        result = compose_result.compose_result(self._payload(items))
        ids = [c["cardId"] for c in result["cards"]]
        self.assertEqual(ids.count("ACC-19"), 1)
        self.assertIn("ACC-18", ids)
        acc19 = [c for c in result["cards"] if c["cardId"] == "ACC-19"][0]
        self.assertEqual(acc19["data"], {"productId": "F1"})

    def test_rejects_array_product_id_on_acc19(self) -> None:
        items = [
            business_item("ACC-19", {"productId": ["F1"]}),
        ]
        with self.assertRaisesRegex(compose_result.CompositionError, "must be a non-empty string"):
            compose_result.compose_result(self._payload(items))

    def test_rejects_tampered_section_title(self) -> None:
        item = business_item("ACC-19", {"productId": "F1"})
        item["section"]["title"] = "篡改标题"
        with self.assertRaisesRegex(compose_result.CompositionError, "fixed card contract"):
            compose_result.compose_result(self._payload([item]))

    def test_rejects_non_deferred_datamode(self) -> None:
        item = business_item("ACC-19", {"productId": "F1"})
        item["card"]["dataMode"] = "inline"
        with self.assertRaisesRegex(compose_result.CompositionError, "dataMode must be deferred"):
            compose_result.compose_result(self._payload([item]))

    def test_simple_must_not_include_conclusion(self) -> None:
        payload = self._payload([business_item("ACC-19", {"productId": "F1"})])
        payload["conclusion"] = {"title": "x", "narrative": "y"}
        with self.assertRaisesRegex(compose_result.CompositionError, "must not include conclusion"):
            compose_result.compose_result(payload)


class EndToEndTests(unittest.TestCase):
    def test_full_test_mode_pipeline(self) -> None:
        route = {
            "originalQuery": "问账户：全部卡片测试",
            "scenes": [{"scene": "问账户", "weight": 1.0, "subQuery": "问账户：全部卡片测试"}],
        }
        self.assertTrue(interceptor.is_test_mode(route))

        plan = interceptor.build_test_plan()
        self.assertEqual(plan["primaryAccountIntent"], "account_test")

        skeleton = build_result_skeleton.build_result_skeleton(plan)
        enriched = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": skeleton["businessItems"],
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金",
                     "itemList": [
                         {"fundId": "F1", "serialNo": "s1", "uri": "u1"},
                         {"fundId": "F1", "serialNo": "s2", "uri": "u2"},
                     ]},
                    {"categoryCode": "6", "classifyName": "投顾",
                     "itemList": [{"fundId": "A1", "serialNo": "s4", "uri": "u4"}]},
                    {"categoryCode": "0", "classifyName": "货币", "itemList": []},
                    {"categoryCode": "4", "classifyName": "资管", "itemList": []},
                    {"categoryCode": "3", "classifyName": "组合", "itemList": []},
                ]},
                "seed": 7,
            }
        )
        result = compose_result.compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "simple",
                "primaryAccountIntent": "account_test",
                "businessItems": enriched["businessItems"],
                "summary": {"title": "卡片测试", "narrative": "这是全部卡片测试。"},
                "followUp": [],
            }
        )
        self.assertEqual(
            set(result), {"version", "meta", "sections", "cards", "risk_warning", "followUp"}
        )
        self.assertEqual(result["meta"]["intent"], "account_test")
        card_ids = [c["cardId"] for c in result["cards"]]
        self.assertEqual(card_ids.count("ACC-19"), 1)
        self.assertIn("ACC-18", card_ids)
        self.assertTrue(all(c["dataMode"] == "deferred" for c in result["cards"]))
        acc19 = [c for c in result["cards"] if c["cardId"] == "ACC-19"][0]
        self.assertEqual(acc19["data"], {"productId": "F1"})  # F1 是多渠道 fundId

    def test_file_based_mode_avoids_llm_truncation(self) -> None:
        """MCP raw data via --holding-detail file, not inline JSON."""
        import tempfile

        plan = interceptor.build_test_plan()
        skeleton = build_result_skeleton.build_result_skeleton(plan)
        holding_detail = {"categoryList": [
            {"categoryCode": "1", "classifyName": "公募基金", "itemList": [
                {"fundId": "F1", "serialNo": "s1", "uri": "u1"},
                {"fundId": "F2", "serialNo": "s2", "uri": "u2"},
            ]},
            {"categoryCode": "6", "classifyName": "投顾", "itemList": [
                {"fundId": "A1", "serialNo": "s4", "uri": "u4"},
                {"fundId": "A2", "serialNo": "s5", "uri": "u5"},
            ]},
            {"categoryCode": "0", "classifyName": "货币", "itemList": []},
            {"categoryCode": "4", "classifyName": "资管", "itemList": []},
        ]}

        with tempfile.TemporaryDirectory() as tmp:
            import json as _json
            skeleton_path = Path(tmp) / "skeleton.json"
            holding_path = Path(tmp) / "holding_detail.json"
            output_path = Path(tmp) / "enriched.json"

            skeleton_path.write_text(_json.dumps(skeleton), encoding="utf-8")
            holding_path.write_text(_json.dumps(holding_detail), encoding="utf-8")

            rc = enrich_test_cards.main(
                [
                    "--business-items", str(skeleton_path),
                    "--holding-detail", str(holding_path),
                    "--seed", "42",
                    "--output", str(output_path),
                ]
            )
            self.assertEqual(rc, 0)

            enriched = _json.loads(output_path.read_text(encoding="utf-8"))
            acc03 = [it for it in enriched["businessItems"] if it["card"]["cardId"] == "ACC-03"][0]
            self.assertIn(acc03["card"]["data"]["balanceSerialNo"], {"s1", "s2"})
            self.assertIn(acc03["card"]["data"]["uri"], {"u1", "u2"})
            acc05 = [it for it in enriched["businessItems"] if it["card"]["cardId"] == "ACC-05"][0]
            self.assertIn(acc05["card"]["data"]["balanceSerialNo"], {"s4", "s5"})
            acc06 = [it for it in enriched["businessItems"] if it["card"]["cardId"] == "ACC-06"][0]
            self.assertIn(acc06["card"]["data"]["balanceSerialNo"], {"s4", "s5"})
            acc08 = [it for it in enriched["businessItems"] if it["card"]["cardId"] == "ACC-08"][0]
            self.assertEqual(acc08["card"]["data"], {})  # 货币无产品项

    def test_single_card_pipeline_acc15(self) -> None:
        """Single-card test for ACC-15: interceptor plan → skeleton → compose."""
        route = {"originalQuery": "问账户：ACC-15测试"}
        self.assertTrue(interceptor.parse_single_card_test(route))
        card_ids = interceptor.parse_single_card_test(route)
        self.assertEqual(card_ids, ["ACC-15"])

        plan = interceptor.build_test_plan(card_ids)
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        skeleton = build_result_skeleton.build_result_skeleton(plan)
        self.assertEqual(len(skeleton["businessItems"]), 1)
        self.assertEqual(skeleton["businessItems"][0]["card"]["cardId"], "ACC-15")

        result = compose_result.compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "simple",
                "primaryAccountIntent": "account_test",
                "businessItems": skeleton["businessItems"],
                "summary": {"title": "卡片测试", "narrative": "单卡 ACC-15 测试。"},
                "followUp": [],
            }
        )
        self.assertEqual(result["meta"]["intent"], "account_test")
        self.assertEqual(result["cards"][0]["cardId"], "ACC-15")
        self.assertEqual(result["cards"][0]["data"], {"dateType": "N"})
        self.assertEqual([s["type"] for s in result["sections"]], ["summary", "return_attribution"])

    def test_single_share_card_pipeline_with_enrich(self) -> None:
        """Single ACC-03: skeleton → enrich with MCP data → compose."""
        plan = interceptor.build_test_plan(["ACC-03"])
        self.assertEqual(plan["primaryAccountIntent"], "account_test")
        skeleton = build_result_skeleton.build_result_skeleton(plan)

        enriched = enrich_test_cards.enrich_test_cards(
            {
                "businessItems": skeleton["businessItems"],
                "holdingDetail": {"categoryList": [
                    {"categoryCode": "1", "classifyName": "公募基金",
                     "itemList": [{"fundId": "F1", "serialNo": "s1", "uri": "u1"}]},
                ]},
                "seed": 1,
            }
        )
        acc03 = enriched["businessItems"][0]
        self.assertEqual(acc03["card"]["data"], {"balanceSerialNo": "s1", "uri": "u1", "productId": "F1"})

        result = compose_result.compose_result(
            {
                "scene": "问账户",
                "taskComplexity": "simple",
                "primaryAccountIntent": "account_test",
                "businessItems": enriched["businessItems"],
                "summary": {"title": "卡片测试", "narrative": "单卡 ACC-03 测试。"},
                "followUp": [],
            }
        )
        self.assertEqual(result["meta"]["intent"], "account_test")
        self.assertEqual(result["cards"][0]["cardId"], "ACC-03")
        self.assertEqual(result["cards"][0]["data"], {"balanceSerialNo": "s1", "uri": "u1", "productId": "F1"})


if __name__ == "__main__":
    unittest.main()
