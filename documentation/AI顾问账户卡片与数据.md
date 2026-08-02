# AI 顾问账户卡片与数据

## 文档定位

本文档是账户卡片组件、数据模式、接口映射、接口字段、数据状态和失败降级的统一归档入口，不定义完整响应骨架、内容顺序或页面编排。整体处理链路见 `documentation/AI顾问整体架构.md`，回复结构和卡片编排见 `documentation/AI顾问结果输出与组件编排.md`。

当前账户域接口依据：

- 《投顾小程序AI顾问-34113-AI顾问-设计文档》
- 版本：V1.0
- 修订日期：2026-07-23
- 接口归属：资产中心

原始设计文档声明本次接口均为新接口。本文档保留原接口字段的 `camelCase` 命名，不擅自改名。

## 通用卡片结构

卡片只声明组件身份、数据提供方式和组件数据，不负责标题、解释文字或页面展示顺序。

```json
{
  "cardId": "CARD-ID",
  "dataMode": "deferred",
  "data": {}
}
```

| 字段 | 作用 |
| --- | --- |
| `cardId` | 卡片组件及其数据协议的唯一标识，并用于与 `section.cardId` 关联 |
| `dataMode` | 数据提供方式；当前账户卡片固定为 `deferred` |
| `data` | 传给卡片组件的数据载荷；默认为空对象，需要 per-request 业务入参的卡片直接在其中放入业务参数（如 `dateType`，见「Deferred 数据模式」） |

结构约束：

- 卡片根级只保留 `cardId`、`dataMode` 和 `data`。
- `type`、`chartType`、`title` 和 `dataQuery` 不属于当前卡片结构。
- 标题、分析文字和展示顺序由 `sections[]` 管理。
- 当前卡片信封中的 `data` 默认为空对象；仅需要 per-request 业务入参的卡片直接在 `data` 中平铺业务参数（如 `dateType`，见「Deferred 数据模式」）。组件加载、空数据和失败状态由前端组件内部处理，不作为编排条件。

## Deferred 数据模式

当前账户卡片统一由前端组件负责取数，所有卡片固定使用 `deferred`。`data` 默认为空对象；只有需要 per-request 业务入参的卡片，才**直接在 `data` 中平铺业务参数**（不套 `requests`/`params` 外层）。

默认卡片（参数固定或由前端组件内置）：

```json
{
  "cardId": "ACC-01",
  "dataMode": "deferred",
  "data": {}
}
```

需要 per-request 入参的卡片（以 ACC-15 收益归因为例，按用户意图解析 `dateType`）：

```json
{
  "cardId": "ACC-15",
  "dataMode": "deferred",
  "data": {
    "dateType": "Y1"
  }
}
```

`data` 入参规则：

- 业务参数**直接作为 `data` 的键平铺**（如 `data.dateType`、`data.productId`、`data.fundId`、`data.comboId`），不使用 `requests` 数组或 `params`、`method`、`path` 外层。
- **接口路径隐含自 `cardId`**：前端按「账户卡片清单」的 cardId→接口映射解析 endpoint；请求方式目前固定为 `GET`，均不在 `data` 中出现。
- `data` 只允许业务参数，**不得携带 `custNo`、`accountName` 等身份参数**（身份由可信运行时注入）。
- 需要在 `data` 中携带业务参数的卡片：ACC-15（`dateType`）、ACC-19（`productId`）、ACC-03 / ACC-05 / ACC-06 / ACC-08 / ACC-10（`serialNo`、`uri`）；其余卡片 `data` 保持为空对象。
- 不得使用 `dataQuery` 或身份参数；可变入参统一平铺进 `data`。
- 组件加载、空数据和失败状态仍由前端组件内部处理，不作为编排条件。

## 可用 MCP 工具

当前账户域可使用以下 MCP 工具获取真实业务数据：

