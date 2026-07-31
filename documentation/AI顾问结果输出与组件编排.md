# AI 顾问结果输出与组件编排

## 文档定位

本文档说明 AI 顾问生成结果的内容结构和页面编排方式，重点描述文字解读、数据卡片、结论、追问及风险提示之间的关系。

## 结果结构

```json
{
  "version": "2.2",
  "meta": {},
  "sections": [],
  "cards": [],
  "risk_warning": "由上游合规规则提供的风险提示",
  "followUp": []
}
```

| 字段 | 职责 |
| --- | --- |
| `version` | 标识当前结果协议版本 |
| `meta` | 描述当前场景、意图及业务上下文 |
| `sections` | 组织回答内容、文字解读和页面展示顺序 |
| `cards` | 保存账户卡片组件；当前统一使用 `deferred` 且 `data` 为空对象 |
| `risk_warning` | 展示统一风险提示 |
| `followUp` | 提供可点击的后续问题 |

## 顶层约束

- `meta.scene` 和 `meta.intent` 决定响应骨架。
- 问账户响应的 `meta.scene` 固定为“问账户”，`meta.intent` 使用账户意图识别结果中的 `primaryAccountIntent`。
- 同一账户回答大类内的复合问题，其他意图通过对应业务 section 的 `type` 表达，不额外修改顶层结构；跨大类意图不混排在同一结果中。
- `sections[]` 和 `cards[]` 是前端消费的主要内容。
- `risk_warning` 必须为上游合规规则提供的非空字符串，并展示在回答末尾。
- `followUp` 可以为空数组。
- 不再使用顶层 `text` 和 `conclusion`；结论统一放入 `sections[]`。

## Sections

`sections[]` 是结果内容和展示顺序的权威来源。每个 section 表示一个页面内容区块。

```json
{
  "type": "return_performance",
  "title": "账户收益表现",
  "narrative": "累计收益、收益率等数据由账户收益组件加载展示。",
  "cardId": "ACC-13-A"
}
```

| 字段 | 职责 |
| --- | --- |
| `type` | 声明内容区块的类型 |
| `title` | 区块标题 |
| `narrative` | 结果摘要、解释或分析文字 |
| `cardId` | 可选，关联需要在当前区块展示的数据卡片 |

section 可以是纯文字区块，也可以关联一张数据卡片：

```text
section.title
→ section.narrative
→ cardId 对应的数据卡片
```

当前账户卡片均为 `deferred`，业务 section 的 `narrative` 只能说明查询范围和卡片将展示的内容。`summary` 和 `conclusion` 可以使用本次 MCP 返回的真实数据生成；没有 MCP 数据依据时，不得生成金额、收益率、趋势、归因或诊断结论。卡片结构和数据规则见 `documentation/AI顾问账户卡片与数据.md`。

## 账户回答类型

“问账户”分为两个账户回答大类：

- **账户诊断类**：资产总览、持仓结构、收益表现、收益归因，对应 ACC-01～ACC-15。
- **自选基金类**：自选基金估值，对应 ACC-18。

一次账户域结果只属于其中一个大类，由本次问账户分发的 `primaryAccountIntent` 所在大类决定，用一对 `summary` 和 `conclusion` 包裹该大类命中的业务 section。同一大类内的多个意图按固定业务顺序混排；当一次问账户分发同时包含两个大类的意图时，账户域只处理 `primaryAccountIntent` 所在大类，丢弃另一大类，不为被丢弃的大类生成 section 或卡片。

### 账户诊断类

标准结构：

```text
summary
→ account_overview
→ holding_structure
→ return_performance
→ return_attribution
→ conclusion
```

| `section.type` | 作用 |
| --- | --- |
| `summary` | 基于必要的 MCP 数据直接回应用户并概括核心结果 |
| `account_overview` | 展示账户规模、账户构成和具体账户情况 |
| `holding_structure` | 展示持仓明细、资产分布和集中度 |
| `return_performance` | 展示收益结果、分年表现和收益明细 |
| `return_attribution` | 说明收益贡献、收益拖累及原因 |
| `conclusion` | 基于同一批 MCP 数据收束回答并给出后续方向 |

`summary` 和 `conclusion` 构成回答的外层结构。中间业务 section 根据用户实际问题选择，不要求每次全部出现，并按照上表中的业务顺序编排。

例如，只询问收益表现时：

```text
summary
→ return_performance
→ conclusion
```

要求完整账户诊断时：

```text
summary
→ account_overview
→ holding_structure
→ return_performance
→ return_attribution
→ conclusion
```

