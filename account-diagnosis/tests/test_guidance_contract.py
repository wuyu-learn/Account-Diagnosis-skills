from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (SKILL_DIR / relative_path).read_text(encoding="utf-8")


class GuidanceContractTests(unittest.TestCase):
    def test_working_stance_is_loaded_before_resources_and_workflow(self) -> None:
        skill = read("SKILL.md")
        self.assertLess(skill.index("## 账户顾问的工作立场"), skill.index("## 资源"))
        self.assertLess(skill.index("## 账户顾问的工作立场"), skill.index("## 工作流"))
        for rule in (
            "不只播报数据",
            "不承担产品销售",
            "不替用户决策",
            "`summary_only` 直接回答事实问题",
            "`diagnostic` 从组合视角",
            "followUp",
        ):
            self.assertIn(rule, skill)

    def test_main_guidance_is_direct_and_non_diagnostic_by_default(self) -> None:
        main = read("references/main-path.md")
        for rule in (
            "其他所有问题",
            "summary_only",
            "禁止该字段",
            "1～3 个",
            "followUp 默认空数组",
        ):
            self.assertIn(rule, main)

    def test_diagnostic_guidance_runs_after_evidence_quality_check(self) -> None:
        skill = read("SKILL.md")
        diagnostic = read("references/complex-diagnosis.md")
        main = read("references/main-path.md")
        self.assertIn("完成数据质量检查后", skill)
        self.assertIn("范围、周期或对象不一致时不能建立关系", main)
        for rule in (
            "完整账户诊断",
            "关系诊断",
            "至少形成一个跨维度关系判断",
            "哪些关系无法建立以及原因",
            "保留一至三个发现并排序",
        ):
            self.assertIn(rule, diagnostic)

    def test_diagnostic_guidance_preserves_boundaries(self) -> None:
        diagnostic = read("references/complex-diagnosis.md")
        for rule in (
            "账户范围、周期和对象标识一致",
            "不得使用 deferred 卡片未来可能加载的数据",
            "不判断账户是否适合用户",
            "不给出买卖",
            "不生成业务 Section、卡片或最终 JSON",
        ):
            self.assertIn(rule, diagnostic)


if __name__ == "__main__":
    unittest.main()
