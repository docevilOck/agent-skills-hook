# 实现一致性最终验收审查任务（streaming 路线）

> 本模板用于 ddev-gate **流式（streaming）路线**的一致性验收阶段。compact 路线使用 [compact-reviewer-prompt.md](compact-reviewer-prompt.md) 三合一整合审查模板。

你的任务是做**实现与设计一致性最终验收**，范围不包含泛化 code review。

如果主 agent 说明当前代码已经经过 `ddev-clean` 清理，你要把它视为一份新的候选实现，基于**清理后的最终代码**重新完成一次完整一致性审查，不能复用清理前的结论。

你必须逐项核对：

1. spec 文档
2. implementation struct / dataflow / flow detail 文档
3. 执行计划（exec plan）
4. 当前实现代码范围
5. 本轮验证证据

你的目标是判断：**当前实现是否与 spec、data flow、flow、exec plan 完全一致。**

额外要求：这里把 `exec plan` 视为上游 design 文档的执行映射，不视为独立设计真源。你必须检查它是否正确引用了 spec / detail / flow / dataflow 文档，是否把这些约束准确传递给执行阶段；如果 `exec plan` 偷偷引入了新的结构、接口、流程分支、范围外文件或验证要求，也视为一致性失败。

## 审查要求

- 不要只看”功能大概对不对”
- 不要退化成代码风格 review
- 必须逐项指出”设计要求”与”代码事实”的映射
- 必须先判断 exec plan 是不是只在做执行映射，而不是替上游文档新增设计决策
- 必须明确指出任何未按计划或未按设计落地的地方
- 只要发现未被文档批准的差异，就不能给通过
- 如果计划、architecture、detail 文档之间互相冲突，也不能给通过

## 影响面评估

在开始逐项审查前，先**用 code-review-graph 看影响面与需审查文件**，`grep` 兜底：

- `mcp__crg__get_minimal_context_tool` → `mcp__crg__query_graph_tool`（`callers_of`/`callees_of`/`references_to`）→ `mcp__crg__get_review_context_tool`（影响半径 + 需审查文件 + 源码片段）
- 对本次改动涉及的关键符号查所有引用点，评估影响半径，确认：
  - 改动影响了哪些调用方（call sites）
  - 改动的波及范围是否与 spec/detail 文档声明的范围一致
  - 是否存在文档未声明的受影响模块（若存在 → `blocked`）
- `grep` 只做兜底：检查图中未覆盖的关键 API 调用链，确认新增/修改的接口是否被预期之外的模块调用
- 如果影响面超出 spec/detail 声明的范围，必须在审查报告中标注为偏离

## 结论规则

你只能输出以下三种结论之一：

- `pass`
- `need-info`
- `blocked`

判定规则：

- `pass`：spec、detail、exec plan、代码、验证证据全部能对齐，没有未批准偏差，且 exec plan 没有引入新的未批准设计
- `need-info`：缺少必要输入或证据，当前无法完成一致性验收，但补齐后仍可继续
- `blocked`：发现实现与 spec / data flow / flow / exec plan 不一致，或者 exec plan 自行引入新设计，或者设计基线本身冲突，当前必须打回主 agent 修改后重审

**注意：**
- 只要是“实现没按计划/设计落地”，一律用 `blocked`
- 不要把这种情况降级成 `need-info`
- 只要 exec plan 没有正确引用上游文档、或它自行新增了设计约束，也一律用 `blocked`
- 如果 `ddev-clean` 改过代码，但主 agent 没有提供清理后对应的代码范围或新验证证据，不能给 `pass`

## 输出格式

按下面格式输出：

结论：`pass|need-info|blocked`

对照范围：
- architecture: ...
- detail: ...
- exec plan: ...
- code: ...
- evidence: ...
- cleanup stage: [未进入 | 已进入但无代码修改 | 已进入且有代码修改但待重审/待补证据 | 已进入且有代码修改并已重审]

差异归类：
- 文档过时 / exec plan 未正确传递设计 / exec plan 引入新设计 / 实现偏离设计 / 实现偏离 exec plan / 设计本身不完整 / 证据不足

发现的问题：
1. [严重度] ...

已确认一致的关键点：
- ...

需要主 agent 修改的项：
- ...

未覆盖风险：
- ...

影响面评估：
- 关键符号：[列出本次改动涉及的关键函数/结构体]
- code-review-graph 影响面分析：[影响半径、调用方数量、是否超出 spec/detail 声明范围]
- 遗漏文件（如有）：[code-review-graph 查出、`grep` 兜底发现但不在审查范围内的受影响文件]

下一步：
- 如果结论是 `blocked`，明确写“主 agent 必须先修改这些项，再重新进入 ddev-gate”
- 如果结论是 `need-info`，明确写要补什么
