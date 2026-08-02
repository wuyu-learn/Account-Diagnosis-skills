# Account Card Routing

## 目录

- 职责
- 通用边界
- 单项选卡
- 卡片组合
- 参数边界

## 职责

作为“用户问题 → `cardPlans`”的唯一规则来源，同时维护单卡映射、复合问题组合、完整账户诊断默认组合和卡片业务参数。

账户 Planner 只输出：

```json
{
  "cardId": "ACC-13-A",
  "params": {}
}
```

不输出 `dataMode`、`data`、Section、标题或 narrative。代码负责生成固定卡片信封和业务 Section。

## 通用边界

- 先根据用户语义确定 simple/complex，再选择卡片；卡片数量和组合不能反向决定复杂度；
- 每个独立 `subQuery` 选择对象和层级最具体的卡片，再合并为一份 `cardPlans`；
- 同一个 cardId 只保留一次；
- 同一业务类型的多张卡片保持用户诉求顺序，跨类型顺序由代码确定；
- 账户诊断类 ACC-01～ACC-15 与自选基金类 ACC-18 不得混排；
- 不根据 MCP、接口记录或数据状态改变选卡；
- 卡片组合不等于 MCP 计划，不按卡片逐张调用 MCP；
- ACC-16、ACC-17 不存在，禁止生成。

## 单项选卡

### account_overview

| cardId | 用户诉求 | params |
| --- | --- | --- |
| ACC-01 | 未指定账户类型的总资产、钱的构成、账户整体概况 | `{}` |
| ACC-02 | 基金账户整体、收益或账户内产品 | `{}` |
| ACC-03 | 指定基金的持有详情 | 可选 `serialNo`、`uri` |
| ACC-19 | 指定产品份额明细 | 可选 `productId` |
| ACC-04 | 投顾账户整体、组合数量或账户收益 | `{}` |
| ACC-05 | 指定投顾组合整体、收益或持仓 | 可选 `serialNo`、`uri` |
| ACC-06 | 指定投顾组合调仓记录 | 可选 `serialNo`、`uri` |
| ACC-07 | 货币账户、货币基金账户或现金宝整体 | `{}` |
| ACC-08 | 指定货币基金持有详情 | 可选 `serialNo`、`uri` |
| ACC-09 | 专户账户整体 | `{}` |
| ACC-10 | 指定专户产品持有详情 | 可选 `serialNo`、`uri` |

优先选择最具体的账户和产品层级。无法确定账户类型时选择 ACC-01；未指定产品时不得选择单产品卡片。

### holding_structure

| cardId | 用户诉求 |
| --- | --- |
| ACC-11 | 买了哪些、持仓列表、单只持仓表现、产品集中情况 |
| ACC-12 | 资产分布、配置结构、地区/行业暴露、集中度 |

同时询问持仓明细和资产结构时选择 ACC-11、ACC-12；无法进一步区分“持仓结构”指产品还是资产结构时也选择两张。

### return_performance

| cardId | 用户诉求 |
| --- | --- |
| ACC-13-A | 泛问收益、今年以来、滚动区间、收益率或基准比较 |
| ACC-13-B | 去年、历年或多个已完成自然年度 |
| ACC-14 | 按日/月/年展开明细、收益日历、最好或最差时段 |

“今年收益怎么样”选择 ACC-13-A；只有分年或历史自然年度视角才选择 ACC-13-B。

### return_attribution

所有产品、类型或行业维度的贡献、拖累和赚亏原因都选择 ACC-15。

### watchlist_valuation

询问自选或关注基金的当日估值、净值更新和涨跌时选择 ACC-18，`params` 为 `{}`。自选基金始终独立回答且固定为 simple。

## 卡片组合

### 组合流程

```text
拆分独立账户问题
→ 为每个问题选择精确卡片
→ 合并 cardPlans
→ 去重相同 cardId
→ 只保留 primaryAccountIntent 所属回答大类
→ 由代码按固定业务顺序生成 Section
```

不得因为 `taskComplexity = complex` 自动补齐所有诊断卡片。只有用户要求完整账户诊断、账户体检或整体分析时，才使用完整诊断默认组合。

