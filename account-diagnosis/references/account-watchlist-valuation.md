---
name: account-watchlist-valuation
description: "将 watchlist_valuation 账户意图映射为 ACC-18 自选基金估值卡，处理自选或关注基金的当日估值、净值更新和涨跌查询。Account Intent Router 输出自选基金估值诉求，需要生成账户卡片响应 JSON 时使用。"
---

# Account Watchlist Valuation

作为账户域 Account Step 2（卡片选择与计划归一化），只处理 `intent = "watchlist_valuation"` 的单条路由记录。输出 ACC-18 自选基金估值卡，不获取、生成或猜测估值、净值和涨跌数据。

## 输入

```json
{
  "intent": "watchlist_valuation",
  "subQuery": "我关注的基金今天涨跌怎么样",
  "entities": {}
}
```

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-18 | `acc18-watchlist-valuation` | 自选基金估值卡 | 自选基金当日表现、估值、净值更新、关注基金涨跌 |

## 规则

1. 确认问题指向自选或关注基金，而不是账户中实际持有的基金。
2. 询问当日表现、盘中估值、最新净值、净值是否更新或涨跌排序时输出 ACC-18。
3. `subQuery` 中出现具体基金时保留基金名称或代码，以便数据查询过滤。
4. 固定输出 `dataMode: "deferred"` 且 `data` 为空对象，不得生成具体估值、净值或涨跌数据。
5. 不检查卡片接口或数据状态，命中时始终输出 ACC-18。
6. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "watchlist_valuation",
  "subQuery": "我关注的基金今天涨跌怎么样",
  "cards": [
    {
      "cardId": "ACC-18",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```
