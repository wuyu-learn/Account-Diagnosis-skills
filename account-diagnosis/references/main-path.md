# Main Path Contract

本文件是常规问账户路径的唯一运行规则。先完成 `main_pipeline.py prepare`；若
`testMode=true`，立即转回 `card-test-mode.md` 的既有测试链路，不继续本文件。

## 1. 回答模式

`responseMode` 只由代码生成，OpenClaw 不得覆盖：

```text
明确要求诊断、解释原因或分析关系 -> diagnostic
其他所有问题                    -> summary_only
```

诊断触发仅包括：

- 诊断：账户诊断、账户体检、全面分析、找主要问题；
- 原因：为什么、为何、什么原因、导致；
- 关系：A 是否影响 B、结构与收益的关系、重仓是否为主要拖累。

`我的账户怎么样`、`我的基金账户怎么样`、`哪些产品拖累了收益`、多个独立事实
并列查询均为 `summary_only`。卡片数量和 MCP 数量不改变模式。

代码固定映射：`summary_only -> simple`，`diagnostic -> complex`。

## 2. 账户计划

OpenClaw 只输出以下三个字段：

```json
{
  "primaryAccountIntent": "return_performance",
  "accountScenes": [
    {"intent": "return_performance", "weight": 0.95, "subQuery": "我今年收益怎么样"}
  ],
  "cardPlans": [{"cardId": "ACC-13-A", "params": {}}]
}
```

意图只允许 `account_overview`、`holding_structure`、`return_performance`、
`return_attribution`、`watchlist_valuation`。第一条 scene 必须等于 primary；scene 按
weight 降序。不要输出复杂度、responseMode、Section、MCP 计划或身份字段。

### 卡片映射

| 卡片 | 用户诉求 |
| --- | --- |
| ACC-01 | 未限定账户类型的总资产、账户概况；“我的账户怎么样” |
| ACC-02 | 基金账户整体 |
| ACC-03 | 指定基金的某个具体份额 |
| ACC-04 | 投顾账户整体 |
| ACC-05 | 指定投顾组合的某个具体份额 |
| ACC-06 | 指定投顾组合某份额的调仓记录 |
| ACC-07 | 货币账户整体 |
| ACC-08 | 指定货币基金的某个具体份额 |
| ACC-09 | 专户账户整体 |
| ACC-10 | 指定专户产品的某个具体份额 |
| ACC-11 | 持仓列表、买了哪些、产品集中情况 |
| ACC-12 | 资产、地区、行业分布与集中度 |
| ACC-13-A | 泛问收益、今年以来、滚动区间、基准比较 |
| ACC-13-B | 去年、历年或多个已完成自然年度 |
| ACC-14 | 日/月/年收益明细、收益日历、最好或最差时段 |
| ACC-15 | 产品、类型或行业贡献、拖累与原因 |
| ACC-18 | 自选基金当日估值、涨跌和净值更新 |
| ACC-19 | 某个产品的多笔份额明细 |

规则：

- 多个独立问题分别选卡后合并去重；卡片数量不决定 responseMode；
- 诊断类 ACC-01～15 与自选 ACC-18 不得混排；自选固定 summary_only；
- ACC-16、ACC-17 不存在；
- 完整诊断/体检固定使用 ACC-01、ACC-11、ACC-12、ACC-13-A、ACC-15，primary 为
  `account_overview`，accountScenes 依次声明 `account_overview`、
  `holding_structure`、`return_performance`、`return_attribution`；关系诊断只选择并
  声明建立目标关系所需的意图和卡片；
- “我买了什么，今年赚多少”使用 ACC-11 + ACC-13-A；
- “今年收益多少，哪些产品拖累”使用 ACC-13-A + ACC-15；
- “重仓产品是否为主要拖累”使用 ACC-11 + ACC-15。

### 参数

ACC-15 必须带 `dateType`：今日 N、昨日 L、本月 M0、近一/三/六月 M1/M3/M6、
今年 Y0、近一/三/五年 Y1/Y3/Y5、指定自然年 Y20XX、成立以来 T；未说明时间用 N。

ACC-19 可带用户明确提供的产品代码 `productId`。ACC-03/05/06/08/10 在计划阶段
保持空参数，MCP 后只把唯一匹配候选的 `productId`、`balanceSerialNo`、`uri`
交给主路径 finalize；多个候选或字段不全时不回填。不得猜测身份或标识。

## 3. MCP 与文字

卡片决定展示，MCP 只支持文字回答；不要逐卡调用。独立 MCP 尽量同批调用。

| 回答需要 | 最少候选 MCP |
| --- | --- |
| 总资产和账户构成 | queryAssetsTotal |
| 今日账户表现 | queryAssetIndex |
| 资产、地区、行业结构 | queryAssetClassify |
| 持仓与基金穿透 | queryHoldingDetail |
| 指定产品份额 | queryShareDetail |
| 区间收益、基准和回撤 | queryProfitAnalyze / queryProfitAnalyzeSum |
| 收益日历 | queryProfitCalendar |
| 收益贡献和拖累 | queryProfitAttribution |
| 今日持仓提醒 | queryHoldingSignal |

每个结果区分可用、部分可用和不可用；校验账户范围、周期、产品标识、零值、估算值
和正负号。范围、周期或对象不一致时不能建立关系。MCP 失败不删除 deferred 卡片。
除份额定位标识外，MCP 数据不得写入卡片 data。

OpenClaw 一次生成最小文字载荷：

```json
{
  "summaryNarrative": "基于本次已校验 MCP 的直接回答。",
  "followUp": []
}
```

diagnostic 时在同一载荷增加 `conclusionNarrative`，并先完整读取
`complex-diagnosis.md`。summary_only 禁止该字段。Summary 只写查询范围、1～3 个
关键事实和直接答案；没有数据时明确不可用，不补造结论。followUp 默认空数组。

## 4. 最终输出

把 `routeExtract`、三字段 plan、text 和可选 `shareBindings` 一次交给：

```bash
python3 scripts/main_pipeline.py finalize --input finalize.json --output result.json
```

脚本负责复杂度、固定标题、业务 Section、卡片、份额回填、风险提示和 v2.2 校验。
只回传 `result.json` 的 JSON 本体，不输出计划、MCP 原文、身份信息、路径或解释文字。