同一业务类型需要展示多张卡片时，可以生成多个相同 `type` 的 section，通过不同的 `title` 和 `cardId` 区分具体内容。例如 ACC-11 持仓明细和 ACC-12 资产结构均使用 `holding_structure`。

### 标准模板与意图选卡

账户意图和标准回复模板承担不同职责：

- 账户意图和 `subQuery` 用于精确选择卡片，决定回答需要哪些业务数据。
- 标准回复模板用于组织完整回答，决定 `summary`、业务 section 和 `conclusion` 的结构与顺序。

完整处理链路：

```text
用户问题
→ 账户意图识别
→ 根据 subQuery 选择精确卡片
→ 根据回答类型选择标准模板
→ 将卡片放入对应业务 section
→ 生成统一的 summary 和 conclusion
```

一个具体子意图即使只命中一张卡片，最终回复也必须使用完整模板。例如，用户询问今年收益并命中 ACC-13-A 时，回复结构是：

```text
summary
→ return_performance + ACC-13-A
→ conclusion
```

同一账户回答大类内的复合问题命中多张卡片时，只生成一个公共 `summary` 和一个公共 `conclusion`，中间按业务顺序放入各卡片对应的业务 section：

```text
summary
→ holding_structure + ACC-11
→ return_performance + ACC-13-A
→ return_attribution + ACC-15
→ conclusion
```

编排层使用上游账户模块已经确定的卡片结果，不重新分类意图，不因文案中出现“收益”“持仓”等词额外增加或替换卡片。卡片决定模板中间的业务内容，但卡片本身不等于完整回复。编排层不检查卡片的接口记录、数据状态或取数结果。

#### 资产总览

| 用户意图 | 精确卡片 | 对应 `section.type` |
| --- | --- | --- |
| 未指定账户类型，询问总资产、钱的构成或账户整体情况 | ACC-01 | `account_overview` |
| 询问基金账户整体、收益或账户内产品 | ACC-02 | `account_overview` |
| 询问指定基金的整体持有情况 | ACC-03 | `account_overview` |
| 询问指定产品的份额明细 | ACC-19 | `account_overview` |
| 询问投顾账户整体、组合数量或账户收益 | ACC-04 | `account_overview` |
| 询问指定投顾组合的整体、收益或组合持仓 | ACC-05 | `account_overview` |
| 询问指定投顾组合的调仓记录 | ACC-06 | `account_overview` |
| 询问货币账户、货币基金账户或现金宝整体情况 | ACC-07 | `account_overview` |
| 询问指定货币基金的持有情况 | ACC-08 | `account_overview` |
| 询问专户账户整体情况 | ACC-09 | `account_overview` |
| 询问指定专户产品的持有情况 | ACC-10 | `account_overview` |

#### 持仓结构

| 用户意图 | 精确卡片 | 对应 `section.type` |
| --- | --- | --- |
| 询问买了哪些、持仓列表或每只持仓的表现 | ACC-11 | `holding_structure` |
| 询问资产分布、配置结构、穿透维度或集中度 | ACC-12 | `holding_structure` |
| 同时询问持仓明细和资产结构 | ACC-11、ACC-12 | 分别生成两个 `holding_structure` section |

#### 收益表现

| 用户意图 | 精确卡片 | 对应 `section.type` |
| --- | --- | --- |
| 泛问赚亏、累计收益、收益率、滚动区间或基准比较 | ACC-13-A | `return_performance` |
| 明确询问去年、历年或自然年度收益 | ACC-13-B | `return_performance` |
| 询问每日、每月、每年收益明细或哪段时间赚亏 | ACC-14 | `return_performance` |
| 同时询问多个收益视角 | 按命中的 ACC-13-A、ACC-13-B、ACC-14 分别生成 section | `return_performance` |

#### 收益归因

| 用户意图 | 精确卡片 | 对应 `section.type` |
| --- | --- | --- |
| 询问为什么赚亏、主要贡献产品或主要拖累产品 | ACC-15 | `return_attribution` |

ACC-15 只生成一个 `return_attribution` section，由同一张卡片展示贡献项和拖累项，不拆成重复引用 ACC-15 的多个 section。当前为 deferred 模式，服务端 `narrative` 不提前生成归因解释。

### 自选基金类

自选基金估值关注用户的自选或关注列表，不参与账户资产、持仓、收益和归因的诊断链路，使用独立结构：

```text
summary
→ watchlist_valuation
→ conclusion
```

| `section.type` | 作用 |
| --- | --- |
| `summary` | 在存在可用 MCP 数据时概括自选基金核心结果 |
| `watchlist_valuation` | 展示自选基金估值、当日涨跌和净值更新情况 |
| `conclusion` | 在存在可用 MCP 数据时收束回答并给出后续方向 |

