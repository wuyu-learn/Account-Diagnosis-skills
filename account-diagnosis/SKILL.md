---
name: account-diagnosis
description: "处理 AI 顾问的完整问账户链路：读取 Route Extract 路由结果，识别账户二级意图，按需加载账户模块完成卡片选择和取数计划，等待真实数据，并编排最终响应。路由结果包含问账户场景，需要执行账户诊断时使用。"
---

# Account Diagnosis

作为“问账户”业务域的唯一 Skill 入口。以 `documentation/卡片组件.md` 和 `documentation/AI顾问数据与取数协议.md` 为卡片及接口权威源，按本文件规定的顺序加载内部模块，不自行发明意图、卡片、接口字段或业务数据。

## 内部结构

```text
account-diagnosis/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── account-intent-router.md
│   ├── account-asset-overview.md
│   ├── account-holding-structure.md
│   ├── account-return-performance.md
│   ├── account-return-attribution.md
│   ├── account-watchlist-valuation.md
│   └── result-composer.md
├── scripts/
│   ├── build_dispatch_plan.py
│   └── compose_result.py
└── assets/
```

`references/` 中的文件是内部处理模块，不作为独立 Skill 触发。

## 输入

接收 Route Extract 的完整结果，并可接收可信系统层注入的请求上下文：

```json
{
  "routeResult": {
    "scenes": [
      {
        "scene": "问账户",
        "weight": 0.93,
        "subQuery": "我今天账户怎么样"
      }
    ],
    "entities": {},
    "primaryScene": "问账户",
    "isMultiScene": false,
    "orchestration": null,
    "clarify": {
      "needed": false,
      "question": null
    }
  },
  "requestContext": {
    "custNo": "由可信系统注入",
    "accountName": "由可信系统按账户范围注入",
    "sessionId": "由可信系统注入"
  },
  "debug": false
}
```

- 只要 `scenes[]` 中存在 `scene = "问账户"` 就执行，不以 `primaryScene` 为唯一条件。
- `routeResult` 必须来自 Route Extract，不得重新生成或改写。
- 将完整 `routeResult` 原样交给账户意图识别模块；该模块只读取 `scenes` 和 `entities`，忽略 `orchestration`、`clarify` 及其他场景记录。
- `requestContext` 只能原样传给数据层，不得由模型生成或修改。
- 最终响应不得泄露内部身份和鉴权信息。

## 调度流程

### 1. 识别账户意图

完整读取 `references/account-intent-router.md`，严格按照其中的输入、意图枚举和输出协议处理 `routeResult`。

只接受：

```json
{
  "accountScenes": [],
  "primaryAccountIntent": null,
  "isMultiAccountIntent": false
}
```

拒绝 `route_id`、`primary_intent`、`secondary_intents`、`disambiguation`、`next_skills` 及任何未定义 intent。

### 2. 生成模块执行计划

将账户意图结果传给：

```bash
python3 scripts/build_dispatch_plan.py --input dispatch-input.json
```

脚本输入：

```json
{
  "accountIntentResult": {},
  "entities": {},
  "requestContext": {}
}
```

脚本按 `accountScenes[]` 顺序返回需要读取的内部模块。

### 3. 按需加载账户模块

按照执行计划逐项完整读取对应文件：

```text
account_overview
→ references/account-asset-overview.md

holding_structure
→ references/account-holding-structure.md

return_performance
→ references/account-return-performance.md

return_attribution
→ references/account-return-attribution.md

watchlist_valuation
→ references/account-watchlist-valuation.md
```

每个模块接收当前记录的 `intent`、`subQuery` 和实体信息。允许并行处理，但必须按执行计划原始顺序收集结果。

禁止因为 `subQuery` 中出现“收益”“持仓”等词额外加载其他模块。调用范围只由经过校验的 `accountScenes[]` 决定。

模块只输出卡片计划或结构化错误，不生成占位 `sections`：

```json
{
  "intent": "holding_structure",
  "subQuery": "我都买了哪些",
  "cards": []
}
```

