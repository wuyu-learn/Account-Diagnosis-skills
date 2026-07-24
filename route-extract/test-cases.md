# Route & Extract 测试用例

每个用例包含输入与期望输出。期望输出已按 SKILL.md 的规则人工校验：
`scenes` 按 weight 降序、`primaryScene` = 最高 weight 场景、`isMultiScene` ⇔ scenes ≥ 2、
entities 六键齐全、无编造实体。

下游 Skill 或自动化测试可用本文件做回归：将输入喂给路由模型，比对场景集合与实体集合
（weight 允许 ±0.15 浮动）。

---

## 1. 单场景 · 问账户

输入：`我今年收益率多少？`

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.95, "subQuery": "我今年收益率多少" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": false
}
```

## 2. 单场景 · 问市场

输入：`最近新能源板块为什么这么火？`

```json
{
  "scenes": [
    { "scene": "问市场", "weight": 0.93, "subQuery": "最近新能源板块为什么这么火" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": ["新能源"],
    "strategy_names": []
  },
  "primaryScene": "问市场",
  "isMultiScene": false
}
```

## 3. 单场景 · 问基金（含代码 + 经理实体）

输入：`018124 这只基金怎么样，基金经理张坤水平如何？`

```json
{
  "scenes": [
    { "scene": "问基金", "weight": 0.94, "subQuery": "018124 这只基金怎么样，基金经理张坤水平如何" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": ["018124"],
    "manager_names": ["张坤"],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": false
}
```

## 4. 单场景 · 问投教

输入：`夏普比率是什么意思？`

```json
{
  "scenes": [
    { "scene": "问投教", "weight": 0.96, "subQuery": "夏普比率是什么意思" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问投教",
  "isMultiScene": false
}
```

## 5. 单场景 · 问策略

输入：`我有 10 万闲钱，应该怎么配置？`

```json
{
  "scenes": [
    { "scene": "问策略", "weight": 0.9, "subQuery": "我有 10 万闲钱，应该怎么配置" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问策略",
  "isMultiScene": false
}
```

## 6. 多场景 · 问基金 + 问市场

输入：`帮我看看永赢先进制造怎么样，另外半导体现在行情如何？`

```json
{
  "scenes": [
    { "scene": "问基金", "weight": 0.92, "subQuery": "永赢先进制造怎么样" },
    { "scene": "问市场", "weight": 0.74, "subQuery": "半导体现在行情如何" }
  ],
  "entities": {
    "fund_names": ["永赢先进制造"],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": ["半导体"],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": true
}
```

## 7. 多场景 · 问账户 + 问策略

输入：`我持仓里的易方达蓝筹亏了不少，要不要调仓？`

```json
{
  "scenes": [
    { "scene": "问账户", "weight": 0.85, "subQuery": "我持仓里的易方达蓝筹亏了多少" },
    { "scene": "问策略", "weight": 0.8, "subQuery": "持仓亏损要不要调仓" }
  ],
  "entities": {
    "fund_names": ["易方达蓝筹"],
    "fund_codes": [],
    "manager_names": [],
    "company_names": ["易方达"],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问账户",
  "isMultiScene": true
}
```

## 8. 多场景 · 问投教 + 问策略（策略名实体）

输入：`什么是杠铃策略？适合我现在用吗？`

```json
{
  "scenes": [
    { "scene": "问策略", "weight": 0.88, "subQuery": "杠铃策略适合我现在用吗" },
    { "scene": "问投教", "weight": 0.72, "subQuery": "什么是杠铃策略" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": [],
    "market_subjects": [],
    "strategy_names": ["杠铃策略"]
  },
  "primaryScene": "问策略",
  "isMultiScene": true
}
```

## 9. 表达不完整 · 降权处理

输入：`那个……华夏的呢？`

（无上下文时无法确定"华夏的"指基金、公司还是主题，选最接近的 `问基金` 并降权；"华夏"按公司名抽取。）

```json
{
  "scenes": [
    { "scene": "问基金", "weight": 0.5, "subQuery": "华夏的基金怎么样" }
  ],
  "entities": {
    "fund_names": [],
    "fund_codes": [],
    "manager_names": [],
    "company_names": ["华夏"],
    "market_subjects": [],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": false
}
```

## 10. 三场景 · 问基金 + 问市场 + 问策略

输入：`中欧医疗健康还能拿吗？医药板块后面怎么看，我要不要减仓？`

```json
{
  "scenes": [
    { "scene": "问基金", "weight": 0.9, "subQuery": "中欧医疗健康还能拿吗" },
    { "scene": "问策略", "weight": 0.82, "subQuery": "我要不要减仓" },
    { "scene": "问市场", "weight": 0.78, "subQuery": "医药板块后面怎么看" }
  ],
  "entities": {
    "fund_names": ["中欧医疗健康"],
    "fund_codes": [],
    "manager_names": [],
    "company_names": ["中欧"],
    "market_subjects": ["医药"],
    "strategy_names": []
  },
  "primaryScene": "问基金",
  "isMultiScene": true
}
```
