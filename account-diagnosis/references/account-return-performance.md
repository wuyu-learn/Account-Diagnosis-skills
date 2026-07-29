---
name: account-return-performance
description: "将 return_performance 账户意图精确映射为 ACC-13-A 账户收益总览、ACC-13-B 分年视角或 ACC-14 收益明细日历，并生成 deferred 卡片计划。"
---

# Account Return Performance

作为账户域 Account Step 2（卡片选择与计划归一化），只处理 `intent = "return_performance"` 的单条路由记录。根据用户关注的收益口径和时间范围选择收益卡片，不获取、生成或猜测收益数据。

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
| ACC-13-A | `acc13a-return-overview` | 账户收益总览 | 赚了多少、收益怎么样、今年以来、滚动区间或基准比较 |
| ACC-13-B | `acc13b-yearly-view` | 账户收益总览 · 分年视角 | 已完成年度、历年或多个自然年度的收益视角 |
| ACC-14 | `acc14-return-calendar` | 收益明细日历 | 按日、按月、按年展开的收益明细及时间序列回顾 |

## 规则

1. 泛问收益、累计赚亏、收益率、今年或今年以来、滚动区间或基准比较时输出 ACC-13-A。
2. 明确询问去年等已完成年度、历年表现或多个自然年度对比时输出 ACC-13-B。
3. 询问按日、按月、按年展开的明细、收益日历或哪段时间赚亏时输出 ACC-14。
4. 同时询问总览和收益明细时，按诉求先后输出对应卡片。
5. 单问“今年收益怎么样”是当前收益总览，输出 ACC-13-A；只有要求年度分拆、历史年度或跨年度视角时才输出 ACC-13-B。
6. 时间表达不明确时输出 ACC-13-A。
7. 卡片固定输出 `dataMode: "deferred"` 且 `data` 为空对象；取数写在前端组件里，本模块不生成 `data.request`。
8. 不得生成具体收益、收益率或基准数据。
9. 不检查卡片接口或数据状态。
10. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "return_performance",
  "subQuery": "我今年收益怎么样",
  "cards": [
    {
      "cardId": "ACC-13-A",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```
