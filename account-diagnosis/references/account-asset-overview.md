---
name: account-asset-overview
description: "将 account_overview 账户意图映射为账户总资产、账户详情和产品份额明细卡片，并阻止无接口的持有详情或调仓卡片生成取数请求。Account Intent Router 输出资产总览诉求，需要生成账户卡片取数计划时使用。"
---

# Account Asset Overview

作为账户域 Phase C，只处理 `intent = "account_overview"` 的单条路由记录。以 `documentation/卡片组件.md` 和 `documentation/AI顾问数据与取数协议.md` 为准选择卡片及真实接口，不生成或猜测账户数据。

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
| ACC-19 | `acc19-fund-holding-summary` | 产品份额明细 | 指定产品的份额明细 |
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
3. 基金账户进入 ACC-02；明确询问产品份额明细时输出 ACC-19。
4. 投顾账户整体进入 ACC-04；指定投顾组合进入 ACC-05；询问组合调仓进入 ACC-06。
5. 货币基金账户或现金宝进入 ACC-07；单只货币基金下钻进入 ACC-08。
6. 专户账户整体进入 ACC-09；单个专户产品下钻进入 ACC-10。
7. 一个 `subQuery` 同时明确命中多个卡片时，按诉求先后输出对应卡片。
8. 无法确定具体账户类型时输出 ACC-01。
9. ACC-01、ACC-02、ACC-04、ACC-07、ACC-09 使用 `GET /v1/asset/agent/total`；根据账户类型由可信系统补齐 `assetType` 和 `accountName`。
10. ACC-19 使用 `GET /v1/asset/agent/share-detail`，由可信系统补齐 `productId`。
11. ACC-03、ACC-05、ACC-06、ACC-08、ACC-10 当前没有可用接口。命中时输出结构化 `unsupported_card` 错误并停止，不得生成空 `data.request`，不得用 `/holding-detail` 或 `/share-detail` 替代。
12. 所有可取数卡片固定使用 `deferred`，不得生成具体资产、收益、份额或调仓记录。
13. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "account_overview",
  "subQuery": "我的基金账户怎么样",
  "cards": [
    {
      "cardId": "ACC-02",
      "dataMode": "deferred",
      "data": {
        "request": {
          "method": "GET",
          "path": "/v1/asset/agent/total",
          "params": {
            "custNo": "由可信系统注入",
            "accountName": "由可信系统注入",
            "assetType": "由可信系统按账户类型注入"
          }
        }
      }
    }
  ]
}
```

无接口卡片输出：

```json
{
  "error": {
    "code": "unsupported_card",
    "cardId": "ACC-03",
    "message": "当前没有可用于基金持有详情的已确认接口"
  }
}
```
