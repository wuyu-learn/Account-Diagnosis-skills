---
name: account-holding-structure
description: "账户持仓结构分析：基于卡片组件.md，将持仓结构类 subQuery 映射为 ACC-11 持仓明细或 ACC-12 资产结构卡片，输出 sections + cards。"
---

# Account Holding Structure（账户持仓结构分析）

账户域持仓结构分析 Skill（三段式流水线 Phase C）。接收上游 **Account Intent Router** 输出的 `accountIntent = "holding_structure"`，根据 `subQuery` 召回对应卡片并输出统一 AI Response 协议 JSON。

卡片定义以 `skills/documentation/卡片组件.md` 为准：

| 卡片字段 | 编号 | 卡片名称 | 触发场景 |
| --- | --- | --- | --- |
| `acc11-position-detail` | ACC-11 | 持仓明细 | 我都买了哪些 / 每只怎么样 / 看持仓 |
| `acc12-asset-structure` | ACC-12 | 资产结构 | 我的钱怎么分布 / 在各维度怎么分 / 是否集中 |

## 输入

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "用户原始持仓问题",
  "entities": {}
}
```

## 输出协议

只输出合法 JSON，不要 markdown 代码块，不要任何解释性文字：

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "holding_structure"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您整理当前持仓明细。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-11",
      "type": "acc11-position-detail",
      "title": "持仓明细",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc11",
        "params": { "userId": "${userId}", "date": "latest" }
      }
    }
  ]
}
```

## 卡片映射

### ACC-11 持仓明细

- **type**: `acc11-position-detail`
- **title**: `持仓明细`
- **触发场景**：
  - 我都买了哪些
  - 我的持仓有哪些
  - 查看我的持仓 / 看持仓
  - 我的投资组合包含什么
  - 每只怎么样
  - 我的基金表现如何
  - 哪只持仓表现最好

### ACC-12 资产结构

- **type**: `acc12-asset-structure`
- **title**: `资产结构`
- **触发场景**：
  - 我的钱怎么分布
  - 在各维度怎么分
  - 我的资产配置情况
  - 我的持仓是否集中
  - 有没有重仓风险
  - 风险是否过于集中

## 判断规则

1. 根据 `subQuery` 匹配触发场景，输出对应卡片。
2. 同时命中 ACC-11 和 ACC-12 场景时，两张卡片都输出。
3. 默认所有卡片使用 `deferred` 数据模式。
4. `sections` 中只放高度概括的摘要文本，不展开具体数值。
5. 无法判断具体场景但属于持仓结构时，同时输出 ACC-11 和 ACC-12。
6. 输出必须是合法 JSON，不添加解释性文字。

## 示例

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "我的持仓有哪些，哪只表现最好",
  "entities": {}
}
```

输出：

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "holding_structure"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您整理持仓明细。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-11",
      "type": "acc11-position-detail",
      "title": "持仓明细",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc11",
        "params": { "userId": "${userId}", "date": "latest" }
      }
    }
  ]
}
```

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "我的钱怎么分布，持仓是否集中",
  "entities": {}
}
```

输出：

```json
{
  "meta": {
    "scene": "问账户",
    "intent": "holding_structure"
  },
  "sections": [
    {
      "type": "summary",
      "content": "已为您分析资产结构与持仓集中度。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-12",
      "type": "acc12-asset-structure",
      "title": "资产结构",
      "dataMode": "deferred",
      "dataQuery": {
        "api": "/api/account/card/acc12",
        "params": { "userId": "${userId}", "date": "latest" }
      }
    }
  ]
}
```
