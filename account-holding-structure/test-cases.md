# Account Holding Structure 测试用例

每个用例包含上游 Account Intent Router 的输出（输入）与期望的持仓结构 Skill 输出。卡片字段、编号、名称以 `skills/documentation/卡片组件.md` 为准。

---

## 1. 持仓查询

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "我的持仓有哪些",
  "entities": {}
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您整理当前持仓明细。" }
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

---

## 2. 单产品表现

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "哪只持仓表现最好",
  "entities": {}
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您整理持仓明细。" }
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

---

## 3. 持仓分布

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "我的钱怎么分布",
  "entities": {}
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您分析资产结构。" }
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

---

## 4. 集中度分析

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "有没有重仓风险",
  "entities": {}
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您分析持仓集中度。" }
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

---

## 5. 分布 + 集中度

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
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您分析资产结构与持仓集中度。" }
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

---

## 6. 默认兜底

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "那个持仓",
  "entities": {}
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "已为您整理持仓明细与资产结构。" }
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
    },
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

---

## 7. Inline 模式

输入：

```json
{
  "accountIntent": "holding_structure",
  "subQuery": "查看我的持仓",
  "entities": {},
  "dataMode": "inline"
}
```

输出：

```json
{
  "meta": { "scene": "问账户", "intent": "holding_structure" },
  "sections": [
    { "type": "summary", "content": "您目前持有 3 只产品，总市值约 100,000.00 元。" }
  ],
  "cards": [
    {
      "cardId": "ACC-11",
      "type": "acc11-position-detail",
      "title": "持仓明细",
      "dataMode": "inline",
      "data": {
        "totalMarketValue": 100000.00,
        "holdings": [
          { "name": "易方达蓝筹精选", "type": "混合型", "amount": 50000.00, "ratio": 0.50 },
          { "name": "华夏上证50ETF联接", "type": "指数型", "amount": 30000.00, "ratio": 0.30 },
          { "name": "中欧医疗健康", "type": "股票型", "amount": 20000.00, "ratio": 0.20 }
        ]
      }
    }
  ]
}
```
