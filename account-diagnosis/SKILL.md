---
name: account-diagnosis
description: "处理主 Agent 分发的问账户任务：代码判定 summary_only/diagnostic，模型只规划意图、deferred 卡片和参数，调用最少必要 MCP 后由主路径脚本一次生成固定 v2.2 JSON；同时保留隔离的卡片测试路径。"
---

# Account Diagnosis

作为 Global Phase B 的“问账户”业务域入口。直接输出账户域最终 v2.2 JSON，不负责跨业务域聚合。

保持 Skill 独立、自包含。只使用本目录的 `SKILL.md`、`references/`、`scripts/` 和 `agents/`。

## 账户顾问的工作立场

本 Skill 的职责是帮助用户看清账户，而不只是展示账户数据。

- 不只播报数据：说明已验证事实与用户当前问题的关系；
- 不承担产品销售：不把账户诊断导向产品推荐；
- 不替用户决策：缺少 KYC、投资目标和风险承受能力时，不给出适配性、买卖或调仓结论；
- `summary_only` 直接回答事实问题，不扩大为账户整体评价；
- `diagnostic` 从组合视角建立结构、表现和归因之间的关系，并指出最值得关注的问题；
- 数据不足时明确判断边界，不用推测填补证据；
- 表达保持清楚、克制、有依据，既不制造焦虑，也不回避已经发现的问题；
- `followUp` 只提供可选的继续诊断方向，不替用户作决定。

## 资源

```text
references/main-path.md              常规主路径唯一运行协议
references/complex-diagnosis.md      diagnostic 诊断规则（按需读取）
references/card-test-mode.md         测试模式 runbook（可移除）
scripts/main_pipeline.py             常规路径 prepare/finalize
scripts/normalize_input.py           共享输入标准化（测试路径继续直接使用）
scripts/build_result_skeleton.py     固定业务骨架生成与计划校验
scripts/enrich_share_identifiers.py  常规路径唯一份额候选回填
scripts/compose_result.py             最终 v2.2 合并与校验
scripts/test_mode/                    测试模式隔离链路（可移除）
```

常规路径只读取 `references/main-path.md`；仅当代码返回 `diagnostic` 时再读取
`references/complex-diagnosis.md`。不要读取已删除的旧分步 reference。

## 上游输入

接收主 Agent 传入的完整 Route Extract JSON：

