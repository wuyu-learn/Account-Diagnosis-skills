---
name: result-composer
description: "调度 AI 顾问最终结果编排：理解已完成取数的卡片结果，生成有数据依据的 section 文案，并调用 compose_result.py 拼接和校验统一响应 JSON。上游已经完成场景路由、意图路由、选卡与取数，需要输出最终页面结果时使用。"
---

# Result Composer

作为 AI 顾问流水线的最终编排阶段。不要重新分类意图、重新选择卡片或补造业务数据。

职责分工：

- `SKILL.md`：理解真实卡片数据，生成 section 标题、摘要、结论和追问，并调度脚本。
- `scripts/compose_result.py`：确定性拼接 `sections` 与 `cards`，补齐顶层结构并校验协议。

## 运行位置

```text
场景路由
→ 业务意图路由
→ 选择卡片并生成取数计划
→ 获取卡片数据
→ Result Composer
→ 前端渲染
```

优先在实际数据已经返回后运行。只有取数请求而没有数据结果时，不得生成具体数值、趋势或判断。

## 输入

接收上游路由结果、卡片结果和合规提示。将其转换为脚本需要的中间 JSON：

```json
{
  "version": "2.2",
  "meta": {
    "scene": "问账户",
    "intent": "return_performance"
  },
  "items": [
    {
      "section": {
        "type": "performance",
        "title": "收益表现",
        "narrative": "根据真实数据生成的结果摘要。"
      },
      "card": {
        "cardId": "ACC-13-B",
        "dataMode": "inline",
        "data": {
          "status": "available"
        }
      }
    }
  ],
  "risk_warning": "投资有风险，请结合自身情况审慎决策。",
  "followUp": []
}
```

输入约束：

- 原样保留上游确定的 `meta`，不要修改场景或意图。
- 按预期展示顺序生成 `items[]`。
- 每个 item 必须包含一个 `section`，并可以包含一张 `card`。
- 卡片只保留 `cardId`、`dataMode` 和 `data`。
- deferred 卡片的 `data.request` 必须包含 `method`、`path` 和 `params`，且 cardId 与接口路径符合已确认映射。
- 使用上游或场景合规规则提供的 `risk_warning`，不要自行编造合规文案。

## 工作流

1. 校验上游是否提供 `version`、`meta`、卡片结果和 `risk_warning`。
2. 根据每项真实数据生成 `section.title` 和 `section.narrative`。
3. 只陈述输入数据能够支持的事实，不复制完整卡片数据。
4. 将卡片规范化为 `cardId`、`dataMode` 和 `data`。
5. 按展示顺序构造 `items[]`。
6. 生成或筛选不超过 3 条 `followUp`，不得重复当前问题。
7. 将中间 JSON 传给 `scripts/compose_result.py`。
8. 脚本失败时根据错误修正中间 JSON 并重新执行，不要绕过校验手工拼接。
9. 将脚本标准输出作为最终结果，只输出合法 JSON。

执行方式：

```bash
python3 scripts/compose_result.py --input normalized-input.json
```

也可以通过标准输入传入 JSON：

```bash
python3 scripts/compose_result.py < normalized-input.json
```

## Sections

```json
{
  "type": "performance",
  "title": "收益表现",
  "narrative": "今年以来账户收益为……"
}
```

- 使用 `title` 和 `narrative`，不要使用 `content`。
- 脚本会根据同一 item 中的 `card.cardId` 自动补齐 `section.cardId`。
- 没有卡片的概要或结论 section 可以省略 `cardId`。
- 不要生成“已为您整理”等没有结果信息的占位摘要。
- `zero` 表示真实值为零，不得解释为无数据。
- `empty` 表示当前范围内没有数据。
- `unavailable` 表示暂时无法获取，不得推断趋势或结论。
- 数据仍为 `deferred` 请求时，只说明正在获取，不生成结果判断。

## Cards

```json
{
  "cardId": "ACC-13-B",
  "dataMode": "inline",
  "data": {}
}
```

- 保持 `cardId` 与上游一致。
- 将实际组件数据或取数信息放入 `data`。
- 不输出根级 `type`、`chartType`、`title` 或 `dataQuery`。
- 不把缺失值改写为 `0`，不生成示例数据填充空字段。
- 同一个 `cardId` 在一次响应中只能出现一次。

## 脚本校验

`scripts/compose_result.py` 负责：

- 校验 `version`、`meta`、`items` 和 `risk_warning`。
- 拒绝 section 中未定义的 `content`。
- 拒绝 card 根级的额外字段。
- 校验 `dataMode` 只能为 `inline` 或 `deferred`。
- 校验 `deferred` 卡片包含 `data.request`。
- 校验请求方法为 `GET`、请求字段完整，并拒绝 cardId 未确认或接口路径错配。
- 自动关联 `section.cardId` 与 `card.cardId`。
- 拒绝重复或相互冲突的 `cardId`。
- 保持 `items[]` 的展示顺序。
- 对 `followUp` 去重并最多保留 3 条。

## 输出

脚本输出完整响应：

```json
{
  "version": "2.2",
  "meta": {},
  "sections": [],
  "cards": [],
  "risk_warning": "",
  "followUp": []
}
```

必须包含全部六个顶层字段。不要输出顶层 `text` 或 `conclusion`；结论作为 `sections[]` 中的内容区块。
