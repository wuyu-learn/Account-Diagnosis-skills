from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (SKILL_DIR / relative_path).read_text(encoding="utf-8")


class CardRoutingGuidanceTests(unittest.TestCase):
    def test_main_path_is_the_only_normal_runtime_rule_source(self) -> None:
        skill = read("SKILL.md")
        routing = read("references/main-path.md")
        self.assertIn("常规主路径唯一运行协议", skill)
        self.assertIn("常规路径只读取 `references/main-path.md`", skill)
        self.assertIn("本文件是常规问账户路径的唯一运行规则", routing)

    def test_reference_covers_single_and_multi_question_combinations(self) -> None:
        routing = read("references/main-path.md")
        for rule in (
            "我的账户怎么样",
            "我买了什么，今年赚多少",
            "今年收益多少，哪些产品拖累",
            "重仓产品是否为主要拖累",
        ):
            self.assertIn(rule, routing)

    def test_response_mode_uses_explicit_triggers_not_card_count(self) -> None:
        routing = read("references/main-path.md")
        self.assertIn("明确要求诊断、解释原因或分析关系", routing)
        self.assertIn("其他所有问题", routing)
        self.assertIn("卡片数量和 MCP 数量不改变模式", routing)

    def test_full_diagnosis_has_one_default_combination(self) -> None:
        routing = read("references/main-path.md")
        rules = routing[routing.index("规则：") :]
        for card_id in ("ACC-01", "ACC-11", "ACC-12", "ACC-13-A", "ACC-15"):
            self.assertIn(card_id, rules)
        self.assertIn("primary 为", rules)
        self.assertIn("关系诊断只选择并", rules)

    def test_card_parameter_and_mcp_boundaries_are_preserved(self) -> None:
        routing = read("references/main-path.md")
        for rule in (
            "诊断类 ACC-01～15 与自选 ACC-18 不得混排",
            "不要逐卡调用",
            "ACC-15 必须带 `dateType`",
            "合并去重",
        ):
            self.assertIn(rule, routing)


if __name__ == "__main__":
    unittest.main()
