# Card Test Mode（测试模式 runbook）

> 本文件属于**可移除的测试模式层**。命中测试指令后由 LLM 读取执行；正常问账户流程不读本文件。设计推演见 `documentation/重构计划/卡片测试.md`。

## 职责与触发

提供一条**确定性路径**验收卡片编排：给定固定测试输入，固定输出卡片，绕过 Planner 的语义判断。

触发：

`interceptor.py` 只判断输入是否以 `问账户：` 开头。只要命中，agent 读取本文件后自行决定具体模式：

- **全量模式**：`originalQuery` 或任一 `subQuery` 在 `问账户：` 之后包含 `全部卡片测试`，或明确表达“全部/所有卡片”语义 → 输出 18 张账户卡片；
- **单卡模式**：`originalQuery` 或任一 `subQuery` 在 `问账户：` 之后包含有效 `ACC-XX` 或 `ACC-XX-X` 卡号 → 只输出指定卡片；
- **模糊 fallback**：看起来像卡片测试（提到“卡片/卡”或“测试/测”）但分不清单卡还是全量时 → **统一按全量模式输出**；
- 未以 `问账户：` 开头，或 agent 判断不属于测试 → 回到正常账户流程。

例如：
- `问账户：全部卡片测试` → 全量
- `问账户：测一下全部卡片` → 全量
- `问账户：ACC-19测试` → 单卡 ACC-19
- `问账户：ACC-01卡片` → 单卡 ACC-01
- `问账户：卡片测试` → 不确定，fallback 全量
- `问账户：测试` → 不像卡片测试，由 agent 判断（通常回到正常流程）
- `问账户：我今年收益怎么样` → 正常账户问题，不走测试链路

测试信号只来自输入文本中的关键字，不改 `meta.intent` 协议。

命中后识别为 `account_test` 意图：`taskComplexity=simple`、`primaryAccountIntent=account_test`，`cardPlans` 由固定规则决定。

## 与正常流程的分发

```text
normalize_input.py（现有，不改）
→ scripts/test_mode/interceptor.py（可移除）
    ├── 命中关键字 → 输出 account_test 计划，进入测试链路
    └── 未命中     → 输出 {"testMode": false}，回到正常步骤 1
```

命中后走测试链路，该链路**复用**共享脚本 `build_result_skeleton.py` 和 `compose_result.py`，只在 `account_test` 意图下放宽诊断/自选混排约束。份额级标识回填仍使用 `scripts/test_mode/enrich_test_cards.py`，从 `queryHoldingDetail` 的产品项自动挑标识。

## 固定 cardPlans

`interceptor.py` 输出标准账户计划：`taskComplexity=simple`、`primaryAccountIntent=account_test`、第一条 `accountScenes` 为 `account_test`，后续补充测试卡片涉及的真实意图（`account_overview`、`holding_structure`、`return_performance`、`return_attribution`、`watchlist_valuation`），以满足共享骨架校验。

cardPlans 含全部账户卡片：

```text
ACC-01 ~ ACC-10                账户级各类型
ACC-11、ACC-12                  持仓与资产结构
ACC-13-A、ACC-13-B、ACC-14      收益
ACC-15（dateType=N）            归因
ACC-18                          自选基金（与诊断类混排，测试模式放宽）
ACC-19（params={}）             产品份额明细，空参占位
```

份额级卡片 ACC-03/05/06/08/10 在拦截器阶段 `params={}`（目标份额要 MCP 后才知道）。

单卡模式只输出指定卡片，`accountScenes` 包含 `account_test` 加上指定卡片涉及的真实意图。

## ACC-19 的 `productId`

ACC-19 的目标份额由 `enrich_test_cards.py` 从 `queryHoldingDetail`(type=1) 中自动挑选：

- 优先挑**多渠道** `fundId`（同一 `fundId` 在 holdingDetail 中出现且 `serialNo` ≥ 2）；
- 无多渠道时 fallback 到任意 `fundId`；
- 无任何产品时 `data` 为空。

注入值为单值字符串 `productId`，与 `account_contract.py` 对 ACC-19 的契约一致。

## 份额级卡片的取值（ACC-03/05/06/08/10）

每张份额级卡片输出三个定位标识，全部由 `enrich_test_cards.py` 按规则自动挑，LLM 不手填：

- `productId`：挑中产品项的 `fundId`；
- `balanceSerialNo`：产品项的 `serialNo`（**输出字段名是 `balanceSerialNo`**）；
- `uri`：产品项的 `uri`。

三个字段**同源**——都来自挑中的那一个产品项。

数据源是 `queryHoldingDetail`(type=1)：其 `categoryList[].itemList[]` 是**产品级**列表，每个产品项带 `fundId`/`serialNo`/`uri`，**一个 MCP 同时覆盖大类归属和份额标识**（不再依赖 `queryShareDetail`，避免几百笔份额响应在 LLM context 截断）。

挑数规则：在该大类（`categoryCode`）的产品项里，**优先挑 `fundId`+`serialNo`+`uri` 三字段齐全的一项**，让三个字段都能填；该大类没有三字段齐全的，**再随机挑一项**，缺的字段不填。

