# AI 顾问数据接口

## 文档定位

本文档是项目中接口定义、返回字段、数据状态和失败降级的统一归档入口，不定义完整响应骨架、内容顺序或页面编排。取数边界、数据提供方式和卡片接口对应关系见 `documentation/AI顾问取数协议.md`；卡片清单及无已确认接口的卡片见 `documentation/AI顾问卡片取数.md`。

当前账户域接口依据：

- 《投顾小程序AI顾问-34113-AI顾问-设计文档》
- 版本：V1.0
- 修订日期：2026-07-23
- 接口归属：资产中心

原始设计文档声明本次接口均为新接口。本文档保留原接口字段的 `camelCase` 命名，不擅自改名。

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
| `dateType` | string | 时间范围类型，值域待确认 |
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

## 数据状态

`dataMode` 与数据状态相互独立。项目统一状态如下：

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
3. `accountName`、`assetType`、`dateType`、`profitType`、`type` 的正式定义。
4. `/list/classify` 原文描述写作 `tpe=1/2/3/4`，应确认其为 `type` 的笔误。
5. `indexCodes` 多值传递格式及默认比较基准。
6. 日期字段的格式、时区、交易日口径和统计区间边界。
7. 金额、比例、收益率和净值字段的单位、精度及正负号规则。
8. 接口 `status`、`yieldStatus` 到项目统一数据状态的映射。