### 典型问题

下表使用 cardId 简写组合；Planner 实际仍按 `{ "cardId": "...", "params": {} }` 输出每一项。

| 用户问题 | 复杂度 | cardPlans |
| --- | --- | --- |
| 我的账户有多少钱 | simple | ACC-01 |
| 我的基金账户怎么样 | simple | ACC-02 |
| 我持有这只产品多少份 | simple | ACC-19 |
| 我都买了什么 | simple | ACC-11 |
| 我的资产、地区和行业怎么分布 | simple | ACC-12 |
| 持仓明细和资产结构都看一下 | simple | ACC-11 + ACC-12 |
| 我今年收益怎么样 | simple | ACC-13-A |
| 看一下历年收益 | simple | ACC-13-B |
| 哪个月亏得最多 | simple | ACC-14 |
| 今年哪些产品在拖累 | simple | ACC-15，`dateType = Y0` |
| 我买了什么，今年赚了多少 | simple | ACC-11 + ACC-13-A |
| 今年收益多少，哪些产品在拖累 | simple | ACC-13-A + ACC-15，`dateType = Y0` |
| 哪些重仓产品是主要拖累 | complex | ACC-11 + ACC-15 |
| 持仓结构为什么导致收益不好 | complex | ACC-11 + ACC-12 + ACC-13-A + ACC-15 |
| 资产和行业配置为什么拖累收益 | complex | ACC-12 + ACC-13-A + ACC-15 |
| 我的账户怎么样 | complex | ACC-01 + ACC-11 + ACC-12 + ACC-13-A + ACC-15 |
| 我的自选基金今天怎么样 | simple | ACC-18，独立回答 |

### 相同组合、不同复杂度

```text
“我买了什么，哪些产品在拖累”
→ 两个结果可以独立回答
→ simple
→ ACC-11 + ACC-15

“我的重仓产品是不是主要拖累”
→ 必须关联持仓权重和同周期归因
→ complex
→ ACC-11 + ACC-15
```

Planner 先判断用户是否要求关系或账户级结论，再按本文件选择卡片。

### 完整账户诊断

“我的账户怎么样”“给账户做一次体检”等完整诊断默认生成：

```text
accountScenes
→ account_overview
→ holding_structure
→ return_performance
→ return_attribution

cardPlans
→ ACC-01
→ ACC-11
→ ACC-12
→ ACC-13-A
→ ACC-15
```

`primaryAccountIntent` 使用 `account_overview`。ACC-15 仍按本文件的 `dateType` 规则填写参数；完整诊断卡片组合不替代 complex 任务独立规划 MCP 证据。

### 跨回答大类

一次账户结果只处理 `primaryAccountIntent` 所属回答大类：

- primary 属于账户诊断类时，丢弃 ACC-18；
- primary 为 `watchlist_valuation` 时，只保留 ACC-18；
- 不为被丢弃的大类生成 cardPlan、Section 或文字结论。

## 参数边界

ACC-15 必须输出 `params.dateType`：

| 用户时间表达 | dateType |
| --- | --- |
| 今日、今天 | `N` |
| 昨日、昨天 | `L` |
| 本月 | `M0` |
| 近一月、近三月、近六月 | `M1`、`M3`、`M6` |
| 今年、本年、今年以来 | `Y0` |
| 近一年、近三年、近五年 | `Y1`、`Y3`、`Y5` |
| 指定自然年 | `Y20XX`，例如 `Y2025` |
| 成立以来、全部、至今 | `T` |

用户未明确时间时使用 `N`。参数由 Planner 识别，代码只校验，不重新解释时间语义。

- `params` 只能包含当前 cardId 允许的业务参数；
- 所有参数值必须是非空字符串；
- 禁止 `custNo`、`accountName` 或其他身份、会话和鉴权字段；
- 用户没有明确提供可选参数时保持空对象，不得猜测；
- ACC-19 可选 `productId`；ACC-03/05/06/08/10 可选 `serialNo`、`uri`；其余未列出的卡片参数必须为空。
