#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock 生成“问账户”子 Agent 的输入。

用法：
    python scripts/mock_account_dispatch_input.py "帮我看看我的基金持仓盈亏"

不传入参数时，会进入交互模式，提示输入问题。
"""

import json
import sys

# Windows 命令行默认编码可能是 GBK，这里强制 stdout/stderr 使用 UTF-8，
# 保证中文正常显示。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def build_account_dispatch_input(question: str) -> str:
    """根据用户问题构造分发给“问账户”子 Agent 的完整输入。"""
    payload = {
        "scenes": [
            {
                "scene": "问账户",
                "weight": 0.95,
                "subQuery": question,
            }
        ],
        "entities": {
            "fund_names": [],
            "fund_codes": [],
            "manager_names": [],
            "company_names": [],
            "market_subjects": [],
            "strategy_names": [],
        },
        "primaryScene": "问账户",
        "isMultiScene": False,
        "orchestration": None,
        "clarify": {
            "needed": False,
            "question": None,
        },
    }

    return (
        "帮我解析并处理和账户相关的问题：\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def main() -> None:
    if len(sys.argv) > 1:
        question = sys.argv[1]
    else:
        question = input("请输入用户问题：").strip()

    if not question:
        print("错误：问题不能为空。", file=sys.stderr)
        sys.exit(1)

    print(build_account_dispatch_input(question))


if __name__ == "__main__":
    main()
