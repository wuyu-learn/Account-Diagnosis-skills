---
name: account-asset-overview
description: "将 account_overview 账户意图映射为 ACC-01 至 ACC-10 的资产总览、账户详情、持有详情、投顾组合或调仓记录卡片。Account Intent Router 输出资产总览诉求，需要生成账户卡片响应 JSON 时使用。"
---

# Account Asset Overview

作为账户域 Phase C，只处理 `intent = "account_overview"` 的单条路由记录。根据账户层级和产品类型选择 ACC-01～ACC-10，不生成或猜测账户数据。

## 输入

```json
{
  "intent": "account_overview",
  "subQuery": "我的基金账户怎么样",
  "entities": {}
}
```

`intent` 和 `subQuery` 对应 Account Intent Router 的一条 `accountScenes` 记录；`entities` 由编排层从 Phase A 原样传入。

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-01 | `acc01-total-asset` | 账户总资产 | 总资产、我的钱构成、未指定类型的账户整体情况 |
| ACC-02 | `acc02-fund-account` | 基金账户详情 | 基金账户整体、收益和账户内主要持仓 |
| ACC-03 | `acc03-fund-holding` | 基金持有详情 | 账户中某只基金的持有情况 |
| ACC-04 | `acc04-advisor-account` | 投顾账户详情 | 投顾账户整体、组合数量和账户收益 |
| ACC-05 | `acc05-advisor-combo` | 投顾组合详情 | 指定投顾组合的整体、收益和组合持仓 |
| ACC-06 | `acc06-advisor-rebalance` | 投顾调仓记录 | 指定投顾组合的调仓历史、内容和原因 |
| ACC-07 | `acc07-money-account` | 货币账户详情 | 货币基金账户、现金宝金额和收益 |
| ACC-08 | `acc08-money-holding` | 货币持有详情 | 从货币账户下钻到单只货币基金 |
| ACC-09 | `acc09-private-account` | 专户账户详情 | 专户账户或专户产品整体情况 |
| ACC-10 | `acc10-private-holding` | 专户持有详情 | 从专户账户下钻到单个专户产品 |

## 规则

1. 优先根据 `subQuery` 中明确的账户类型、产品层级和动作选择最具体的卡片。
2. 未指定账户类型，只问总资产、钱的构成或账户整体情况时输出 ACC-01。
3. 基金账户进入 ACC-02；明确问账户中某只基金的持有情况进入 ACC-03。
4. 投顾账户整体进入 ACC-04；指定投顾组合进入 ACC-05；询问组合调仓进入 ACC-06。
5. 货币基金账户或现金宝进入 ACC-07；单只货币基金下钻进入 ACC-08。
6. 专户账户整体进入 ACC-09；单个专户产品下钻进入 ACC-10。
7. 一个 `subQuery` 同时明确命中多个卡片时，按诉求先后输出对应卡片。
8. 无法确定具体账户类型时输出 ACC-01。
9. 所有卡片固定使用 `deferred`，不得生成具体资产、收益、份额或调仓记录。
10. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "account_overview"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您整理基金账户信息。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-02",
      "type": "acc02-fund-account",
      "title": "基金账户详情",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc02",
        "params": {
          "userId": "${userId}",
          "date": "latest"
        }
      }
    }
  ]
}
```
