---
name: account-return-attribution
description: "将 return_attribution 账户意图映射为 ACC-15 收益归因、ACC-16 收益构成或 ACC-17 区间收益归因卡片。Account Intent Router 输出收益原因、来源构成或区间归因诉求，需要生成账户卡片响应 JSON 时使用。"
---

# Account Return Attribution

作为账户域 Phase C，只处理 `intent = "return_attribution"` 的单条路由记录。根据归因层级选择 ACC-15～ACC-17，不生成或猜测收益来源。

## 输入

```json
{
  "intent": "return_attribution",
  "subQuery": "我的钱为什么亏了",
  "entities": {}
}
```

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-15 | `acc15-return-attribution` | 收益归因 | 为什么赚钱或亏钱、主要靠什么赚 |
| ACC-16 | `acc16-return-composition` | 收益构成 | 收益来自哪些部分、哪类资产贡献更多 |
| ACC-17 | `acc17-period-attribution` | 区间收益归因 | 指定时间或基金的收益来源、买入位置、回撤 |

## 规则

1. 泛问账户为什么赚亏或主要贡献与拖累时输出 ACC-15。
2. 询问收益由哪些账户、产品或资产类别构成时输出 ACC-16。
3. 明确指定时间区间、具体基金、买入位置或回撤时输出 ACC-17。
4. 同时询问收益构成和原因时，按诉求先后输出 ACC-16 与 ACC-15。
5. 无法判断具体归因层级时输出 ACC-15。
6. 所有卡片固定使用 `deferred`，不得生成具体贡献、拖累、买入点或回撤数据。
7. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "return_attribution"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您整理收益归因信息。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-15",
      "type": "acc15-return-attribution",
      "title": "收益归因",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc15",
        "params": {
          "userId": "${userId}",
          "date": "latest"
        }
      }
    }
  ]
}
```
