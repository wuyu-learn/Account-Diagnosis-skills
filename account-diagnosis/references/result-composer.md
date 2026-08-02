# Result Composer

## 目录

- 职责
- 输入来源
- compose_result.py 输入
- 脚本职责
- 最终输出

## 职责

把代码生成的固定业务骨架与 LLM 文案合并，并调用 `scripts/compose_result.py` 输出最终 v2.2 JSON。

禁止重新识别意图、重新选择卡片、修改业务 Section 或调用额外 MCP。

## 输入来源

### 固定业务骨架

`scripts/build_result_skeleton.py` 输出：

```json
{
  "taskComplexity": "simple",
  "complexityReason": "用户只询问本年收益",
  "primaryAccountIntent": "return_performance",
  "businessItems": []
}
```

### LLM 文案

简单任务输出 `summary + followUp`；复杂任务输出 `summary + conclusion + followUp`。

业务骨架只能来自代码，不能接收 LLM 生成的 Section 或卡片。

## compose_result.py 输入

简单任务：

```json
{
  "scene": "问账户",
  "taskComplexity": "simple",
  "primaryAccountIntent": "return_performance",
  "businessItems": [],
  "summary": {
    "title": "今年收益概况",
    "narrative": "基于真实数据的直接回答。"
  },
  "followUp": []
}
```

简单任务禁止出现 `conclusion` 键。

复杂任务：

```json
{
  "scene": "问账户",
  "taskComplexity": "complex",
  "primaryAccountIntent": "account_overview",
  "businessItems": [],
  "summary": {
    "title": "账户诊断摘要",
    "narrative": "基于真实数据的核心发现。"
  },
  "conclusion": {
    "title": "综合结论",
    "narrative": "基于同一批证据的跨维度判断。"
  },
  "followUp": []
}
```

## 脚本职责

`compose_result.py`：

- simple 要求一个 Summary 且禁止 Conclusion；
- complex 要求一个 Summary 和一个 Conclusion；
- 校验固定业务 Section 标题和 narrative 未被修改；
- 校验 Section 顺序、卡片映射、卡片参数和重复 cardId；
- 阻止账户诊断类与自选基金类混排；
- 自动补齐 `section.cardId`；
- 对 `followUp` 去重并最多保留三条；
- 补齐 `version`、`meta` 和固定风险提示。

脚本失败时修正输入并重试，不得绕过脚本手工拼接。

## 最终输出

最终结果严格保持：

```json
{
  "version": "2.2",
  "meta": {
    "scene": "问账户",
    "intent": "return_performance"
  },
  "sections": [],
  "cards": [],
  "risk_warning": "投资有风险，请结合自身情况审慎决策。",
  "followUp": []
}
```

顶层只能包含上述六个字段。不得输出 `originalQuery`、`taskComplexity`、账户计划、MCP 原始数据、身份信息或调试字段。