### 4. 归一化卡片计划

内部模块直接输出当前卡片结构。只保留 `cardId`、`dataMode` 和 `data`，不得生成旧字段 `type`、`title` 或 `dataQuery`。

归一化结果：

```json
{
  "intent": "holding_structure",
  "subQuery": "我都买了哪些",
  "card": {
    "cardId": "ACC-11",
    "dataMode": "deferred",
    "data": {
      "request": {
        "method": "GET",
        "path": "/v1/asset/agent/holding-detail",
        "params": {
          "custNo": "由可信系统注入",
          "accountName": "由可信系统注入",
          "type": "根据是否穿透基金确定"
        }
      }
    }
  }
}
```

卡片与接口必须符合以下已确认关系：

| 卡片 | 接口 |
| --- | --- |
| ACC-01、ACC-02、ACC-04、ACC-07、ACC-09 | `/v1/asset/agent/total` |
| ACC-11 | `/v1/asset/agent/holding-detail` |
| ACC-12 | `/v1/asset/agent/list/classify` |
| ACC-13-A | `/v1/asset/agent/analyze/profit/sum` 或 `/v1/asset/agent/analyze/profit/yield` |
| ACC-13-B | `/v1/asset/agent/analyze/profit/yield` |
| ACC-14 | `/v1/asset/agent/analyze/profit/calendar` |
| ACC-15 | `/v1/asset/agent/analyze/attribution` |
| ACC-19 | `/v1/asset/agent/share-detail` |

ACC-03、ACC-05、ACC-06、ACC-08、ACC-10、ACC-18 当前没有已确认接口。模块命中这些卡片时返回结构化 `unsupported_card` 错误并停止，不得生成空请求或替代接口。

### 5. 获取真实数据

- `inline`：使用模块已经提供的真实数据。
- `deferred`：将 `data.request` 和可信 `requestContext` 交给数据层。
- `data.request` 必须包含 `method = "GET"`、已确认的 `path` 和对象类型的 `params`。
- 不使用示例值、`${userId}` 等占位符或模型生成值代替真实参数。
- 取数失败时保留真实失败状态，不得改写为 `0`。
- 数据层不可用时停止最终编排，返回结构化错误或待处理状态。

### 6. 编排最终结果

真实数据准备完成后，完整读取 `references/result-composer.md`：

1. 按其中规则生成有数据依据的 `section.title`、`section.narrative` 和 `followUp`。
2. 将规范化的中间 JSON 传给：

```bash
python3 scripts/compose_result.py --input normalized-input.json
```

3. 将脚本标准输出作为最终响应。

最终响应必须包含：

```json
{
  "version": "2.2",
  "meta": {},
  "sections": [],
  "cards": [],
  "risk_warning": "",
  "followUp": []
}
```

没有真实数据时，不得生成具体金额、收益率、趋势、归因或评价。

## 失败处理

出现以下情况时立即停止：

- 内部模块不存在或无法完整读取。
- 模块输出不是合法 JSON。
- intent、cardId 或字段不符合协议。
- cardId 重复或与账户意图归属冲突。
- cardId 不在 `documentation/卡片组件.md` 中。
- cardId 与 `data.request.path` 不符合已确认映射。
- 命中当前无接口的卡片或诉求。
- deferred 取数缺少请求信息。
- 真实数据未返回但流程要求生成结果摘要。
- 拼接脚本校验失败。

不得为了继续流程而补造字段、意图、卡片或数据。

## 调试输出

`debug = true` 时只输出：

```json
{
  "routeExtract": {},
  "accountIntentRouter": {},
  "dispatchPlan": {},
  "accountDomainResults": [],
  "cardPlans": [],
  "dataResults": [],
  "finalResult": null,
  "errors": []
}
```

- 保存每个阶段的真实 JSON，不重新概括。
- 未执行阶段使用 `null`、空对象或空数组。
- 发生错误时写入 `errors` 并停止。
- 不在 JSON 前后添加解释文字。

`debug = false` 时只输出最终响应 JSON。
