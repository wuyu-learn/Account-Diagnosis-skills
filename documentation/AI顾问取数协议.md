# AI 顾问取数协议

## 文档定位

本文档是项目中取数边界、数据提供方式和卡片接口对应关系的统一归档入口，不定义完整响应骨架、内容顺序或页面编排。接口定义、返回字段、数据状态和失败降级见 `documentation/AI顾问数据接口.md`；无已确认接口的卡片清单见 `documentation/AI顾问卡片取数.md`。

当前账户域接口依据：

- 《投顾小程序AI顾问-34113-AI顾问-设计文档》
- 版本：V1.0
- 修订日期：2026-07-23
- 接口归属：资产中心

原始设计文档声明本次接口均为新接口。本文档保留原接口字段的 `camelCase` 命名，不擅自改名。

## 取数边界

- AI 只负责识别意图、选择卡片和生成取数计划，不得生成 `custNo`、账户身份或业务数据。
- `custNo`、`accountName` 等身份及账户上下文必须由可信系统或数据层注入。
- 所有金额、收益、净值、行情、持仓及归因数据必须来自真实接口响应。
- 原始设计文档未说明参数必填性、鉴权方式、统一响应包裹、错误码和超时规则；相关内容在联调确认前不得自行假设。
- 接口返回示例中的数值 `0` 和字符串 `"string"` 仅表示字段类型，不是业务默认值。

## 数据模式

卡片通过 `dataMode` 声明数据提供方式：

| 模式 | 含义 |
| --- | --- |
| `inline` | 数据已经由可信数据层取得并直接包含在当前响应中 |
| `deferred` | 当前响应提供取数请求，后续由编排层或前端调用资产中心接口 |

### Inline

```json
{
  "cardId": "CARD-ID",
  "dataMode": "inline",
  "data": {
    "status": "available"
  }
}
```

- `data` 必须来自真实数据源。
- 数据缺失时返回明确状态，不使用示例值填充。
- 调用方无需再次请求卡片接口。

### Deferred

目前前端把取数写在组件里，`data` 为空：

```json
{
  "cardId": "ACC-13",
  "dataMode": "deferred",
  "data": {
    }
}
```

基本流程：

```text
识别账户意图
→ 选择卡片
→ 生成 data.request
→ 可信系统补齐身份及账户参数
→ 调用资产中心接口
→ 校验并归一化真实响应
→ 编排卡片和文案
```

旧模块中的 `dataQuery.api` 和 `dataQuery.params` 仅作为过渡输入，进入总控流程时归一化为：

```json
{
  "data": {
    "request": {
      "method": "GET",
      "path": "/v1/asset/agent/...",
      "params": {}
    }
  }
}
```

不得在最终卡片中同时保留 `data.request` 和 `dataQuery`。

## 卡片接口对应关系

可取数卡片与资产中心接口的对应关系如下；接口业务参数取值见 `documentation/AI顾问数据接口.md`，无已确认接口的卡片见 `documentation/AI顾问卡片取数.md`。原始接口文档没有直接给出 ACC 编号；未列入映射的卡片不得仅凭接口名称推断为可取数。

| `cardId` | 接口 |
| --- | --- |
| ACC-01 | `GET /v1/asset/agent/total` |
| ACC-02 | `GET /v1/asset/agent/total` |
| ACC-04 | `GET /v1/asset/agent/total` |
| ACC-07 | `GET /v1/asset/agent/total` |
| ACC-09 | `GET /v1/asset/agent/total` |
| ACC-11 | `GET /v1/asset/agent/holding-detail` |
| ACC-12 | `GET /v1/asset/agent/list/classify` |
| ACC-13-A | 简单总览：`GET /v1/asset/agent/analyze/profit/sum`；滚动区间或基准比较：`GET /v1/asset/agent/analyze/profit/yield` |
| ACC-13-B | `GET /v1/asset/agent/analyze/profit/yield` |
| ACC-14 | `GET /v1/asset/agent/analyze/profit/calendar` |
| ACC-15 | `GET /v1/asset/agent/analyze/attribution` |
| ACC-19 | `GET /v1/asset/agent/share-detail` |
