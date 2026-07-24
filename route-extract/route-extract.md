---
name: route-extract
description: "AI 投顾统一入口：意图识别与场景分类（问账户/市场/基金/投教/策略）、多场景拆分、实体抽取，输出严格 JSON。"
---

# Route & Extract（意图识别与实体抽取）

AI 投顾系统的统一入口（三段式流水线 Phase A）。识别用户问题所属业务场景，抽取后续 Skill 所需的关键实体。**只输出路由结果，不回答用户问题本身。**

## 任务

对每条用户输入完成两件事：

1. **场景分类（Scene Classification）**：支持单场景和多场景。一句话包含多个问题时拆分为多个 `subQuery`，按 `weight` 降序排列。输出 `primaryScene` 与 `isMultiScene`。
2. **实体抽取（Entity Extraction）**：提取基金名称、基金代码、基金公司、基金经理、市场主题、策略名称，供下游业务 Skill 使用。

## 场景目录（primaryScene 只允许以下五种）

| Scene | 覆盖范围 |
| ----- | -------- |
| 问账户 | 账户资产、持仓、收益、收益率、收益归因、资产结构、交易记录、账户诊断 |
| 问市场 | 宏观经济、市场行情、行业、板块、指数、热点、市场观点 |
| 问基金 | 具体基金产品：介绍、分析、业绩、风险、持仓、基金经理、基金比较、是否值得买 |
| 问投教 | 基金知识、投资知识、专业术语解释、投资理念、规则制度、概念科普 |
| 问策略 | 资产配置、投资策略、定投策略、组合配置、买卖建议、调仓建议 |

## 实体定义

| 字段 | 含义 | 示例 |
| ---- | ---- | ---- |
| `fund_names` | 基金全称/简称/常见别名 | "永赢先进制造" |
| `fund_codes` | 基金代码（6 位数字或字母数字） | "018124" |
| `manager_names` | 基金经理姓名 | "张坤" |
| `company_names` | 基金公司名称 | "易方达" |
| `market_subjects` | 市场主题、行业、板块、概念、指数 | "半导体"、"沪深300" |
| `strategy_names` | 策略名称 | "定投"、"网格"、"杠铃策略" |

## 输出格式

只输出合法 JSON，不要 markdown 代码块，不要任何解释性文字：

```json
{
  "scenes": [
    {
      "scene": "问基金",
      "weight": 0.92,
      "subQuery": "永赢先进制造怎么样"
    },
    {
      "scene": "问市场",
      "weight": 0.74,
      "subQuery": "半导体现在行情如何"
    }
  ],
  "entities": {
    "fund_names": ["永赢先进制造"],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": ["半导体"],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": true
}
```

## 识别规则

1. 一个问题可以命中多个场景。
2. `scenes` 按 `weight` 从高到低排序。
3. `primaryScene` 为 `weight` 最高的场景；权重相同时取数组中第一个。
4. `isMultiScene = true` 当且仅当命中两个及以上场景，否则为 `false`。
5. `subQuery` 仅包含对应场景的子问题，不得混入其他场景内容；保留子问题中的关键实体。
6. 用户表达不完整时，结合上下文推断最可能的场景；无法判断时选择最接近的场景，并适当降低 `weight`（一般 ≤ 0.6）。
7. `entities` 的六个键必须全部出现，没有命中时为空数组 `[]`；不要编造原文中未出现的实体。
8. 输出必须是合法 JSON，不添加解释性文字。

## 边界情况

- **基金经理/基金公司出现在基金产品问题中**：主场景仍是 `问基金`，人名/公司名照常抽取进 `manager_names` / `company_names`。
- **"我该买什么/怎么配"类问题**：属于 `问策略`；若同时点名具体基金，则同时命中 `问基金`。
- **"什么是 XX"类概念问题**：属于 `问投教`，即使 XX 是某个策略名（策略名仍抽取进 `strategy_names`）。
- **"我的收益/我的持仓"类问题**：属于 `问账户`，不是 `问基金`。
- **完全无法归类**：选择最接近的场景，`weight` ≤ 0.5。

## 示例

更多见 [test-cases.md](test-cases.md)。

输入：`帮我看看永赢先进制造怎么样，另外半导体现在行情如何？`

```json
{
  "scenes": [
    { "scene": "问基金", "weight": 0.92, "subQuery": "永赢先进制造怎么样" },
    { "scene": "问市场", "weight": 0.74, "subQuery": "半导体现在行情如何" }
  ],
  "entities": {
    "fund_names": ["永赢先进制造"],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": ["半导体"],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": true
}
```

输入：`什么是基金定投？`

```json
{
  "scenes": [
    { "scene": "问投教", "weight": 0.95, "subQuery": "什么是基金定投" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": ["基金定投"]
  },
  "primaryScene": "问投教",
  "isMultiScene": false
}
```
