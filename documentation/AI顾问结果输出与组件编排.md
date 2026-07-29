# AI 顾问结果输出与组件编排

## 文档定位

本文档说明 AI 顾问生成结果的内容结构和页面编排方式，重点描述文字解读、数据卡片、结论、追问及风险提示之间的关系。

## 结果结构

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

| 字段 | 职责 |
| --- | --- |
| `version` | 标识当前结果协议版本 |
| `meta` | 描述当前场景、意图及业务上下文 |
| `sections` | 组织回答内容、文字解读和页面展示顺序 |
| `cards` | 保存卡片组件的数据载荷，包括实际数据或后续取数信息 |
| `risk_warning` | 展示统一风险提示 |
| `followUp` | 提供可点击的后续问题 |

## 顶层约束

- `meta.scene` 和 `meta.intent` 决定响应骨架。
- `sections[]` 和 `cards[]` 是前端消费的主要内容。
- `risk_warning` 必须展示在回答末尾。
- `followUp` 可以为空数组。
- 不再使用顶层 `text` 和 `conclusion`；结论统一放入 `sections[]`。

## Sections

`sections[]` 是结果内容和展示顺序的权威来源。每个 section 表示一个页面内容区块。

```json
{
  "type": "performance",
  "title": "业绩表现",
  "narrative": "近一年收益表现较好。",
  "cardId": "CARD-ID"
}
```

| 字段 | 职责 |
| --- | --- |
| `type` | 声明内容区块的类型 |
| `title` | 区块标题 |
| `narrative` | 结果摘要、解释或分析文字 |
| `cardId` | 可选，关联需要在当前区块展示的数据卡片 |

section 可以是纯文字区块，也可以关联一张数据卡片：

```text
section.title
→ section.narrative
→ cardId 对应的数据卡片
```

`narrative` 可以概括或解释卡片结果。卡片的数据载荷保存在 `cards[]` 中；该载荷可以是实际数据，也可以是后续取数信息。

## Section 类型

基金解读页面结构（按展示顺序）：

```text
基金解读
├── 核心观点 summary
├── 业绩表现 performance
├── 风险分析 risk
├── 持仓分析 holdings
└── 综合建议 conclusion
```

| `type` | 名称 |
| --- | --- |
| `summary` | 核心观点 |
| `performance` | 业绩表现 |
| `risk` | 风险分析 |
| `holdings` | 持仓分析 |
| `conclusion` | 综合建议 |

其他场景（问账户、问市场等）的页面结构和 section 类型待补充。

## Cards

`cards[]` 是卡片数据池，不决定页面展示顺序。section 通过 `cardId` 查找相同标识的卡片。

```json
{
  "cardId": "CARD-ID",
  "dataMode": "inline",
  "data": {}
}
```

前端的基本处理流程：

```text
按顺序遍历 sections[]
→ 渲染标题和文字内容
→ 检查是否存在 cardId
→ 从 cards[] 查找对应卡片
→ 在当前区块中渲染卡片
```

## 典型编排

```text
概要说明
→ 结果分析 + 数据卡片
→ 风险分析 + 数据卡片
→ 综合结论
→ 后续问题
→ 风险提示
```

其中：

- 概要、分析和结论属于 `sections[]`。
- 图表及其他数据组件属于 `cards[]`。
- 后续问题来自 `followUp`。
- 页面底部风险提示来自 `risk_warning`。

## 结构边界

- `sections[]` 负责“表达什么、按什么顺序展示”。
- `cards[]` 负责“使用什么数据渲染组件”。
- section 不应复制完整卡片数据。
- card 不负责标题、分析文字及页面顺序。
- 没有 `cardId` 的 section 按纯文字区块展示。
- 前端不得根据 `cards[]` 的排列顺序重新组织回答。