| 序号 | 工具名 | 功能 |
| --- | --- | --- |
| 1 | `queryAssetsTotal` | 查询客户总资产 |
| 2 | `queryAssetIndex` | 查询今日表现（账户管家） |
| 3 | `queryAssetClassify` | 穿透查询资产分类分布，包括基金类型、大类资产、市场区域和行业风格 |
| 4 | `queryHoldingDetail` | 查询持仓明细，支持按资产分类汇总或按基金穿透 |
| 5 | `queryHoldingSignal` | 查询今日持仓提醒 |
| 6 | `queryShareDetail` | 查询份额明细 |
| 7 | `queryProfitAnalyze` | 查询收益分析 |
| 8 | `queryProfitAnalyzeSum` | 查询收益总览 |
| 9 | `queryProfitAttribution` | 查询收益归因，支持产品、类型和行业维度 |
| 10 | `queryProfitCalendar` | 查询收益日历，支持日、月和年视角 |

### MCP 的用途与边界

- MCP 数据主要用于生成有真实数据依据的 `summary`，以及复杂任务的 `conclusion`。
- 账户卡片仍统一输出为 `deferred`，由前端组件自行取数；MCP 返回值不写入 `cards[].data`。
- MCP 调用计划与卡片计划相互独立，不要求一张卡片对应一次 MCP 调用。
- 不得因为选中某张卡片就自动调用其相关 MCP；只根据 `summary`，以及复杂任务 `conclusion` 的最小数据需求选择必要工具。
- 业务 section 只说明 deferred 卡片将展示的内容，不使用未调用 MCP、未返回或无法验证的数据生成分析判断。
- `summary` 和复杂任务的 `conclusion` 只能覆盖本次 MCP 实际返回且校验通过的数据，不得推断未查询的卡片内容。
- MCP 调用失败或数据不足时，不得补造金额、收益率、趋势、归因或诊断结论。
- 工具的请求参数、返回 Schema、鉴权及错误处理以实际 MCP 工具定义为准，本节只记录已知能力。

## 取数边界

- AI 负责识别意图、选择卡片、按需调用已批准的 MCP 工具并生成回复内容，不得生成 `custNo`、账户身份或业务数据。
- `custNo`、`accountName` 等身份及账户上下文必须由可信系统或数据层注入。
- `summary` 和复杂任务 `conclusion` 中使用的金额、收益、净值、行情、持仓及归因数据必须来自本次真实 MCP 响应。
- deferred 卡片展示的数据由前端组件调用真实数据源取得，与 MCP 摘要数据链相互独立。
- 接口参数、鉴权和错误规则未明确的部分，在联调确认前不得自行假设。
- 接口示例中的数值 `0` 和字符串 `"string"` 只表示字段类型，不是业务默认值。

## 账户卡片清单

