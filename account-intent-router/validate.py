"""校验 test-cases.md 中全部期望输出 JSON 是否符合 account-intent-router.md 的规则。

用法: python validate.py
退出码 0 = 全部通过, 1 = 有失败项。
"""
import json
import re
import sys
from pathlib import Path

ALLOWED_INTENTS = {
    "account_overview",
    "holding_structure",
    "return_performance",
    "return_attribution",
    "account_operations",
}

md = Path(__file__).with_name("test-cases.md").read_text(encoding="utf-8")
blocks = re.findall(r"```json\n(.*?)```", md, re.S)

# 每个用例一对: [输入, 输出]
pairs = [(blocks[i], blocks[i + 1]) for i in range(0, len(blocks) - 1, 2)]
if len(blocks) % 2:
    print(f"FAIL: json 代码块数量为奇数 ({len(blocks)}), 有用例缺输入或输出")
    sys.exit(1)

failures = 0
for idx, (raw_in, raw_out) in enumerate(pairs, 1):
    try:
        upstream = json.loads(raw_in)
        out = json.loads(raw_out)
    except json.JSONDecodeError as e:
        print(f"FAIL 用例 {idx}: JSON 解析失败: {e}")
        failures += 1
        continue

    errs = []
    scenes = out.get("accountScenes")
    if not isinstance(scenes, list):
        errs.append("accountScenes 不是数组")
        scenes = []

    for s in scenes:
        if s.get("intent") not in ALLOWED_INTENTS:
            errs.append(f"非法 intent: {s.get('intent')!r}")
        w = s.get("weight")
        if not isinstance(w, (int, float)) or not 0 < w <= 1:
            errs.append(f"weight 越界: {w!r}")
        if not s.get("subQuery"):
            errs.append("subQuery 为空")

    weights = [s["weight"] for s in scenes if isinstance(s.get("weight"), (int, float))]
    if weights != sorted(weights, reverse=True):
        errs.append(f"accountScenes 未按 weight 降序: {weights}")

    expected_primary = scenes[0]["intent"] if scenes else None
    if out.get("primaryAccountIntent") != expected_primary:
        errs.append(f"primaryAccountIntent={out.get('primaryAccountIntent')!r}, 期望 {expected_primary!r}")

    if out.get("isMultiAccountIntent") != (len(scenes) >= 2):
        errs.append(f"isMultiAccountIntent={out.get('isMultiAccountIntent')}, 但 accountScenes 有 {len(scenes)} 条")

    # 无问账户输入 ⇔ 空输出
    has_account = any(s.get("scene") == "问账户" for s in upstream.get("scenes", []))
    if has_account and not scenes:
        errs.append("输入含问账户场景, 输出却为空")
    if not has_account and scenes:
        errs.append("输入无问账户场景, 输出应为空数组")

    if errs:
        failures += 1
        for e in errs:
            print(f"FAIL 用例 {idx}: {e}")
    else:
        print(f"PASS 用例 {idx}")

print(f"\n{len(pairs) - failures}/{len(pairs)} 通过")
sys.exit(1 if failures else 0)
