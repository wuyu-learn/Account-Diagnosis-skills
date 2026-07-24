# Account Intent Router 测试用例

每个用例包含上游 Route & Extract 的输出（输入）与期望的二级路由输出。期望输出已按 account-intent-router.md 的规则人工校验：`accountScenes` 按 weight 降序、`primaryAccountIntent` = 最高 weight 意图、`isMultiAccountIntent` ⇔ accountScenes ≥ 2、intent 只取五种合法值。

自动化回归：运行 `python validate.py`，校验本文件中全部输出 JSON 的结构规则（weight 允许 ±0.15 浮动，不在脚本校验范围内）。

---

## 1. 单意图 · 收益表现

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.95, "subQuery": "我今年赚了多少钱" }
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
    { "intent": "return_performance", "weight": 0.92, "subQuery": "我今年赚了多少钱" }
  ],
  "primaryAccountIntent": "return_performance",
  "isMultiAccountIntent": false
}
```

---

## 2. 单意图 · 账户资产总览

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.94, "subQuery": "我账户里现在一共有多少钱" }
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
    { "intent": "account_overview", "weight": 0.93, "subQuery": "我账户里现在一共有多少钱" }
  ],
  "primaryAccountIntent": "account_overview",
  "isMultiAccountIntent": false
}
```

---

## 3. 单意图 · 持仓结构

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.93, "subQuery": "我的资产里股票和基金各占多少" }
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
    { "intent": "holding_structure", "weight": 0.91, "subQuery": "我的资产里股票和基金各占多少" }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": false
}
```

---

## 4. 单意图 · 收益归因

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.92, "subQuery": "我这个月为什么亏钱了" }
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
    { "intent": "return_attribution", "weight": 0.9, "subQuery": "我这个月为什么亏钱了" }
  ],
  "primaryAccountIntent": "return_attribution",
  "isMultiAccountIntent": false
}
```

---

## 5. 单意图 · 账户操作

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

---

## 6. 多意图 · 账户资产总览 + 收益表现

输入：

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

---

## 7. 多意图 · 收益表现 + 收益归因（结果 + 原因）

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.93, "subQuery": "我今年收益多少，主要是哪些基金贡献的" }
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
    { "intent": "return_performance", "weight": 0.9, "subQuery": "我今年收益多少" },
    { "intent": "return_attribution", "weight": 0.84, "subQuery": "主要是哪些基金贡献的" }
  ],
  "primaryAccountIntent": "return_performance",
  "isMultiAccountIntent": true
}
```

---

## 8. 边界 · 提及具体基金的账户问题（实体由上游处理）

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.85, "subQuery": "我持仓里的易方达蓝筹亏了多少" }
  ],
  "entities": {
    "fund_names": ["易方达蓝筹"], "fund_codes": [], "manager_names": [],
    "company_names": ["易方达"], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": true
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "return_performance", "weight": 0.88, "subQuery": "我持仓里的易方达蓝筹亏了多少" }
  ],
  "primaryAccountIntent": "return_performance",
  "isMultiAccountIntent": false
}
```

---

## 9. 表达不完整 · 降权处理

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.55, "subQuery": "那个收益呢" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

（无上下文时"那个收益"指代不明，选最接近的 `return_performance` 并降权。）

输出：

```json
{
  "accountScenes": [
    { "intent": "return_performance", "weight": 0.55, "subQuery": "我的收益是多少" }
  ],
  "primaryAccountIntent": "return_performance",
  "isMultiAccountIntent": false
}
```

---

## 10. 无问账户场景 · 空输出

输入：

```json
{
  "scenes": [
    { "scene": "问市场", "weight": 0.93, "subQuery": "最近新能源板块为什么这么火" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": ["新能源"], "strategy_names": []
  },
  "primaryScene": "问市场",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [],
  "primaryAccountIntent": null,
  "isMultiAccountIntent": false
}
```

---

## 11. 基金账户怎么样 · 三意图拆分

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.94, "subQuery": "我基金账户怎么样" }
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

---

## 12. 投顾组合怎么样 · 三意图拆分

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.93, "subQuery": "我的稳健回报组合怎么样" }
  ],
  "entities": {
    "fund_names": [], "fund_codes": [], "manager_names": [],
    "company_names": [], "market_subjects": [], "strategy_names": ["稳健回报"]
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

输出：

```json
{
  "accountScenes": [
    { "intent": "account_overview", "weight": 0.87, "subQuery": "我的稳健回报组合当前情况" },
    { "intent": "return_performance", "weight": 0.83, "subQuery": "我的稳健回报组合收益怎么样" },
    { "intent": "holding_structure", "weight": 0.79, "subQuery": "我的稳健回报组合里买了什么" }
  ],
  "primaryAccountIntent": "account_overview",
  "isMultiAccountIntent": true
}
```

---

## 13. 持仓列表 + 单品表现

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

---

## 14. 持仓分布 + 集中度

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.91, "subQuery": "我的钱怎么分布，是否集中" }
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
    { "intent": "holding_structure", "weight": 0.9, "subQuery": "我的钱怎么分布" },
    { "intent": "holding_structure", "weight": 0.85, "subQuery": "持仓是否集中" }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": true
}
```

---

## 15. 单只基金持有情况

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.89, "subQuery": "我这只基金持有得怎么样" }
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
    { "intent": "holding_structure", "weight": 0.86, "subQuery": "我这只基金持有表现怎么样" },
    { "intent": "return_performance", "weight": 0.8, "subQuery": "我这只基金收益怎么样" }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": true
}
```

---

## 16. 现金宝收益

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.88, "subQuery": "现金宝收益" }
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
    { "intent": "return_performance", "weight": 0.9, "subQuery": "现金宝收益" }
  ],
  "primaryAccountIntent": "return_performance",
  "isMultiAccountIntent": false
}
```

---

## 17. 为什么调仓

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.87, "subQuery": "为什么调仓" }
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
    { "intent": "account_operations", "weight": 0.88, "subQuery": "为什么调仓" }
  ],
  "primaryAccountIntent": "account_operations",
  "isMultiAccountIntent": false
}
```

---

## 18. 收益归因 + 操作

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.86, "subQuery": "这段时间我这只基金赚的是怎么来的，我买在什么位置" }
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
    { "intent": "return_attribution", "weight": 0.87, "subQuery": "这段时间我这只基金赚的是怎么来的" },
    { "intent": "account_operations", "weight": 0.82, "subQuery": "我买在什么位置" }
  ],
  "primaryAccountIntent": "return_attribution",
  "isMultiAccountIntent": true
}
```

---

## 19. 专户产品怎么样

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.85, "subQuery": "我专户产品怎么样" }
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
    { "intent": "account_overview", "weight": 0.84, "subQuery": "我专户产品当前情况" },
    { "intent": "return_performance", "weight": 0.8, "subQuery": "我专户产品收益怎么样" },
    { "intent": "holding_structure", "weight": 0.76, "subQuery": "我专户产品里有哪些" }
  ],
  "primaryAccountIntent": "account_overview",
  "isMultiAccountIntent": true
}
```

---

## 20. 投顾账户里几个组合

输入：

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.84, "subQuery": "投顾账户里几个组合" }
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
    { "intent": "holding_structure", "weight": 0.9, "subQuery": "投顾账户里几个组合" }
  ],
  "primaryAccountIntent": "holding_structure",
  "isMultiAccountIntent": false
}
```