| 意图大类 | 组件标识 | `cardId` | 卡片名称 | 资产中心接口记录 |
| --- | --- | --- | --- | --- |
| 资产总览 | `acc01-total-asset` | ACC-01 | 账户总资产 | `GET /v1/asset/agent/total` |
| 资产总览 | `acc02-fund-account` | ACC-02 | 基金账户详情 | `GET /v1/asset/agent/total` |
| 资产总览 | `acc03-fund-holding` | ACC-03 | 基金持有详情 | 未记录 |
| 资产总览 | `acc19-fund-holding-summary` | ACC-19 | 产品份额明细 | `GET /v1/asset/agent/share-detail` |
| 资产总览 | `acc04-advisor-account` | ACC-04 | 投顾账户详情 | `GET /v1/asset/agent/total` |
| 资产总览 | `acc05-advisor-combo` | ACC-05 | 投顾组合详情 | 未记录 |
| 资产总览 | `acc06-advisor-rebalance` | ACC-06 | 投顾调仓记录 | 未记录 |
| 资产总览 | `acc07-money-account` | ACC-07 | 货币账户详情 | `GET /v1/asset/agent/total` |
| 资产总览 | `acc08-money-holding` | ACC-08 | 货币持有详情 | 未记录 |
| 资产总览 | `acc09-private-account` | ACC-09 | 专户账户详情 | `GET /v1/asset/agent/total` |
| 资产总览 | `acc10-private-holding` | ACC-10 | 专户持有详情 | 未记录 |
| 持仓结构 | `acc11-position-detail` | ACC-11 | 持仓明细 | `GET /v1/asset/agent/holding-detail` |
| 持仓结构 | `acc12-asset-structure` | ACC-12 | 资产结构 | `GET /v1/asset/agent/list/classify` |
| 收益表现 | `acc13a-return-overview` | ACC-13-A | 账户收益总览 | `GET /v1/asset/agent/analyze/profit/sum` 或 `/yield` |
| 收益表现 | `acc13b-yearly-view` | ACC-13-B | 账户收益总览 · 分年视角 | `GET /v1/asset/agent/analyze/profit/yield` |
| 收益表现 | `acc14-return-calendar` | ACC-14 | 收益明细日历 | `GET /v1/asset/agent/analyze/profit/calendar` |
| 收益归因 | `acc15-return-attribution` | ACC-15 | 收益归因 | `GET /v1/asset/agent/analyze/attribution` |
| 自选基金估值 | `acc18-watchlist-valuation` | ACC-18 | 自选基金估值卡 | 未记录 |

补充约束：

- ACC-16、ACC-17 不在当前卡片清单中，不得生成。
- `GET /v1/asset/agent/index`（账户管家）和 `GET /v1/asset/agent/holding-signal`（今日提醒）暂无对应卡片编号。
- `/holding-detail` 只对应 ACC-11，不得替代 ACC-03、ACC-05、ACC-08 或 ACC-10。
- `/share-detail` 只对应 ACC-19，不得替代其他单产品持有详情卡片。
- “未记录”只表示当前资产中心设计文档没有记录对应接口，不表示卡片不可编排。卡片选择和回复编排不以接口记录或数据状态为前置条件。
- 账户卡片按账户回答大类归属：ACC-01～ACC-15 属账户诊断类，ACC-18 属自选基金类。两个大类的编排与混排规则见 `documentation/AI顾问结果输出与组件编排.md`。

## 公共请求参数

| 参数 | 类型 | 来源 | 说明 |
| --- | --- | --- | --- |
| `custNo` | string | 可信系统注入 | 客户标识；AI 不得生成 |
| `accountName` | string | 用户明确表达或可信系统补齐 | 账户名称或账户范围 |

原始设计文档没有标注以上参数是否必填，也没有说明 `accountName` 的枚举和值域，需在接口联调中确认。

## 接口定义

### 账户总资产和账户详情

`GET /v1/asset/agent/total`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `assetType` | string | 资产类型；原文说明传 `9` 查询全部分类占比，否则查询某一类型汇总 |

已确认取值方式（均不传 `custNo` 和 `accountName`）：

| 卡片 | 取值方式 |
| --- | --- |
| ACC-01 账户总资产 | `{"assetType": "9"}` |
| ACC-02 基金账户详情 | `{"assetType": "1"}` |
| ACC-04 投顾账户详情 | `{"assetType": "6"}` |
| ACC-07 货币账户详情 | `{"assetType": "0"}` |
| ACC-09 专户账户详情 | `{"assetType": "4"}` |

返回字段：

- 汇总：`totalAmt`、`todayActualProfit`、`todayEstimatedProfit`、`balanceProfit`、`totalProfit`、`yieldDate`、`status`、`holdCnt`
- `classifyVoList[]`：`classifyName`、`totalAmt`、`percent`、`todayActualProfit`、`todayEstimatedProfit`、`status`
- `sourceList[]`：`source`、`totalAmt`、`percent`
- `itemList[]`：`serialNo`、`uri`、`isExternal`、`isFirmOffer`、`refNo`、`groupNo`、`groupName`、`fundId`、`fundName`、`todayEstimatedProfit`、`todayActualProfit`、`todayYield`、`balanceProfit`、`balanceYield`、`fundNum`、`yield`

