from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (SKILL_DIR / relative_path).read_text(encoding="utf-8")


class CardRoutingGuidanceTests(unittest.TestCase):
    def test_card_routing_is_the_only_combination_rule_source(self) -> None:
        skill = read("SKILL.md")
        planner = read("references/account-route-planner.md")
        routing = read("references/account-card-routing.md")

        self.assertIn("单卡、卡片组合和业务参数", skill)
        self.assertIn("卡片组合和业务参数", skill)
        self.assertIn("唯一规则来源", planner)
        self.assertIn("用户问题 → `cardPlans`", routing)

    def test_reference_covers_single_and_multi_question_combinations(self) -> None:
        routing = read("references/account-card-routing.md")
        for rule in (
            "我的账户有多少钱 | simple | ACC-01",
            "持仓明细和资产结构都看一下 | simple | ACC-11 + ACC-12",
            "我买了什么，今年赚了多少 | simple | ACC-11 + ACC-13-A",
            "今年收益多少，哪些产品在拖累 | simple | ACC-13-A + ACC-15",
        ):
            self.assertIn(rule, routing)

    def test_same_card_combination_can_be_simple_or_complex(self) -> None:
        routing = read("references/account-card-routing.md")
        self.assertIn("## 卡片组合", routing)
        self.assertIn("### 相同组合、不同复杂度", routing)
        self.assertGreaterEqual(routing.count("ACC-11 + ACC-15"), 3)
        self.assertIn("卡片数量和组合不能反向决定复杂度", routing)

    def test_full_diagnosis_has_one_explicit_default_combination(self) -> None:
        routing = read("references/account-card-routing.md")
        full_diagnosis = routing[routing.index("### 完整账户诊断") :]
        for card_id in ("ACC-01", "ACC-11", "ACC-12", "ACC-13-A", "ACC-15"):
            self.assertIn(card_id, full_diagnosis)
        self.assertIn("primaryAccountIntent` 使用 `account_overview", full_diagnosis)
        self.assertIn("不得因为 `taskComplexity = complex` 自动补齐", routing)

    def test_card_combinations_preserve_class_parameter_and_mcp_boundaries(self) -> None:
        routing = read("references/account-card-routing.md")
        for rule in (
            "账户诊断类 ACC-01～ACC-15 与自选基金类 ACC-18 不得混排",
            "卡片组合不等于 MCP 计划",
            "ACC-15 必须输出 `params.dateType`",
            "同一个 cardId 只保留一次",
        ):
            self.assertIn(rule, routing)


if __name__ == "__main__":
    unittest.main()
