# Simple Summary

## 适用条件

只在 `taskComplexity = simple` 时使用。完整读取 `references/mcp-evidence.md`。

简单任务回答明确、有限的账户事实问题，不形成账户级诊断，不生成 Conclusion。

## 工作流

```text
读取 originalQuery、accountScenes 和卡片计划
→ 明确各子问题的直接答案
→ 选择最少必要 MCP
→ 校验真实数据
→ 生成一个 Summary
```

多张卡片仍可以是简单任务。各子问题可以独立回答时，只在同一个 Summary 中合并事实，不解释跨维度关系。

## Summary

```text
查询范围
+ 1～3 个关键事实
+ 对用户问题的直接回答
```

规则：

- 直接回答，不写“下面为您展示”等套话；
- 说明关键事实与用户当前问题的关系，不退化为字段播报；
- 表达清楚、克制、有依据，不因单一指标制造焦虑；
- 金额、比例、收益、持仓和归因必须来自本次 MCP；
- 不概括未调用 MCP 的卡片内容；
- 不扩展为“账户健康”“配置合理”“风险可控”等账户级判断；
- 后续方向可以写入 `followUp`，但必须是可选方向，不替用户作决定，也不增加 Conclusion。

## 输出

只输出：

```json
{
  "summary": {
    "title": "回答摘要",
    "narrative": "基于真实 MCP 数据的直接回答。"
  },
  "followUp": []
}
```

禁止输出 `conclusion`、Section 类型、业务 Section、卡片、顶层 v2.2 字段或 MCP 原始数据。

## 数据不可用

Summary 说明当前无法取得回答所需的数据，不补造判断。已选 deferred 卡片继续由代码输出。