```json
{
  "originalQuery": "我今年收益怎么样",
  "scenes": [
    {
      "scene": "问账户",
      "weight": 0.95,
      "subQuery": "我今年收益怎么样"
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

执行以下约束：

- 将 `originalQuery` 视为可信上游原样透传的用户问题，禁止改写；
- 处理全部 `scenes[].scene = "问账户"` 的记录，不以 `primaryScene` 为唯一条件；
- 保留完整上游输入，不重新生成、裁剪或包装为 `routeResult`；
- `isMultiScene` 只表示全局场景数量，不表示账户任务复杂度；
- 身份、会话和鉴权只从可信运行时或 MCP 连接取得；
- 没有问账户记录、缺少 `originalQuery` 或输入结构非法时停止并返回结构错误。

## 工作流

### 0. 常规入口准备

常规路径首先调用统一 prepare：

```bash
python3 scripts/main_pipeline.py prepare --input upstream.json --output prepared.json
```

prepare 一次完成输入标准化、测试前缀识别和常规路径
`responseMode` 判定。它输出 `routeExtract`、`testMode` 以及常规路径的
`responseMode`。

若上游已严格提供标准 Route Extract，仍调用 prepare 以取得代码判定的
`responseMode`；OpenClaw 不得自行生成或覆盖该字段。

prepare 内部复用 `normalize_input.py`，并继续保证：

- 将非 JSON 文本（如用户原始问题字符串）转换为标准 Route Extract；
- 补齐缺失的 `originalQuery`（从 `scenes[].subQuery` 派生）；
- 将 `entities` 变体（如 `funds` 对象数组）转换为标准六类字符串数组；
- 为缺失的 `primaryScene`、`isMultiScene`、`orchestration`、`clarify` 填充默认值；
- 当输入没有任何 `scene = 问账户` 或无法得到 `originalQuery` 时返回结构错误。

适配不改变 `originalQuery` 语义。当 `testMode=false` 时进入常规步骤 1；
当 `testMode=true` 时仍转入下方既有测试链路，不使用主路径 finalize。

### 0.5 测试模式（可移除）

仅当 prepare 输出 `testMode=true` 时，继续运行既有测试模式拦截器：

```bash
python3 scripts/test_mode/interceptor.py --input route-extract.json --output test-mode-signal.json
```

拦截器只做一件事：**判断输入是否以 `问账户：` 开头**。

- 若 `originalQuery` 或任一 `scenes[].subQuery` 以 `问账户：` 开头，输出 `{"testMode": true}`，LLM 读取 `references/card-test-mode.md` 后自行决定走全量测试、单卡测试，还是按普通账户问题处理；
- 若未以 `问账户：` 开头，输出 `{"testMode": false}`，继续步骤 1。

具体测试计划（全量 18 张或单卡若干张）由 `scripts/test_mode/interceptor.py` 提供的 `build_test_plan()` 生成，agent 按需调用。测试链路复用共享的 `build_result_skeleton.py` 和 `compose_result.py`；`account_test` 意图下允许诊断类卡片与 `ACC-18` 混排，且不生成 `conclusion`。`queryHoldingDetail`(type=1) 原始数据通过文件传给 `enrich_test_cards.py`，由脚本为份额级卡片（ACC-03/05/06/08/10）及 ACC-19 自动挑值。流水线完成后输出固定 v2.2 JSON 并结束，不进入下方正常流程。

命中测试指令后，完整读取 `references/card-test-mode.md`，按测试链路执行：

```text
interceptor.py → build_result_skeleton.py → enrich_test_cards.py → compose_result.py
```

测试链路复用共享的 `build_result_skeleton.py` 和 `compose_result.py`；`account_test` 意图下允许诊断类卡片与 `ACC-18` 混排，且不生成 `conclusion`。`queryHoldingDetail`(type=1) 原始数据通过文件传给 `enrich_test_cards.py`，由脚本为份额级卡片（ACC-03/05/06/08/10）自动挑 `productId`/`balanceSerialNo`/`uri`（ACC-19 的多渠道 `productId` 判定暂搁置）。流水线完成后输出固定 v2.2 JSON 并结束，不进入下方正常流程。

测试模式自成隔离链路，不修改共享脚本；删除 `scripts/test_mode/`、`references/card-test-mode.md` 和 `tests/test_test_mode.py` 即可完全回退。

### 1. 生成账户计划

完整读取常规路径唯一协议 `references/main-path.md`。基于
`prepared.json.routeExtract` 只输出三个字段：

```json
{
  "primaryAccountIntent": "return_performance",
  "accountScenes": [],
  "cardPlans": []
}
```

不得输出 `responseMode`、`taskComplexity`、`complexityReason`、Section、
MCP 计划或最终信封。模式、复杂度和固定字段全由代码负责。

### 2. 取证并一次生成文字

按 `main-path.md` 选择最少必要 MCP，不按卡片逐张调用。互不依赖的
MCP 尽量在同一工具批次发出。

- `responseMode=summary_only`：生成 `summaryNarrative`，禁止 Conclusion；
- `responseMode=diagnostic`：取数前完整读取 `complex-diagnosis.md`，完成数据质量检查后
  在同一次模型输出中生成 `summaryNarrative` 和
  `conclusionNarrative`。

只使用本次 MCP 实际返回且校验通过的证据；不得使用 deferred
卡片未加载的数据。`followUp` 默认为空数组。

### 3. 一次生成最终 JSON

将 `routeExtract`、三字段账户计划、文字载荷和可选 `shareBindings`
写入 `finalize.json`，调用：

```bash
python3 scripts/main_pipeline.py finalize --input finalize.json --output result.json
```

常规份额候选格式：

```json
[
  {
    "cardId": "ACC-03",
    "productId": "P001",
    "balanceSerialNo": "S001",
    "uri": "..."
  }
]
```

同一 cardId 只有一个且 `balanceSerialNo`/`uri` 完整时才回填；多个候选一律
视为有歧义并保留空 data。常规路径不随机选份额。

finalize 会重新按 `originalQuery` 计算 `responseMode`，忽略模型对复杂度的
任何猜测，然后一次完成骨架、份额回填、Summary/Conclusion 约束、
v2.2 合并和校验。只回传 `result.json` 的 JSON 本体。

## 失败与降级

以下错误必须停止：

- 上游输入缺少原始问题或问账户场景；
- 三字段账户计划输出非法意图、卡片或参数；
- 卡片重复、跨回答大类混排或固定业务骨架被修改；
- `summary_only` 携带 Conclusion；
- `diagnostic` 缺少 Conclusion；
- 最终编排脚本校验失败。

以下数据问题不删除卡片：

- MCP 不可用、失败、空数据或部分可用；
- 缺少可信身份或账户上下文；
- 卡片没有已登记接口或前端尚未取数。

数据不足时只降低文字判断范围。`summary_only` 仍不生成
Conclusion；`diagnostic` 使用 Conclusion 明确无法形成的账户级判断。

## 最终输出

成功时只输出固定 v2.2 JSON：

```json
{
  "version": "2.2",
  "meta": {
    "scene": "问账户",
    "intent": "return_performance"
  },
  "sections": [],
  "cards": [],
  "risk_warning": "投资有风险，请结合自身情况审慎决策。",
  "followUp": []
}
```

顶层只能包含上述六个字段。不得输出 `originalQuery`、`taskComplexity`、账户计划、MCP 原始数据、身份信息、Markdown 代码围栏或解释文字。
