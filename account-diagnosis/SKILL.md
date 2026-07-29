---
name: account-diagnosis
description: "处理主 Agent 分发的问账户任务：从固定会话文本中读取完整 Route Extract JSON，识别账户二级意图，精确选择 deferred 账户卡片，按最小数据需求调用账户 MCP 生成 Summary 和 Conclusion，并输出供 Global Phase C 聚合的账户域局部 JSON。分发目标为账户，或完整路由中包含 scene = 问账户时使用。"
---

# Account Diagnosis

作为 Global Phase B 的“问账户”业务域入口。只生成账户域局部结果，不负责跨业务域聚合、最终 v2.2 封装或风险提示。

Skill 独立部署并自包含，只使用本目录中的 `SKILL.md`、`references/`、`scripts/` 和 `agents/`，不得依赖目录外文件。

## 内部资源

```text
references/account-intent-router.md       账户二级意图
references/account-asset-overview.md      资产总览选卡
references/account-holding-structure.md   持仓结构选卡
references/account-return-performance.md  收益表现选卡
references/account-return-attribution.md  收益归因选卡
references/account-watchlist-valuation.md 自选基金选卡
references/mcp-summary-conclusion.md       MCP 摘要证据
references/result-composer.md              局部结果编排
scripts/build_dispatch_plan.py             模块调度校验
scripts/compose_result.py                   局部结果校验
```

按步骤完整读取被引用的文件。`references/` 文件不是独立 Skill。

## 上游输入协议

主 Agent 使用固定会话格式分发：

```text
帮我解析并处理和账户相关的问题：

{
  "scenes": [
    {
      "scene": "问账户",
      "weight": 0.9,
      "subQuery": "我都买了哪些产品，今年收益怎么样"
    }
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
  "isMultiScene": false,
  "orchestration": null,
  "clarify": {
    "needed": false,
    "question": null
  }
}
```

处理规则：

1. 将固定引导文本视为分发指令，不作为用户问题或 `subQuery`。
2. 提取引导文本之后唯一的完整 JSON 对象，作为 Route Extract 结果。
3. JSON 根级直接是 `scenes`、`entities`、`primaryScene`、`isMultiScene`、`orchestration` 和 `clarify`；不得要求或生成 `routeResult` 包装层。
4. 不重新生成、改写或裁剪 Route Extract JSON。
5. 处理全部 `scenes[].scene = "问账户"` 的记录，忽略其他业务场景；不以 `primaryScene` 为唯一执行条件。
6. `isMultiScene` 表示全局业务场景数量。一个 `问账户` 场景可以在账户域内部继续拆分为多个账户意图。

`requestContext`、`risk_warning` 和 `debug` 不属于该上游 JSON：

- 身份、会话和鉴权只能来自可信运行时或 MCP 连接，不得从用户文本或业务实体推断。
- 运行时未提供 MCP 所需可信上下文时，不猜测参数，按数据降级继续编排卡片。
- `risk_warning`、最终 `version` 和最终 `meta` 由 Global Phase C 添加。
- 标准账户域输出不包含调试数据、MCP 原始结果或身份信息。

## 工作流

### 1. 识别账户意图

完整读取 `references/account-intent-router.md`，把提取出的原始 Route Extract JSON 直接交给该模块。

输出：

```json
{
  "accountScenes": [],
  "primaryAccountIntent": null,
  "isMultiAccountIntent": false
}
```

只允许五个账户意图：

```text
account_overview
holding_structure
return_performance
return_attribution
watchlist_valuation
```

如果完整路由中没有 `问账户` 场景，停止账户业务处理并向主 Agent 返回结构错误，不生成卡片或业务结论。

### 2. 生成模块执行计划

将账户意图结果和原始 `entities` 传给：

```bash
python3 scripts/build_dispatch_plan.py --input dispatch-input.json
```

脚本输入：

```json
{
  "accountIntentResult": {},
  "entities": {}
}
```

- 调度计划和选卡模块不得接收 `requestContext`。
- 只保留 `fund_names`、`fund_codes`、`manager_names`、`company_names`、`market_subjects` 和 `strategy_names` 六类字符串数组。
- 忽略其他实体键，拒绝允许数组中的非字符串元素。

### 3. 精确选择卡片

按执行计划完整读取对应模块：