用户询问自选或关注基金的当日估值、涨跌或净值更新情况时，精确选择 ACC-18，并生成一个 `watchlist_valuation` section 和 deferred 卡片。是否已有接口或数据不影响该卡片进入编排。

自选基金类结果是否生成，取决于本次问账户分发的 `primaryAccountIntent` 是否属于自选基金类；当 primary 意图属于账户诊断类时，自选意图被丢弃，不生成自选类 section。

### MCP 驱动的 Summary 与 Conclusion

卡片计划和 MCP 数据计划相互独立：

```text
用户问题
├── 卡片计划
│   └── 根据具体子意图选择 deferred 卡片
│
└── MCP 数据计划
    └── 根据 summary 和 conclusion 的最小数据需求选择工具
```

选中卡片不代表必须调用与其业务相近的 MCP。只有当 `summary` 或 `conclusion` 需要某项真实数据时，才调用能够提供该数据的 MCP。

完整流程：

```text
识别用户希望得到的核心回答
→ 确定 summary 和 conclusion 所需的最小数据
→ 选择并调用必要 MCP
→ 校验 MCP 返回状态和数据范围
→ 基于 MCP 真实数据生成 summary
→ 生成 deferred 业务 section 和卡片
→ 基于同一批 MCP 数据生成 conclusion
```

#### 总体生成思路

```text
summary = 查询范围 + 1～3 个关键 MCP 事实 + 直接回答
conclusion = 整体判断 + 主要关注点 + 后续方向
```

| 内容 | `summary` | `conclusion` |
| --- | --- | --- |
| 回答的问题 | 结果是什么 | 应该怎么看 |
| 位置 | 回答开头 | 回答结尾 |
| 数据依据 | 最少必要的 MCP 真实数据 | 原则上复用 summary 的同一批 MCP 数据 |
| 内容重点 | 关键事实和直接答案 | 综合判断和后续关注方向 |
| 长度建议 | 1～3 句话 | 1～2 句话 |

`summary` 不写“下面为您展示”等空泛引导语；`conclusion` 不重复摘要，也不得引入 MCP 未返回的新事实。两者都不得根据 deferred 卡片推断数据。

#### Summary 生成规则

- `summary` 直接回应用户问题，优先表达最重要的一至三个事实。
- `summary` 中的金额、收益率、持仓、行情、归因和诊断判断必须来自本次实际 MCP 响应。
- 只调用形成核心回答所必需的 MCP，不为了覆盖所有已选卡片扩大调用范围。
- 同一账户回答大类内的复合问题只生成一个公共 `summary`，可以综合多个 MCP 的已确认结果。
- 不得在 `summary` 中概括未调用 MCP 的卡片内容。

#### Conclusion 生成规则

- `conclusion` 使用本次已经取得的 MCP 数据对回答进行收束，不为每张卡片分别生成结论。
- `conclusion` 原则上复用为 `summary` 已调用的 MCP，不因存在 deferred 卡片自动增加工具调用。
- 只有用户明确要求进一步诊断，且现有 MCP 数据不足时，才增加完成该判断所必需的 MCP。
- `conclusion` 只能覆盖实际查询的数据范围，不得把局部结果扩展为完整账户判断。
- 后续可查看的卡片或问题通过 `conclusion` 和 `followUp` 引导，不需要为此预先调用对应 MCP。

#### MCP 选择参考

下表按 summary 和 conclusion 需要回答的内容选择 MCP，不表示 MCP 与卡片一一绑定：

| 摘要或结论需要的数据 | 可用 MCP |
| --- | --- |
| 客户总资产和账户构成 | `queryAssetsTotal` |
| 今日账户表现 | `queryAssetIndex` |
| 资产分类、市场、区域、行业和集中度 | `queryAssetClassify` |
| 持仓数量、持仓构成和基金穿透 | `queryHoldingDetail` |
| 今日持仓提醒 | `queryHoldingSignal` |
| 指定产品份额 | `queryShareDetail` |
| 区间收益、收益走势和比较分析 | `queryProfitAnalyze` |
| 收益总览 | `queryProfitAnalyzeSum` |
| 产品、类型或行业收益归因 | `queryProfitAttribution` |
| 日、月或年收益日历 | `queryProfitCalendar` |

#### 业务 Section 的文案边界

- 业务 section 关联 deferred 卡片，只说明卡片将展示的内容。
- MCP 数据默认只用于 `summary` 和 `conclusion`，不要求在每个业务 section 中重复分析。
- MCP 返回值不写入 `cards[].data`，卡片仍由前端组件自行取数。
- MCP 与前端卡片应使用一致的用户、账户范围、时间范围和业务口径。

