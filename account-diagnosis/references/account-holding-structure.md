---
name: account-holding-structure
description: "将 holding_structure 账户意图映射为 ACC-11 持仓明细或 ACC-12 资产结构卡片。Account Intent Router 输出持仓结构诉求，需要生成账户卡片响应 JSON 时使用。"
---

# Account Holding Structure

作为账户域 Account Step 2（卡片选择与取数计划），只处理 `intent = "holding_structure"` 的单条路由记录。根据 `subQuery` 选择持仓结构卡片，不生成或猜测账户数据。

## 输入

```json
{
  "intent": "holding_structure",
  "subQuery": "我的持仓有哪些",
  "entities": {}
}
```

`intent` 和 `subQuery` 直接对应 Account Intent Router 的一条 `accountScenes` 记录；`entities` 由编排层从 Global Phase A 原样传入。

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-11 | `acc11-position-detail` | 持仓明细 | 买了哪些、每只怎么样、查看持仓 |
| ACC-12 | `acc12-asset-structure` | 资产结构 | 资产分布、维度构成、集中度 |

## 规则

1. 查询持仓列表、单只持仓表现或持仓好差时输出 ACC-11。
2. 查询资产分布、配置结构、穿透维度或集中度时输出 ACC-12。
3. 同时命中两个范围时按诉求先后输出两张卡片。
4. 无法进一步判断但确定为 `holding_structure` 时，同时输出 ACC-11 和 ACC-12。
5. 可取数卡片固定输出 `dataMode: "deferred"` 且 `data` 为空对象；取数写在前端组件里，本模块不生成 `data.request`。
6. 不得生成具体金额、比例或持仓。
7. `sections` 只写概括性说明，不写未经查询的数据。
8. 只输出合法 JSON，不添加解释文字。

## 输出

```json
{
  "intent": "holding_structure",
  "subQuery": "我的持仓有哪些",
  "cards": [
    {
      "cardId": "ACC-11",
      "dataMode": "deferred",
      "data": {}
    }
  ]
}
```
