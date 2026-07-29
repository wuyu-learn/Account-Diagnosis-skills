---
name: account-return-attribution
description: "将 return_attribution 账户意图映射为 ACC-15 收益归因 deferred 卡片，覆盖产品、类型和行业维度的收益贡献与拖累诉求。"
---

# Account Return Attribution

作为账户域 Account Step 2（卡片选择与计划归一化），只处理 `intent = "return_attribution"` 的单条路由记录。卡片清单只允许 ACC-15，不生成 ACC-16 或 ACC-17。

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
| ACC-15 | `acc15-return-attribution` | 收益归因 | 查看产品、类型或行业维度的收益贡献与拖累 |

## 规则

1. 询问账户为什么赚亏、主要贡献或拖累时输出 ACC-15。
2. 产品、类型或行业维度的收益归因都输出 ACC-15。
3. 其他收益归因诉求仍输出 ACC-15，不因 MCP 或接口能力改变卡片；Summary 和 Conclusion 能否形成具体判断由 MCP 结果决定。
4. 卡片固定输出 `dataMode: "deferred"` 且 `data` 为空对象；不得生成具体贡献或拖累数据。
5. 不得虚构 ACC-16 或 ACC-17。
6. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "return_attribution",
  "subQuery": "哪些产品拖累了收益",
  "cards": [
    {
      "cardId": "ACC-15",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```
