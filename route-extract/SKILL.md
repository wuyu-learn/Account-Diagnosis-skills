---
name: route-extract
description: "对 AI 投顾用户问题进行原文透传、场景分类、多场景拆分和实体抽取，覆盖问账户、问市场、问基金、问投教和问策略。用户提出投资相关问题，需要保留原始问题、识别业务场景、拆分子问题或生成下游路由 JSON 时使用。"
---

# Route & Extract（意图识别与实体抽取）

AI 投顾系统的统一入口（三段式流水线 Phase A）。识别用户问题所属业务场景，抽取后续 Skill 所需的关键实体。**只输出路由结果，不回答用户问题本身。**

## 输入

输入为用户当前一条自然语言问题。只处理当前问题；仅当调用上下文中明确提供了相关历史对话时，才可用历史对话补全指代或省略信息。不得假设或编造未提供的上下文。

## 任务

对每条用户输入完成两件事：

1. **原文透传**：将用户当前问题逐字写入 `originalQuery`，不得摘要、改写或清洗。
2. **场景分类（Scene Classification）**：支持单场景和多场景。一句话包含多个问题时拆分为多个 `subQuery`，按 `weight` 降序排列。输出 `primaryScene` 与 `isMultiScene`。
3. **实体抽取（Entity Extraction）**：提取基金名称、基金代码、基金公司、基金经理、市场主题、策略名称，供下游业务 Skill 使用。

## 场景目录

`scenes[].scene` 和 `primaryScene` 只允许使用以下五种场景：

| Scene | 覆盖范围 |
| ----- | -------- |
| 问账户 | 账户资产、持仓、收益、收益率、收益归因、资产结构、交易记录、账户诊断、自选或关注基金 |
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
  "originalQuery": "帮我看看永赢先进制造怎么样，另外半导体现在行情如何？",
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
  "isMultiScene": true,
  "orchestration": null,
  "clarify": {
    "needed": false,
    "question": null
  }
}
```

## 识别规则

1. 一个问题可以命中一个或多个场景记录；一个场景记录只包含一个可独立处理的子问题。
2. 同一场景包含多个可独立处理的子问题时，可以输出多条相同 `scene` 的记录。
3. `scenes` 按 `weight` 从高到低排序。
4. `primaryScene` 为 `weight` 最高记录的 `scene`；权重相同时取数组中第一条记录。
5. `isMultiScene = true` 当且仅当 `scenes` 包含两个及以上场景记录，否则为 `false`，不要求记录的 `scene` 互不相同。
6. `subQuery` 仅包含该记录对应的子问题，不得混入其他场景内容；必须保留该子问题中的关键实体，使下游能根据 `subQuery` 判断实体归属。
7. `originalQuery` 必须逐字等于当前用户问题；即使问题为空、无关或使用历史上下文补全，也不得改写该字段。
8. `entities` 汇总当前问题中明确出现的全部实体。六个键必须全部出现，没有命中时使用空数组 `[]`；不得编造原文或明确历史上下文中未出现的实体。
9. 用户表达不完整时，仅可使用明确提供的历史对话补全。没有相关上下文且仍可判断时，选择最接近的场景并降低 `weight`，一般不高于 `0.6`。
10. 输入为空、只有寒暄，或与投资业务完全无关时，不强行归类，输出空 `scenes`、空实体、`primaryScene: null` 和 `isMultiScene: false`，但仍保留 `originalQuery`。
11. `orchestration` 为下游编排预留字段，当前阶段固定输出 `null`。
12. `clarify` 必须包含 `needed` 和 `question`。当前阶段不发起澄清，固定输出 `{ "needed": false, "question": null }`。
13. 所有顶层字段必须完整输出，不得省略；输出必须是合法 JSON，不添加解释性文字。

## 边界情况

- **基金经理/基金公司出现在基金产品问题中**：主场景仍是 `问基金`，人名/公司名照常抽取进 `manager_names` / `company_names`。
- **具体基金分析 vs 个性化策略**：询问某只基金本身的介绍、表现、风险或是否值得买，属于 `问基金`；结合用户自身资产、目标或风险承受能力询问买卖、配置或调仓建议，属于 `问策略`。一个问题同时要求基金分析和个性化建议时，拆分为 `问基金` 与 `问策略`。
- **"我该买什么/怎么配"类问题**：未指定具体产品的买入、配置和调仓建议属于 `问策略`。
- **"什么是 XX"类概念问题**：属于 `问投教`，即使 XX 是某个策略名（策略名仍抽取进 `strategy_names`）。
- **"我的收益/我的持仓"类问题**：属于 `问账户`，不是 `问基金`。
- **"我的自选/我的关注"类问题**：询问自选或关注基金的估值、净值更新和当日涨跌时属于 `问账户`；询问某只基金产品本身的介绍、长期业绩或风险时仍属于 `问基金`。
- **投资相关但无法准确归类**：选择最接近的场景，`weight` 不高于 `0.5`。

## 示例

输入：`帮我看看永赢先进制造怎么样，另外半导体现在行情如何？`

```json
{
  "originalQuery": "帮我看看永赢先进制造怎么样，另外半导体现在行情如何？",
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
  "isMultiScene": true,
  "orchestration": null,
  "clarify": {
    "needed": false,
    "question": null
  }
}
```

输入：`什么是基金定投？`

```json
{
  "originalQuery": "什么是基金定投？",
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
  "isMultiScene": false,
  "orchestration": null,
  "clarify": {
    "needed": false,
    "question": null
  }
}
```
