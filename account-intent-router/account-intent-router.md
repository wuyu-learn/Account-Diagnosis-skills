---
name: account-intent-router
description: "账户二级意图路由：subQuery 子意图识别（账户总览/持仓结构/收益表现/收益归因/账户操作），多意图拆分，输出严格 JSON。"
---

# Account Intent Router（账户二级意图路由）

AI 投顾系统的账户域二级路由（三段式流水线 Phase B）。当上游 **Route & Extract** 输出的 `scenes` 中包含 `问账户` 时，对其 `subQuery` 做账户子意图识别，把请求分发给对应的账户能力 Skill。**只输出路由结果，不做任何业务分析或回答。**

## 任务

1. 从上游输出的 `scenes` 数组中取出 `scene = "问账户"` 的记录，以其 `subQuery` 作为本 Skill 的识别输入。
2. **账户子意图分类**：支持单意图和多意图。一句话包含多个账户诉求时拆分为多条 `subQuery`，按 `weight` 降序排列，输出 `primaryAccountIntent` 与 `isMultiAccountIntent`。

## 子意图目录（`intent` 只允许以下五种）

| 意图中文 | 意图代码 `intent` | 覆盖范围 |
| -------- | ----------------- | -------- |
| 账户资产总览 | `account_overview` | 总资产、账户余额、持有数量、某账户/产品当前金额等整体情况："我有多少钱"、"账户总资产"、"我基金账户怎么样"、"我货币基金多少钱"、"我专户产品怎么样" |
| 持仓结构 | `holding_structure` | 持仓列表、单品表现、持仓分布、集中度："我都买了哪些"、"每只怎么样"、"我的钱怎么分布"、"是否集中"、"组合里买了啥" |
| 收益表现 | `return_performance` | 收益结果本身："赚了多少"、"收益率多少"、"跑赢大盘了吗"、"每天/每月/每年收益"、"哪段时间赚亏" |
| 收益归因 | `return_attribution` | 收益/亏损的产生原因："为什么赚钱/亏钱"、"主要靠什么赚的"、"收益从哪几块来的"、"哪类资产赚得多" |
| 账户操作 | `account_operations` | 交易、调仓、买卖位置等操作记录："都调过哪些仓"、"上次调仓干了啥"、"为什么调仓"、"我买在什么位置" |

## 输出格式

只输出合法 JSON，不要 markdown 代码块，不要任何解释性文字：

```json
{
  "accountScenes": [
    {
      "intent": "holding_structure",
      "weight": 0.92,
      "subQuery": "我的持仓有哪些"
    }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": false
}
```

## 判断规则

1. 一个 `subQuery` 可以命中多个账户子意图，命中多个时必须拆分。
2. `accountScenes` 按 `weight` 从高到低排序。
3. `primaryAccountIntent` 为 `weight` 最高的意图；权重相同时取数组中第一个。
4. `isMultiAccountIntent = true` 当且仅当命中两个及以上子意图，否则为 `false`。
5. 拆分后的 `subQuery` 仅包含对应该意图的子问题，不得混入其他意图内容。
6. 表达不完整时，结合上下文推断最可能的意图；无法判断时选择最接近的意图，并适当降低 `weight`（一般 ≤ 0.6）。
7. 输入的 `scenes` 中不存在 `问账户` 记录时，输出 `"accountScenes": []`、`"primaryAccountIntent": null`、`"isMultiAccountIntent": false`。
8. 输出必须是合法 JSON，不添加解释性文字。

## 典型查询分类

### 账户资产总览 `account_overview`

- 我有多少钱
- 账户总资产
- 某个账户怎么样（仅问整体/金额时）
- 我基金账户怎么样
- 我投顾账户整体怎么样
- 我货币基金多少钱 / 现金宝里有多少
- 我专户产品怎么样（仅问当前情况/金额时）

### 持仓结构 `holding_structure`

- 我的钱构成
- 我都买了哪些
- 我的持仓有哪些
- 查看我的持仓 / 看持仓
- 每只怎么样
- 我这只基金持有得怎么样
- 基金账户里有哪些
- 投顾账户里几个组合
- 组合里买了啥
- 我的钱怎么分布
- 在各维度怎么分
- 是否集中 / 有没有重仓风险