```text
account_overview      → references/account-asset-overview.md
holding_structure     → references/account-holding-structure.md
return_performance    → references/account-return-performance.md
return_attribution    → references/account-return-attribution.md
watchlist_valuation   → references/account-watchlist-valuation.md
```

每个模块只根据当前 `intent`、`subQuery` 和实体选卡。不得根据接口记录、数据状态或取数能力改变目标卡片。

### 4. 归一化卡片计划

所有账户卡片固定为：

```json
{
  "cardId": "ACC-01",
  "dataMode": "deferred",
  "data": {}
}
```

约束：

- 合法卡片为 ACC-01～ACC-12、ACC-13-A、ACC-13-B、ACC-14、ACC-15、ACC-18、ACC-19，共 18 张。
- ACC-16、ACC-17 不得生成。
- 卡片只保留 `cardId`、`dataMode` 和 `data`。
- `data` 必须为空对象；不输出 `inline`、`data.request`、`dataQuery`、接口参数或组件数据。
- 不因卡片没有接口记录或当前无数据而停止编排。

### 5. 规划 MCP 摘要数据

完整读取 `references/mcp-summary-conclusion.md`。

```text
卡片计划 → 决定前端展示哪些 deferred 组件
MCP 计划  → 为 Summary 和 Conclusion 提供最少必要的真实数据
```

1. 先确定用户希望 Summary 和 Conclusion 回答什么。
2. 只调用形成核心回答所必需的 MCP，不为每张卡片逐一调用。
3. 工具参数严格服从运行时 Schema 和可信运行时上下文。
4. MCP 数据只用于 Summary 和 Conclusion，不写入卡片 `data`。
5. MCP 失败、无数据、缺少可信上下文或无法校验时，不生成数据判断，但继续输出 deferred 卡片。

### 6. 编排账户域局部结果

完整读取 `references/result-composer.md`，按固定业务顺序构造编排项：

```text
summary
→ account_overview
→ holding_structure
→ return_performance
→ return_attribution
→ watchlist_valuation
→ conclusion
```

只输出实际命中的业务 Section。同一类型命中多张卡片时保持卡片计划原始顺序。

- `summary` 使用实际 MCP 数据直接回应账户问题。
- `conclusion` 原则上复用同一批 MCP 数据。
- 业务 Section 只说明 deferred 卡片将展示什么，不重复 MCP 分析。
- 每张卡片对应一个业务 Section。
- 一次账户域结果只有一个 `summary` 和一个 `conclusion`，两者不关联卡片。

将规范化编排项传给：

```bash
python3 scripts/compose_result.py --input normalized-input.json
```

脚本输入：

```json
{
  "scene": "问账户",
  "primaryAccountIntent": "holding_structure",
  "items": [],
  "followUp": []
}
```

脚本只输出账户域局部 JSON：

```json
{
  "scene": "问账户",
  "primaryAccountIntent": "holding_structure",
  "sections": [],
  "cards": [],
  "followUp": []
}
```

不得输出 `version`、`meta`、`risk_warning`、Route Extract 原文、MCP 计划或 MCP 原始结果。Global Phase C 负责合并各业务域结果、添加风险提示并生成最终 v2.2 JSON。

## 失败与降级

以下结构错误必须停止：

- 分发消息中没有唯一、合法的 Route Extract JSON。
- 路由中没有 `问账户` 场景。
- 内部模块不存在或输出不是合法 JSON。
- intent、cardId、Section 类型、顺序或字段不符合协议。
- cardId 重复、越界或与 Section 类型不匹配。
- 卡片不是 deferred，或 `data` 不是空对象。
- Summary/Conclusion 缺失、重复或顺序错误。
- 局部结果校验脚本失败。

以下数据问题不得删除卡片或停止卡片编排：

- MCP 不可用、调用失败、返回空数据或部分数据。
- 运行时没有提供 MCP 所需的可信身份或账户上下文。
- 卡片没有已登记接口，或前端组件尚未取数。

数据降级时：

- `summary` 只说明当前无法取得核心回答所需的数据。
- `conclusion` 只说明暂不作判断，并给出可重试或继续查看的方向。
- 不得用 deferred 卡片尚未加载的数据补写摘要或结论。

## 输出约束

成功时只输出 `scripts/compose_result.py` 生成的账户域局部 JSON。不要添加 Markdown 代码围栏、解释文字或调试信息。