### 持仓明细

`GET /v1/asset/agent/holding-detail`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `type` | string | `1` 按类型；`2` 按基金穿透 |

已确认：ACC-11 持仓明细的取值方式为 `{"type": "1"}`，不传 `custNo` 和 `accountName`。

返回字段：

- 汇总：`totalAmt`、`todayEstimatedProfit`、`todayActualProfit`、`todayYield`、`balanceProfit`、`status`
- `categoryList[]`：`categoryCode`、`classifyName`、`holdCnt`、`totalAmt`
- `categoryList[].itemList[]`：`categoryCode`、`serialNo`、`uri`、`isFirmOffer`、`refNo`、`groupNo`、`groupName`、`isExternal`、`fundId`、`fundName`、`percent`、`marketValue`、`latestPrice`、`dailyChange`、`latestPriceDate`、`nav`、`navDate`、`dailyGrowthRateDisplay`、`balanceProfit`、`balanceYield`、`todayEstimatedProfit`、`todayActualProfit`、`todayChangeRate`、`status`、`fundNum`
- `subFundList[]`：`fundId`、`fundName`、`marketValue`
- `sourceList[]`：string

### 产品份额明细

`GET /v1/asset/agent/share-detail`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `productId` | string | 产品标识 |

返回字段：

- 汇总：`totalAmt`、`todayEstimatedProfit`、`todayActualProfit`、`balanceProfit`、`totalProfit`、`status`、`shareCnt`
- `itemList[]`：`fundId`、`fundName`、`uri`、`marketValue`、`todayEstimatedProfit`、`todayActualProfit`、`todayChangeRate`、`balanceProfit`、`balanceYield`

### 资产结构

`GET /v1/asset/agent/list/classify`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `type` | string | 原文标注值域为 `1/2/3/4`，各值语义待确认 |

返回字段：

- `totalAmt`
- `fundTypeList[]`、`assetClassList[]`、`marketRegionList[]`、`industryStyleList[]`：每项包含 `name`、`amt`、`percent`、`tip`
- `marketRegionPercent`

### 账户收益总览

`GET /v1/asset/agent/analyze/profit/sum`

请求参数：`custNo`、`accountName`。

返回字段：`todayEstimatedProfit`、`todayActualProfit`、`todayYield`、`profit`、`status`、`balanceProfit`、`redeemedProfit`、`totalYield`。

### 账户收益走势图

`GET /v1/asset/agent/analyze/profit/yield`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `dateType` | string | 时间范围类型，值域待确认 |
| `indexCodes` | string | 对比指数代码，多个代码的分隔格式待确认 |

返回字段：

- 汇总：`todayEstimatedProfit`、`todayActualProfit`、`todayYield`、`profit`、`status`、`balanceProfit`、`redeemedProfit`、`totalYield`、`maxDrawdown`、`excessReturn`
- `profitTrend.totalTrendYieldList[]`：`date`、`time`、`value`、`stdValue`
- `profitTrend.indexTrendYieldList[]`：`code`、`name`、`trendYieldVoList[]`
- `trendYieldVoList[]`：`date`、`time`、`value`、`stdValue`
- `profitTrend.supportIndexList[]`：`indexCode`、`indexName`

### 账户收益日历

`GET /v1/asset/agent/analyze/profit/calendar`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `dateType` | string | 日期粒度或范围，值域待确认 |
| `profitType` | string | 收益类型，值域待确认 |
| `date` | string | 查询日期，格式待确认 |

返回字段：

- `calendarType`、`totalProfit`、`curDate`、`preDate`、`nextDate`
- `items[]`：`startDate`、`endDate`、`date`、`profit`、`valid`
- `topGainList[]`、`topLossList[]`：每项包含 `name`、`code`、`profit`、`status`

