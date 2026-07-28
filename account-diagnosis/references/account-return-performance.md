---
name: account-return-performance
description: "将 return_performance 账户意图映射为 ACC-13-A 账户收益总览、ACC-13-B 分年视角或 ACC-14 收益明细日历，并生成已确认资产中心接口的取数计划。"
---

# Account Return Performance

作为账户域 Phase C，只处理 `intent = "return_performance"` 的单条路由记录。根据用户关注的收益口径和时间范围选择收益卡片，不生成或猜测收益数据。

## 输入

```json
{
  "intent": "return_performance",
  "subQuery": "我今年收益怎么样",
  "entities": {}
}
```

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-13-A | `acc13a-return-overview` | 账户收益总览 | 赚了多少、收益怎么样、滚动区间或基准比较 |
| ACC-13-B | `acc13b-yearly-view` | 账户收益总览 · 分年视角 | 去年、历年或自然年度收益 |
| ACC-14 | `acc14-return-calendar` | 收益明细日历 | 每日、每月、每年收益及时间序列回顾 |

## 规则

1. 泛问收益、累计赚亏、收益率、滚动区间或基准比较时输出 ACC-13-A。
2. 明确询问去年、历年或自然年度收益时输出 ACC-13-B。
3. 询问每日、每月、每年明细或哪段时间赚亏时输出 ACC-14。
4. 同时询问总览和收益明细时，按诉求先后输出对应卡片。
5. 时间表达不明确时输出 ACC-13-A。
6. ACC-13-A 的简单总览使用 `/analyze/profit/sum`；滚动区间或基准比较使用 `/analyze/profit/yield`。
7. ACC-13-B 使用 `/analyze/profit/yield`；ACC-14 使用 `/analyze/profit/calendar`。
8. 所有卡片固定使用 `deferred`，不得生成具体收益、收益率或基准数据。
9. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "return_performance",
  "subQuery": "我去年收益怎么样",
  "cards": [
    {
      "cardId": "ACC-13-B",
      "dataMode": "deferred",
      "data": {
        "request": {
          "method": "GET",
          "path": "/v1/asset/agent/analyze/profit/yield",
          "params": {
            "custNo": "由可信系统注入",
            "accountName": "由可信系统注入",
            "dateType": "根据用户时间范围确定",
            "indexCodes": "根据用户明确要求确定"
          }
        }
      }
    }
  ]
}
```
