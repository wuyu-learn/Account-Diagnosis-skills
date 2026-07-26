---
name: account-return-performance
description: "将 return_performance 账户意图映射为 ACC-13 账户收益总览、ACC-13-A/ACC-13-B 区间视图或 ACC-14 收益明细日历。Account Intent Router 输出收益表现诉求，需要生成账户卡片响应 JSON 时使用。"
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
| ACC-13 | `acc13-return-overview` | 账户收益总览 | 赚了多少、收益怎么样、是否跑赢基准 |
| ACC-13-A | `acc13-return-overview` | 滚动区间 | 近一周、近一月、近三月、近一年等滚动区间 |
| ACC-13-B | `acc13-return-overview` | 固定区间 | 今年、去年、某年或明确起止日期 |
| ACC-14 | `acc14-return-calendar` | 收益明细日历 | 每日、每月、每年收益及时间序列回顾 |

## 规则

1. 泛问收益、累计赚亏、收益率或基准比较时输出 ACC-13。
2. 明确询问“近 N 天/月/年”等滚动窗口时输出 ACC-13-A。
3. 明确询问自然年度或起止日期等固定区间时输出 ACC-13-B。
4. 询问每日、每月、每年明细或哪段时间赚亏时输出 ACC-14。
5. ACC-13-A 和 ACC-13-B 是 ACC-13 的区间视图；选择区间子卡时不重复输出 ACC-13。
6. 同时询问总览和收益明细时，按诉求先后输出对应卡片。
7. 时间表达不明确时输出 ACC-13。
8. 所有卡片固定使用 `deferred`，不得生成具体收益、收益率或基准数据。
9. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "return_performance"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您整理账户收益表现。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-13-B",
      "type": "acc13-return-overview",
      "title": "固定区间",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc13",
        "params": {
          "userId": "${userId}",
          "rangeType": "fixed",
          "date": "latest"
        }
      }
    }
  ]
}
```