### 收益归因

`GET /v1/asset/agent/analyze/attribution`

请求参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `custNo` | string | 客户标识 |
| `accountName` | string | 账户名称 |
| `dateType` | string | 时间范围类型；取值见下文「dateType 取值」 |
| `type` | string | 原文说明目前仅实现 `1`，按产品归因 |

返回字段：

- 汇总：`profit`、`earnProfit`、`lossProfit`、`status`
- `topList[]`、`bottomList[]`：每项包含 `name`、`code`、`profit`、`status`

### 账户管家

`GET /v1/asset/agent/index`

请求参数：`custNo`、`accountName`。

返回字段：`yield`、`profit`、`excessYield`、`yieldStatus`。

### 今日提醒

`GET /v1/asset/agent/holding-signal`

请求参数：`custNo`。原始文档使用单字段文本而非 JSON 示例，其实际传参位置和格式待确认。

返回字段：

- `positiveCount`、`watchCount`
- `positive`、`watch`：均包含 `stockName`、`stockCode`、`changeRate`、`amplitude`、`fundCount`、`fundNames[]`、`navRate`、`message`

## dateType 取值

`dateType` 用于收益类接口的时间范围选择。ACC-13-A、ACC-13-B、ACC-14 与 ACC-15 **共用下表同一套取值**；区别在于 `dateType` 的确定方式：

- **ACC-13-A / ACC-13-B / ACC-14**：`dateType` 的默认值由**前端组件内部逻辑**决定，编排层既不选择、也不在卡片信封中传递 `dateType`；前端按组件内置默认取数，无需额外处理。
- **ACC-15 收益归因**：`dateType` **需根据用户意图选择**（如"近一年归因"→`Y1`、"2025 年归因"→`Y2025`、"成立以来归因"→`T`），没有固定默认值。

### 完整取值表

| 代码 | 含义 | 时间范围 | 分组 |
| --- | --- | --- | --- |
| `N` | 今日 | 当日 | 日维度 |
| `L` | 昨日 | 上一日 | 日维度 |
| `M0` | 本月 | 当月1日 至今 | 月维度（滚动） |
| `M1` | 近一月 | 往前推1个月 | 月维度（滚动） |
| `M3` | 近三月 | 往前推3个月 | 月维度（滚动） |
| `M6` | 近六月 | 往前推6个月 | 月维度（滚动） |
| `Y0` | 本年 | 当年1月1日 至今 | 年维度（滚动） |
| `Y1` | 近一年 | 往前推1年 | 年维度（滚动） |
| `Y3` | 近三年 | 往前推3年 | 年维度（滚动） |
| `Y5` | 近五年 | 往前推5年 | 年维度（滚动） |
| `Y20XX` | 指定自然年（如 `Y2024`、`Y2025`） | 该年1月1日 至 12月31日 | 自然年 |
| `T` | 至今（成立以来） | 账户/产品成立日 至今 | 全周期 |

### 分组逻辑

- **N / L** — 日维度（`N` 今日、`L` 昨日）。
- **M 系列** — 月维度滚动区间（`M0` 本月、`M1`/`M3`/`M6` 近 N 月）。
- **Y 系列（数字）** — 年维度滚动区间（`Y0` 本年、`Y1`/`Y3`/`Y5` 近 N 年）。
- **Y20XX** — 自然年区间，支持指定任意年份（如 `Y2024`、`Y2025`）。
- **T** — 成立以来全周期。

### 使用示例

```text
N     → 今日归因
L     → 昨日归因
M1    → 近一月归因
Y1    → 近一年归因
Y5    → 近五年归因
Y2025 → 2025年全年归因
T     → 成立以来归因
```

### ACC-15 意图解析（dateType）

ACC-15 收益归因没有固定 `dateType` 默认值，必须**根据用户意图解析**出 `dateType`，写入卡片的 `data.dateType`（结构见「Deferred 数据模式」，完整取值见上表）。`type`（固定 `"1"`，按产品归因）由前端按 `cardId` 内置，不写入 `data`。

