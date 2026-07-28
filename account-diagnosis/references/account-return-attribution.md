---
name: account-return-attribution
description: "将 return_attribution 账户意图映射为卡片清单中的 ACC-15 收益归因，并生成当前仅支持按产品归因的资产中心接口取数计划。"
---

# Account Return Attribution

作为账户域 Phase C，只处理 `intent = "return_attribution"` 的单条路由记录。卡片清单当前只允许 ACC-15，不生成 ACC-16 或 ACC-17。

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
| ACC-15 | `acc15-return-attribution` | 收益归因 | 按产品查看收益贡献与拖累 |

## 规则

1. 询问账户为什么赚亏、主要贡献或拖累时输出 ACC-15。
2. ACC-15 固定使用 `GET /v1/asset/agent/analyze/attribution`，当前仅允许 `type = "1"` 按产品归因。
3. 资产类别归因、买入位置等现有接口不支持的诉求，输出 `unsupported_query`，不得虚构 ACC-16、ACC-17 或改用其他接口。
4. 所有可取数结果固定使用 `deferred`，不得生成具体贡献或拖累数据。
5. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "return_attribution",
  "subQuery": "哪些产品拖累了收益",
  "cards": [
    {
      "cardId": "ACC-15",
      "dataMode": "deferred",
      "data": {
        "request": {
          "method": "GET",
          "path": "/v1/asset/agent/analyze/attribution",
          "params": {
            "custNo": "由可信系统注入",
            "accountName": "由可信系统注入",
            "dateType": "根据用户时间范围确定",
            "type": "1"
          }
        }
      }
    }
  ]
}
```