```text
queryHoldingDetail(type=1) → categoryList[categoryCode].itemList[] 产品项
                            → 优先三字段齐全；否则随机挑一项
                            → 注入 data.productId / data.balanceSerialNo / data.uri (缺的不填)
```

| 卡片 | 大类（categoryCode） |
| --- | --- |
| ACC-03 | `1`（公募基金） |
| ACC-05、ACC-06 | `6`（投顾） |
| ACC-08 | `0`（货币） |
| ACC-10 | `4`（资管/专户） |

大类下无任何产品项（`itemList` 为空或无该大类）→ 三字段都不填，卡片保留。

## LLM 任务

测试模式是 simple 路径，`primaryAccountIntent=account_test`，LLM 做以下事情，**不生成 Conclusion**：

1. 跑通骨架：`build_result_skeleton.py`（account_test 意图下允许诊断/自选混排）；
2. **按需调 MCP**：检查 `test-plan.json` 的 `cardPlans` 中是否包含需要回填的卡片：
   - 含 `ACC-03/05/06/08/10`（份额级标识）或 `ACC-19`（产品份额明细的 `productId`）→ 调 `queryHoldingDetail`(type=1)，写 `holding_detail.json`，跑 `enrich_test_cards.py`；
   - 其他卡片（ACC-01/02/04/07/09/11/12/13-A/13-B/14/15/18）→ **跳过 MCP 和 enrich**，直接进入 compose；
3. 生成一个固定 Summary（如"这是卡片测试"）。

MCP 返回**原封不动**写入文件，不截断、不筛选、不加工。
不调 Planner、不做意图识别、不做诊断判断。

## 脚本序列

```text
interceptor.py         --input route-extract.json  --output test-plan.json
build_result_skeleton.py --input test-plan.json           --output skeleton.json

【cardPlans 含 ACC-03/05/06/08/10 或 ACC-19】
  LLM: queryHoldingDetail(type=1) → holding_detail.json
  enrich_test_cards.py --business-items skeleton.json \
                       --holding-detail holding_detail.json \
                       --seed 42 --output enriched.json

【其他卡片（ACC-01/02/04/07/09/11/12/13-A/13-B/14/15/18）】
  跳过 MCP 和 enrich，skeleton.json 的 businessItems 直接用于 compose。

compose_result.py --input compose.json        --output result.json   # v2.2
```

MCP 原始数据通过文件传给 `enrich_test_cards.py`，不经过 LLM 再加工，避免截断导致 fundId 交叉匹配失败。
`compose.json` = `scene` + `taskComplexity` + `primaryAccountIntent=account_test` + businessItems + `summary` + `followUp`。

流水线完成后两件事，缺一不可：

1. **清理文件系统**：LLM 删除测试产生的中间文件（拦截器计划、骨架、MCP 原始响应 `holding_detail.json`、`enriched.json`、`compose.json` 等），只保留最终 `result.json` 供联调。
2. **回传 JSON 本体**：将 `result.json` 的 v2.2 JSON **作为最终输出回传**——纯 JSON，顶层只有六个字段，不带文件路径、任务摘要、执行流程、代码围栏或任何解释文字。

不得用「已存储到 `result.json`」、任务完成摘要或路径报告代替 JSON 本体；`SKILL.md` 的「最终输出」契约（只输出固定 v2.2 JSON、不得输出解释文字）在测试模式下同样生效。

## 测试模式放宽的契约边界

只在 `scripts/test_mode/` 内生效，共享脚本与其他 references 不受影响：

- **诊断/自选混排**：允许 ACC-18 与诊断类同出。
- 其余约束（卡片编号合法、同 cardId 不重复、参数必须字符串、`CARD_SPECS` 允许参数、dataMode=deferred、意图覆盖、primary 有卡、section 顺序、ACC-15 dateType、title/narrative 逐字匹配）保持启用。

## 联调字段（实测 schema；不符时仅改 `enrich_test_cards.py` 顶部常量）

- **`body` 包装**：真实响应是 `{returnCode, body:{categoryList, ...}}`，列表在 `body` 下。`enrich_test_cards.py` 的 `_extract_items` 会穿透 `body`，也兼容顶层 list 或直接数组——LLM 把 MCP 响应原样写文件即可，不需手动剥 `body`。
- `queryHoldingDetail`(type=1)：`body.categoryList[]` 每项含 `categoryCode`/`classifyName`/`holdCnt`/`totalAmt` + `itemList[]`。`itemList[]` 是**产品级**（每产品一项），每项含 `fundId`、`fundName`、`serialNo`、`uri`、`marketValue`、`percent`、`balanceProfit`、`balanceYield` 等（`uri` 偶有为 null）；组合/投顾产品带 `subFundList`。enrich 只用 `fundId`/`serialNo`/`uri` 三字段。
- 份额级卡片→大类映射见上表。

## 回退

删 `scripts/test_mode/` + `references/card-test-mode.md` + `tests/test_test_mode.py` + `SKILL.md` 的「0.5 测试模式」段与资源清单两行 → 共享脚本与现有 references 零改动。
