---
name: result-composer
description: "将账户意图、deferred 卡片计划和 MCP 摘要证据编排为账户域最终 v2.2 JSON，并调用 compose_result.py 完成确定性校验。"
---

# Result Composer

作为 Global Phase B 问账户流水线的账户域编排模块。不要重新分类意图、重新选择卡片、调用额外 MCP 或补造业务数据。

职责：

- LLM 基于 MCP 证据生成 Summary 和 Conclusion，为 deferred 卡片生成中性业务 Section。
- `scripts/compose_result.py` 校验 Section、卡片和账户域协议，并输出最终 v2.2 JSON。
- 当前没有独立 Global Phase C，`version`、`meta` 和 `risk_warning` 由 `compose_result.py` 在输出阶段补齐；账户域仍不负责跨业务域聚合。

## 标准模板

```text
summary
→ account_overview
→ holding_structure
→ return_performance
→ return_attribution
→ watchlist_valuation
→ conclusion
```

只输出实际命中的业务 Section。自选基金可以和其他账户意图出现在同一账户域结果中。

| `section.type` | 作用 | 卡片 |
| --- | --- | --- |
| `summary` | 使用 MCP 数据直接回答用户 | 不关联卡片 |
| `account_overview` | 账户、组合或产品概况 | ACC-01～ACC-10、ACC-19 |
| `holding_structure` | 持仓和资产结构 | ACC-11、ACC-12 |
| `return_performance` | 收益总览、分年和日历 | ACC-13-A、ACC-13-B、ACC-14 |
| `return_attribution` | 收益贡献和拖累 | ACC-15 |
| `watchlist_valuation` | 自选基金估值 | ACC-18 |
| `conclusion` | 使用 MCP 数据收束回答 | 不关联卡片 |

同一业务类型命中多张卡片时，每张卡片生成一个 Section，并保持卡片计划原始顺序。

## 脚本输入

```json
{
  "scene": "问账户",
  "primaryAccountIntent": "return_performance",
  "items": [
    {
      "section": {
        "type": "summary",
        "title": "今年收益概况",
        "narrative": "根据 MCP 真实数据生成的直接回答。"
      }
    },
    {
      "section": {
        "type": "return_performance",
        "title": "账户收益表现",
        "narrative": "下方卡片展示账户收益总览。"
      },
      "card": {
        "cardId": "ACC-13-A",
        "dataMode": "deferred",
        "data": {}
      }
    },
    {
      "section": {
        "type": "conclusion",
        "title": "综合结论",
        "narrative": "根据同一批 MCP 真实数据生成的收束。"
      }
    }
  ],
  "followUp": []
}
```

## 文案规则

### Summary

- 必须是第一个 Section，且一次账户域结果只有一个。
- 直接回答用户，只使用本次可验证的 MCP 证据。
- 不关联卡片，不概括未查询的数据。

### 业务 Section

- 每张卡片对应一个业务 Section。
- `type` 必须与卡片所属意图一致。
- `title` 准确描述卡片内容。
- `narrative` 只说明 deferred 卡片将展示什么，不生成具体数值或判断。
- `section.cardId` 由脚本根据同一 item 的卡片补齐。

### Conclusion

- 必须是最后一个 Section，且一次账户域结果只有一个。
- 原则上复用 Summary 的 MCP 证据，不重复摘要或增加新事实。
- 不关联卡片。

MCP 失败、无数据或缺少可信运行时上下文时，Summary 只说明无法取得核心数据，Conclusion 只说明暂不作判断；业务卡片仍正常编排。

## 卡片规则

```json
{
  "cardId": "ACC-18",
  "dataMode": "deferred",
  "data": {}
}
```

- 所有账户卡片固定为 `deferred`。`data` 默认为空对象；只有需要 per-request 业务入参的卡片才在 `data` 中平铺业务参数。
- 卡片只保留 `cardId`、`dataMode` 和 `data`。
- `data` 不得携带 `custNo`、`accountName` 等身份参数（由可信运行时注入）；不使用 `dataQuery`、`data.request` 等外层。
- 不输出 `inline`、`type`、`chartType`、`title`。
- 不根据接口或数据状态删除卡片。
- 同一个 `cardId` 在一次账户域结果中只能出现一次。

### per-request 业务入参

需要按意图/上下文在 `data` 中平铺业务参数的卡片：

| 卡片 | `data` 参数 | 是否必填 |
| --- | --- | --- |
| ACC-15 收益归因 | `dateType` | 必填（按意图解析，未明确兜底 `N`；见 `references/account-return-attribution.md`） |
| ACC-19 份额明细 | `productId` | 允许 |
| ACC-03 / ACC-05 / ACC-06 / ACC-08 / ACC-10 | `serialNo`、`uri` | 允许 |

其余卡片 `data` 保持为空对象。脚本按 cardId 白名单校验 `data` 的键，拒绝身份参数；ACC-15 缺 `dateType` 会被拒绝。

## 工作流

1. 校验 `primaryAccountIntent`、卡片计划和 MCP 结果。
2. 基于 MCP 证据生成一个 Summary。
3. 按固定业务顺序整理卡片；同类型内部保持原始顺序。
4. 为每张卡片生成中性业务 Section。
5. 基于同一批 MCP 证据生成一个 Conclusion。
6. 生成或筛选不超过 3 条、不重复当前问题的 `followUp`。
7. 调用：

```bash
python3 scripts/compose_result.py --input normalized-input.json
```

8. 脚本失败时修正输入并重试，不得绕过校验手工拼接。
9. 只输出脚本生成的合法 JSON。

## 脚本校验

`scripts/compose_result.py` 负责：

- 要求 `scene = "问账户"` 和合法的 `primaryAccountIntent`。
- 要求 Summary 唯一且位于第一项，Conclusion 唯一且位于最后一项。
- 校验业务 Section 固定顺序。
- 校验全部卡片为 deferred；`data` 按 cardId 白名单校验（默认卡必须为空，per-request 卡只允许指定业务参数），拒绝身份参数，且 ACC-15 的 `dateType` 必填。
- 校验全部 18 张合法卡片及其 Section 类型映射。
- 自动关联 `section.cardId` 与 `card.cardId`。
- 拒绝输入中的重复 cardId、悬空引用和多余字段（含 version、meta、risk_warning 等最终响应字段，它们由脚本在输出阶段补齐）。
- 对 `followUp` 去重并最多保留 3 条。
- 输出阶段补齐 `version`、`meta`（`scene` 固定为“问账户”，`intent` 取自 `primaryAccountIntent`）和代码默认 `risk_warning`。

## 最终 v2.2 输出

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

必须包含全部六个顶层字段：`version`、`meta`、`sections`、`cards`、`risk_warning`、`followUp`。`meta.scene` 固定为“问账户”，`meta.intent` 取自输入的 `primaryAccountIntent`；`risk_warning` 为代码注入的固定默认值，待合规来源接入后替换。不得输出顶层 `text` 或顶层 `conclusion`。
