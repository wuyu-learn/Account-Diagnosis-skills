---
name: account-asset-overview
description: "将 account_overview 账户意图精确映射为账户总资产、账户详情、持有详情、组合调仓或产品份额卡片。Account Intent Router 输出资产总览诉求，需要生成 deferred 账户卡片计划时使用。"
---

# Account Asset Overview

作为账户域 Account Step 2（卡片选择与计划归一化），只处理 `intent = "account_overview"` 的单条路由记录。按本文件规则选择卡片，不获取、生成或猜测账户数据。

## 输入

```json
{
  "intent": "account_overview",
  "subQuery": "我的基金账户怎么样",
  "entities": {}
}
```

`intent` 和 `subQuery` 对应 Account Intent Router 的一条 `accountScenes` 记录；`entities` 由编排层从 Global Phase A 原样传入。

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
9. 所有卡片固定输出 `dataMode: "deferred"` 且 `data` 为空对象；取数写在前端组件里，本模块不生成 `data.request`。
10. `subQuery` 未指定具体产品时不得输出 ACC-19；诉求实为账户整体情况时改输出对应账户详情卡。
11. 不检查卡片是否已有接口记录或数据，不得因数据能力改变目标卡片。
12. 不得生成具体资产、收益、份额或调仓记录。
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
      "data": {}
    }
  ]
}
```

ACC-19 输出：

```json
{
  "intent": "account_overview",
  "subQuery": "我这只产品有多少份额",
  "cards": [
    {
      "cardId": "ACC-19",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```

ACC-03 输出：

```json
{
  "intent": "account_overview",
  "subQuery": "我持有的这只基金怎么样",
  "cards": [
    {
      "cardId": "ACC-03",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```
