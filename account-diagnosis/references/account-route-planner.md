# Account Route Planner

## 目录

- 职责
- 上游输入
- 账户意图
- 复杂度
- 输出

## 职责

读取上游完整 Route Extract 输入，一次完成：

```text
识别账户意图
→ 判断任务复杂度
→ 选择卡片
→ 识别卡片参数
→ 输出账户内部计划
```

只输出计划，不回答用户问题，不调用 MCP，不生成卡片结构或 Section。

完整读取 `references/account-card-routing.md` 后再规划卡片。该文件是单卡映射、复合问题组合和完整诊断默认组合的唯一规则来源；不要在 Planner 中创造其他组合。

## 上游输入

上游必须原样提供：

```json
{
  "originalQuery": "用户原始问题",
  "scenes": [],
  "entities": {},
  "primaryScene": "问账户",
  "isMultiScene": false,
  "orchestration": null,
  "clarify": {
    "needed": false,
    "question": null
  }
}
```

规则：

- `originalQuery` 是可信上游透传的原始文本，禁止改写或在计划中重复生成；
- 处理全部 `scenes[].scene = "问账户"` 的记录，忽略其他业务域；
- `primaryScene` 和 `isMultiScene` 是全局路由信息，不表示账户任务复杂度；
- 保留六类 `entities`，只使用用户明确提供的实体；
- ACC-19 `productId` 是产品代码（不是基金代码），上游/实体已提供时透传（规则见 `account-card-routing.md` 参数边界）；`serialNo`/`uri` 不在 plan 阶段填，属份额级，由 MCP 后回填步骤处理；
- 没有问账户记录时返回结构错误，不生成账户计划。

## 账户意图

`accountScenes[].intent` 只允许：

| intent | 范围 |
| --- | --- |
| `account_overview` | 总资产、分账户、组合、单产品持有和份额 |
| `holding_structure` | 持仓明细、资产/地区/行业结构和集中度 |
| `return_performance` | 收益总览、分年表现、收益日历和基准比较 |
| `return_attribution` | 收益贡献、拖累和原因 |
| `watchlist_valuation` | 自选基金估值、净值更新和当日涨跌 |

一个独立账户诉求生成一条 `accountScenes`。数组按权重降序；第一条 intent 为 `primaryAccountIntent`。

用户明确要求完整账户诊断、账户体检或整体分析时，按 `account-card-routing.md` 的完整诊断规则展开所需 `accountScenes` 和 `cardPlans`。一般 complex 关系问题仍只覆盖用户实际要求的维度，不自动扩展为完整诊断。

## 复杂度

### simple

满足以下条件时输出 `simple`：

- 对象和回答目标明确；
- 每个子问题都能作为独立事实问题回答；
- 不要求解释多个诊断维度之间的关系；
- 一个 Summary 可以直接完成回答。

多张卡片不自动升级为 complex。例如“我都买了什么，今年赚了多少”仍是 simple。

### complex

满足任一条件时输出 `complex`：

- 要求整体账户诊断、体检或主要问题判断；
- 要求综合结构、收益、超额收益、回撤或归因；
- 要求解释两个以上诊断维度之间的关系；
- 要求确定主要贡献、主要拖累或问题优先级。

单张卡片也可能对应 complex；复杂度不能按问题长度、卡片数量或 MCP 数量判断。

判断顺序：

```text
是否明确要求整体诊断？
├── 是 → complex
└── 否
    ↓
是否需要建立两个以上诊断维度的关系？
├── 是 → complex
└── 否
    ↓
各子问题能否独立直接回答？
├── 是 → simple
└── 否 → complex
```

自选基金估值固定为 simple，并且不能与账户诊断类卡片混排。

## 输出

只输出合法 JSON：

```json
{
  "taskComplexity": "simple",
  "complexityReason": "用户只询问本年收益，不需要跨维度诊断",
  "primaryAccountIntent": "return_performance",
  "accountScenes": [
    {
      "intent": "return_performance",
      "weight": 0.95,
      "subQuery": "我今年收益怎么样"
    }
  ],
  "cardPlans": [
    {
      "cardId": "ACC-13-A",
      "params": {}
    }
  ]
}
```

输出约束：

- 顶层只能包含示例中的五个字段；
- `taskComplexity` 只允许 `simple` 或 `complex`；
- `complexityReason` 必须说明是否需要跨维度诊断；
- `primaryAccountIntent` 必须等于第一条 `accountScenes` 的 intent；
- `cardPlans` 只包含 `cardId` 和 `params`；
- `cardPlans` 必须来自 `account-card-routing.md`，多个独立问题先分别选卡再合并去重；
- 不输出 `originalQuery`、`dataMode`、Section、MCP 计划或最终响应字段；
- 卡片计划只覆盖 `primaryAccountIntent` 所属回答大类；
- 同一个 cardId 只能出现一次。