用户表达 → `dateType` 映射：

| 用户表达 | `dateType` |
| --- | --- |
| 今日、今天 | `N` |
| 昨日、昨天 | `L` |
| 本月、这个月 | `M0` |
| 近一月、最近一个月、过去一个月 | `M1` |
| 近三月、最近三个月 | `M3` |
| 近六月、近半年、最近六个月 | `M6` |
| 今年、本年、今年以来、YTD | `Y0` |
| 近一年、最近一年、过去一年 | `Y1` |
| 近三年、最近三年 | `Y3` |
| 近五年、最近五年 | `Y5` |
| 去年、上一年；或指定年份（如"2024 年"） | 自然年代号 `Y20XX`（按当前年份推导：当前 2026 年时，去年 = `Y2025`；"2024 年" = `Y2024`） |
| 成立以来、全部、至今、一直 | `T` |

解析要点：

- 优先按用户**明确表达的时间范围**匹配上表；表达有歧义时取最接近的区间，不得编造用户未给出的区间。
- 自然年表达（"去年""2024 年"）映射为 `Y20XX`，年份按当前日期推导或取用户指定年份。
- 用户**未明确任何时间范围**时（如仅说“分析下收益归因”），`dateType` 默认取 `N`（今日）。

写入示例：

```json
{
  "cardId": "ACC-15",
  "dataMode": "deferred",
  "data": {
    "dateType": "Y1"
  }
}
```

## 数据状态

以下状态用于资产接口响应及前端组件内部的数据处理，不写入当前 deferred 卡片的空 `data`。项目统一状态如下：

| 状态 | 含义 |
| --- | --- |
| `available` | 数据正常可用 |
| `zero` | 数据正常，实际数值为 0 |
| `empty` | 当前统计范围内没有数据 |
| `unavailable` | 数据缺失、接口异常或暂不可用 |
| `estimated` | 当前数据为估算值 |
| `mixed` | 部分数据已确认，部分仍为估算值 |
| `real` | 数据已经确认 |

必须区分：

```text
真实值为 0 ≠ 没有数据
没有数据 ≠ 数据不可用
估算数据 ≠ 已确认数据
```

接口中的 `status`、`yieldStatus` 与项目统一状态之间尚无正式映射。映射确定前必须原样保留接口状态，不得依据数值自行推断。

## 数据失败与降级

- 请求参数缺少可信身份信息时停止取数，不得由模型补造。
- 接口失败、超时或响应不完整时使用 `unavailable` 或结构化错误，不得以 `0` 替代。
- 空数组只有在接口成功且业务上确实没有记录时才能解释为 `empty`。
- `todayEstimatedProfit` 与 `todayActualProfit` 必须分别保留，不得把估算收益冒充实际收益。
- 部分字段可用时保留真实字段，并将整体状态标记为 `mixed`；不得补齐缺失数值。
- 真实数据未返回前，不生成具体金额、收益率、趋势结论或归因结论。

## 待联调确认

1. 所有接口的网关前缀、鉴权方式、统一响应包裹、错误码和超时规则。
2. 各请求参数的必填性、默认值、枚举和值域。
3. `accountName`、`assetType`、`profitType`、`type` 的正式定义；`dateType` 取值见「dateType 取值」，其中 `/analyze/profit/yield`、`/analyze/profit/calendar` 是否与归因同口径待联调确认。
4. `/list/classify` 原文描述写作 `tpe=1/2/3/4`，应确认其为 `type` 的笔误。
5. `indexCodes` 多值传递格式及默认比较基准。
6. 日期字段的格式、时区、交易日口径和统计区间边界。
7. 金额、比例、收益率和净值字段的单位、精度及正负号规则。
8. 接口 `status`、`yieldStatus` 到项目统一数据状态的映射。
