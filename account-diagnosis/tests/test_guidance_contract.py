from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (SKILL_DIR / relative_path).read_text(encoding="utf-8")


class GuidanceContractTests(unittest.TestCase):
    def test_working_stance_is_always_loaded_before_resources_and_workflow(self) -> None:
        skill = read("SKILL.md")
        stance = skill.index("## 账户顾问的工作立场")
        resources = skill.index("## 资源")
        workflow = skill.index("## 工作流")

        self.assertLess(stance, resources)
        self.assertLess(stance, workflow)
        for rule in (
            "不只播报数据",
            "不承担产品销售",
            "不替用户决策",
            "simple 直接回答局部问题",
            "complex 从组合视角",
            "followUp",
        ):
            self.assertIn(rule, skill)

    def test_simple_guidance_stays_direct_and_non_diagnostic(self) -> None:
        simple = read("references/simple-summary.md")
        for rule in (
            "不形成账户级诊断",
            "不生成 Conclusion",
            "事实与用户当前问题的关系",
            "不因单一指标制造焦虑",
            "可选方向",
        ):
            self.assertIn(rule, simple)

    def test_complex_guidance_injects_after_evidence_quality_check(self) -> None:
        skill = read("SKILL.md")
        complex_reference = read("references/complex-diagnosis.md")
        evidence_reference = read("references/mcp-evidence.md")

        self.assertIn("MCP 返回并完成数据质量检查后", skill)
        self.assertIn("## 复杂诊断交接", evidence_reference)
        for rule in (
            "## 复杂诊断注入块",
            "完整账户诊断",
            "关系型诊断",
            "至少形成一个跨维度关系判断",
            "明确哪些关系无法建立以及原因",
            "一至三个发现并排序",
        ):
            self.assertIn(rule, complex_reference)

    def test_complex_guidance_preserves_evidence_and_advice_boundaries(self) -> None:
        complex_reference = read("references/complex-diagnosis.md")
        for rule in (
            "账户范围、诊断周期和对象标识一致",
            "不得使用 deferred 卡片未来可能加载的数据",
            "不判断账户是否适合用户",
            "不给出买卖或调仓结论",
            "不输出业务 Section、卡片、最终 v2.2 字段",
        ):
            self.assertIn(rule, complex_reference)


if __name__ == "__main__":
    unittest.main()