### 收益表现 `return_performance`

- 基金账户赚了多少
- 投顾赚了多少
- 这个组合赚了多少
- 现金宝收益
- 我赚了多少
- 收益怎么样
- 跑赢大盘了吗
- 我每天/每月/每年收益
- 哪段时间赚亏
- 回撤多大

### 收益归因 `return_attribution`

- 我的钱为什么赚/亏
- 主要靠什么赚的
- 我的收益从哪几块来的
- 哪类资产赚得多
- 这段时间我这只基金赚的是怎么来的

### 账户操作 `account_operations`

- 我这组合都调过哪些仓
- 上次调仓干了啥
- 为什么调仓
- 我买在什么位置

## 多意图拆分规则

以下“怎么样”类问题通常同时包含总览、结构、收益，需要拆分为多条：

| 原问题 | 拆分结果 |
| ------ | -------- |
| 我基金账户怎么样 | `account_overview` + `holding_structure` + `return_performance` |
| 我的稳健回报组合怎么样 | `account_overview` + `holding_structure` + `return_performance` |
| 某个账户怎么样 | `account_overview` + `holding_structure` + `return_performance` |
| 我专户产品怎么样 | `account_overview` + `holding_structure` + `return_performance` |
| 我这只基金持有得怎么样 | `holding_structure` + `return_performance` |

拆分权重建议：
- 当用户明确提到“赚/收益/怎么样”时，`return_performance` 权重最高；
- 当用户明确提到“有哪些/买了什么/分布”时，`holding_structure` 权重最高；
- 当用户仅说“X 怎么样”无其他限定，默认 `account_overview` 最高，再拆 `holding_structure`、`return_performance`。

## 边界情况

- **收益表现 vs 收益归因**：问“结果”（多少、收益率、跑赢、时段）是 `return_performance`；问“原因”（为什么、靠什么、从哪来）是 `return_attribution`。同时问结果和原因（如“今年赚了多少，靠什么赚的”）拆为双意图。
- **账户资产总览 vs 持仓结构**：问“总量/余额/金额/怎么样”（多少钱、里有多少）是 `account_overview`；问“比例/构成/分布/买了哪些/是否集中”是 `holding_structure`。
- **持仓结构 vs 账户操作**：问“当前买了什么”是 `holding_structure`；问“调过哪些仓/为什么调/买在什么位置”是 `account_operations`。
- **提及具体基金/组合/账户**：仍按上述规则判账户子意图；具体实体由上游 Route & Extract 抽取，本 Skill 不处理实体，但需在 `subQuery` 中保留。
- **完全无法归类**：选择最接近的意图，`weight` ≤ 0.5。

## 示例

更多见 [test-cases.md](test-cases.md)。

输入（上游 Route & Extract 输出）：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.95, "subQuery": "我的账户有多少钱，今年收益怎么样" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "account_overview", "weight": 0.9, "subQuery": "我的账户有多少钱" },
    { "intent": "return_performance", "weight": 0.85, "subQuery": "今年收益怎么样" }
  ],
  "primaryAccountIntent": "account_overview",
  "isMultiAccountIntent": true
}
```

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.94, "subQuery": "我的基金账户怎么样" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "account_overview", "weight": 0.88, "subQuery": "我的基金账户当前情况" },
    { "intent": "return_performance", "weight": 0.82, "subQuery": "我的基金账户收益怎么样" },
    { "intent": "holding_structure", "weight": 0.78, "subQuery": "我的基金账户里有哪些" }
  ],
  "primaryAccountIntent": "account_overview",
  "isMultiAccountIntent": true
}
```

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.92, "subQuery": "我都买了哪些，哪只表现最好" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "holding_structure", "weight": 0.91, "subQuery": "我都买了哪些" },
    { "intent": "holding_structure", "weight": 0.86, "subQuery": "哪只持仓表现最好" }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": true
}
```

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.9, "subQuery": "我这组合都调过哪些仓" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "account_operations", "weight": 0.92, "subQuery": "我这组合都调过哪些仓" }
  ],
  "primaryAccountIntent": "account_operations",
  "isMultiAccountIntent": false
}
```