#### 失败与数据不足

- MCP 调用失败、返回空数据或结果无法校验时，不得生成数据结论。
- `summary` 只能明确说明当前无法取得回答所需的数据。
- `conclusion` 只能说明暂不作业务判断，并提供可重试或继续查看的方向。
- 单个 MCP 失败不影响无依赖关系的 deferred 卡片输出，但不得用卡片尚未加载的数据补写摘要或结论。

### Section 与卡片的关联规则

- 每次完整回复只生成一个 `summary` 和一个 `conclusion`，两者不关联卡片。
- `summary` 根据本次用户问题和实际 MCP 数据概括核心结果，不总结未查询的数据。
- `conclusion` 基于同一批 MCP 数据形成整体收束和后续方向，不为每个子意图重复生成。
- 每个业务 section 最多关联一张卡片，`section.cardId` 必须等于该卡片的 `cardId`。
- 同一意图命中多张卡片时，为每张卡片分别生成一个业务 section。
- 同一个 `cardId` 在一次响应中只能出现一次，也只能被一个 section 关联。
- 业务 section 的 `type` 由账户意图确定，标题和展示范围由精确卡片编号确定。
- 卡片是否已有接口、是否能够取数或当前是否有数据，不属于编排层的判断条件。
- deferred 卡片对应的业务 section 只能生成不包含具体数值、趋势或判断的中性文字；这一限制不影响 `summary` 和 `conclusion` 使用真实 MCP 数据。

## Cards

`cards[]` 是卡片数据池，不决定页面展示顺序。section 通过 `cardId` 查找相同标识的卡片。

```json
{
  "cardId": "CARD-ID",
  "dataMode": "deferred",
  "data": {}
}
```

当前账户卡片统一使用 `deferred`，`data` 为空对象，由前端组件完成取数。

前端的基本处理流程：

```text
按顺序遍历 sections[]
→ 渲染标题和文字内容
→ 检查是否存在 cardId
→ 从 cards[] 查找对应卡片
→ 在当前区块中渲染卡片
```

## 完整输出示例

以下示例对应用户问题“我的账户今年收益怎么样”。具体子意图命中 ACC-13-A；系统只调用生成摘要和结论所需的 `queryProfitAnalyzeSum`，假设 MCP 实际返回今年累计收益 1250.35 元、累计收益率 3.20%，卡片仍保持 deferred：

```json
{
  "version": "2.2",
  "meta": {
    "scene": "问账户",
    "intent": "return_performance"
  },
  "sections": [
    {
      "type": "summary",
      "title": "今年收益概况",
      "narrative": "根据账户收益总览数据，今年以来累计收益为 1250.35 元，累计收益率为 3.20%。"
    },
    {
      "type": "return_performance",
      "title": "账户收益表现",
      "narrative": "累计收益、收益率及当前持有收益等数据由账户收益组件加载展示。",
      "cardId": "ACC-13-A"
    },
    {
      "type": "conclusion",
      "title": "综合结论",
      "narrative": "今年以来账户整体取得正收益；如需进一步了解收益的持续性和来源，可以继续查看历年收益和收益归因。"
    }
  ],
  "cards": [
    {
      "cardId": "ACC-13-A",
      "dataMode": "deferred",
      "data": {}
    }
  ],
  "risk_warning": "投资有风险，请结合自身情况审慎决策。",
  "followUp": [
    "查看我的历年收益",
    "分析我的收益来源"
  ]
}
```

示例中的数值只用于说明“MCP 文案数据链”和“deferred 卡片数据链”的关系，不是业务默认值。实际 `summary` 和 `conclusion` 必须使用本次 MCP 的真实返回；业务 section 不重复分析 MCP 数据，卡片继续由前端组件取数且 `data` 保持为空对象。

## 典型编排

```text
MCP 数据摘要
→ 业务说明 + deferred 数据卡片
→ MCP 数据结论
→ 后续问题
→ 风险提示
```

其中：

- MCP 数据摘要、业务说明和 MCP 数据结论属于 `sections[]`。
- 账户数据组件属于 `cards[]`，由前端组件完成取数。
- 后续问题来自 `followUp`。
- 页面底部风险提示来自 `risk_warning`。

## 结构边界

- `sections[]` 负责“表达什么、按什么顺序展示”。
- `cards[]` 负责“使用什么数据渲染组件”。
- section 不应复制完整卡片数据。
- card 不负责标题、分析文字及页面顺序。
- 没有 `cardId` 的 section 按纯文字区块展示。
- 前端不得根据 `cards[]` 的排列顺序重新组织回答。
