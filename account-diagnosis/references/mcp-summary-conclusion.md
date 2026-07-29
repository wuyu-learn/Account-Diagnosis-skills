---
name: mcp-summary-conclusion
description: "为问账户回复规划最少必要的 MCP 调用，并只基于真实 MCP 数据生成 Summary 和 Conclusion。卡片计划已经完成，需要准备摘要与结论时使用。"
---

# MCP Summary and Conclusion

作为账户域摘要数据规划模块。卡片计划和 MCP 计划相互独立：卡片决定前端展示组件，MCP 只为 Summary 和 Conclusion 提供真实数据。

## 可用工具

| 工具 | 能力 |
| --- | --- |
| `queryAssetsTotal` | 查询客户总资产 |
| `queryAssetIndex` | 查询今日表现（账户管家） |
| `queryAssetClassify` | 查询基金类型、大类资产、市场区域和行业风格分布 |
| `queryHoldingDetail` | 查询按资产分类汇总或按基金穿透的持仓明细 |
| `queryHoldingSignal` | 查询今日持仓提醒 |
| `queryShareDetail` | 查询份额明细 |
| `queryProfitAnalyze` | 查询区间收益、收益走势和比较分析 |
| `queryProfitAnalyzeSum` | 查询收益总览 |
| `queryProfitAttribution` | 查询产品、类型或行业收益归因 |
| `queryProfitCalendar` | 查询日、月或年收益日历 |

工具参数、返回 Schema、鉴权和错误结构以运行时 MCP 定义为准。不得根据本文件猜测参数或字段。

## MCP 计划

```text
识别用户希望直接得到的答案
→ 确定 Summary 和 Conclusion 的最小数据需求
→ 选择必要 MCP
→ 按运行时 Schema 构造参数
→ 校验用户、账户、时间和统计口径
→ 调用并保存真实结果
```

禁止根据卡片清单逐张调用 MCP。选中卡片不代表必须调用业务相近的工具。

选择参考：

| Summary 或 Conclusion 需要的数据 | MCP |
| --- | --- |
| 总资产和账户构成 | `queryAssetsTotal` |
| 今日账户表现 | `queryAssetIndex` |
| 资产分布和集中度 | `queryAssetClassify` |
| 持仓数量、构成和穿透 | `queryHoldingDetail` |
| 今日持仓提醒 | `queryHoldingSignal` |
| 指定产品份额 | `queryShareDetail` |
| 区间收益、走势和比较 | `queryProfitAnalyze` |
| 收益总览 | `queryProfitAnalyzeSum` |
| 产品、类型或行业归因 | `queryProfitAttribution` |
| 日、月或年收益明细 | `queryProfitCalendar` |

## Summary

```text
summary = 查询范围 + 1～3 个关键 MCP 事实 + 直接回答
```

- 用 1～3 句话回答用户最关心的结果。
- 金额、收益率、持仓、行情、归因和诊断判断必须来自本次 MCP 响应。
- 复合问题只生成一个 Summary，可以综合多个 MCP 的已确认结果。
- 不写“下面为您展示”等空泛引导语。
- 不概括未调用 MCP 的卡片内容。

## Conclusion

```text
conclusion = 整体判断 + 主要关注点 + 后续方向
```

- 用 1～2 句话收束回答。
- 原则上复用 Summary 已调用的同一批 MCP，不因存在 deferred 卡片增加工具调用。
- 只有用户明确要求进一步诊断且现有证据不足时，才增加必要 MCP。
- 不重复 Summary，不引入 MCP 未返回的新事实。
- 不把局部结果扩展为完整账户判断。

## 内部证据

内部保存 MCP 计划和结果，不写入账户域局部 JSON：

```json
{
  "mcpPlan": [
    {
      "tool": "queryProfitAnalyzeSum",
      "purpose": "回答今年收益情况",
      "scope": {
        "account": "来自可信请求上下文",
        "period": "今年"
      }
    }
  ],
  "mcpResults": [
    {
      "tool": "queryProfitAnalyzeSum",
      "status": "available",
      "scope": {},
      "data": {}
    }
  ]
}
```

不得把 MCP 返回值写入 deferred 卡片的 `data`。

身份和鉴权只能来自可信运行时或 MCP 连接。缺少工具所需的可信上下文时不得猜测参数，直接按数据降级处理。任何对外输出都不得包含 `custNo`、`accountName`、`sessionId`、鉴权信息或 MCP 原始请求。

## 失败与降级

- MCP 失败、无数据或结果无法校验时，不生成业务数据判断。
- Summary 只说明当前无法取得核心回答所需的数据。
- Conclusion 只说明暂不作判断，并给出可重试或继续查看的方向。
- 单个 MCP 失败不删除或阻止任何已选 deferred 卡片。
