---
name: account-return-attribution
description: "将 return_attribution 账户意图映射为 ACC-15 收益归因 deferred 卡片，覆盖产品、类型和行业维度的收益贡献与拖累诉求。"
---

# Account Return Attribution

作为账户域 Account Step 2（卡片选择与计划归一化），只处理 `intent = "return_attribution"` 的单条路由记录。卡片清单只允许 ACC-15，不生成 ACC-16 或 ACC-17。

## 输入

```json
{
  "intent": "return_attribution",
  "subQuery": "我的钱为什么亏了",
  "entities": {}
}
```

## 卡片

| `cardId` | `type` | 标题 | 触发范围 |
| --- | --- | --- | --- |
| ACC-15 | `acc15-return-attribution` | 收益归因 | 查看产品、类型或行业维度的收益贡献与拖累 |

## 规则

1. 询问账户为什么赚亏、主要贡献或拖累时输出 ACC-15。
2. 产品、类型或行业维度的收益归因都输出 ACC-15。
3. 其他收益归因诉求仍输出 ACC-15，不因 MCP 或接口能力改变卡片；Summary 和 Conclusion 能否形成具体判断由 MCP 结果决定。
4. 卡片固定输出 `dataMode: "deferred"`；`data` 必须携带 `dateType`（按用户意图解析，未明确时兜底 `N`，详见下文「dateType 解析」）；不得生成具体贡献或拖累数据。
5. 不得虚构 ACC-16 或 ACC-17。
6. 只输出合法 JSON，不添加解释文字。

## dateType 解析

ACC-15 的 `data.dateType` 由 LLM 按用户意图解析后写入（与 ACC-13-A/13-B/14 共用同一套取值）。

取值表：

| 代码 | 含义 |
| --- | --- |
| `N` | 今日 |
| `L` | 昨日 |
| `M0` | 本月 |
| `M1` / `M3` / `M6` | 近一月 / 近三月 / 近六月 |
| `Y0` | 本年 |
| `Y1` / `Y3` / `Y5` | 近一年 / 近三年 / 近五年 |
| `Y20XX` | 指定自然年（如 `Y2024`、`Y2025`） |
| `T` | 至今（成立以来） |

用户表达 → `dateType`：

| 用户表达 | `dateType` |
| --- | --- |
| 今日、今天 | `N` |
| 昨日、昨天 | `L` |
| 本月、这个月 | `M0` |
| 近一月 / 近三月 / 近六月 | `M1` / `M3` / `M6` |
| 今年、本年、今年以来 | `Y0` |
| 近一年 / 近三年 / 近五年 | `Y1` / `Y3` / `Y5` |
| 去年、上一年；或指定年份（如“2024 年”） | `Y20XX`（按当前年份推导） |
| 成立以来、全部、至今 | `T` |

- 优先按用户**明确表达**匹配；表达有歧义时取最接近的区间，不得编造用户未给出的区间。
- 用户**未明确时间范围**时，`dateType` 兜底取 `N`（今日）。
- 只写入 `data.dateType`；不得写入 `custNo`、`accountName` 等身份参数。

## 输出

```json
{
  "intent": "return_attribution",
  "subQuery": "哪些产品拖累了收益",
  "cards": [
    {
      "cardId": "ACC-15",
      "dataMode": "deferred",
      "data": { "dateType": "N" }
    }
  ]
}
```
