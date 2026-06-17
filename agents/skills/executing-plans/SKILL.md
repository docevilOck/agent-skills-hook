---
name: executing-plans
description: 在当前会话里按已写好的实现计划顺序执行任务时使用
---

# 执行计划

读取计划，先做批判性检查，再按顺序执行所有任务，并在完成后进入默认收尾。执行时不只看计划本身，还要把计划引用的 architecture / detail / flow / dataflow 文档一并作为实现依据。

**开始时声明：** “我正在使用 executing-plans skill 来执行这个计划。”

## 何时使用

- 已经有明确的实现计划文档
- 现在要按计划直接落地，而不是继续做规划
- 任务之间有顺序依赖，适合同一会话连续推进
- 不需要为每个任务单独派发新的实现子代理

## 流程

### 第一步：读取并审查计划

1. 读取计划文件
2. 读取计划里引用的 architecture / detail / flow / dataflow 文档
3. 先批判性审查一遍，找出缺口、歧义、风险和无法执行的地方
4. 如果计划存在关键问题，先向用户指出，再继续
5. 如果计划可执行，就创建 TodoWrite / `update_plan` 跟踪并开始

### 计划审查重点

- 每个任务是否都明确引用了上游设计文档，而不是只给抽象目标
- 计划里的任务边界、文件范围和验证动作，是否都能追溯到已确认设计
- 计划是否偷偷引入了文档里没有的新设计、新接口或新流程分支
- 如果计划与引用文档冲突，是否已经回退到上游澄清，而不是强行执行

### 第二步：按任务执行

对每个任务都按这个顺序推进：

1. 标记任务为 `in_progress`
2. 先阅读该任务引用的文档和图，确认输入、输出、状态、接口与流程约束
3. 严格按计划步骤执行，不要擅自跳步，也不要脱离引用文档补设计
4. 运行该任务要求的验证
5. 做任务内一致性核对，确认实现结果与引用文档一致
6. 记录结果与未覆盖风险
7. 任务完成后再标记为 `completed`

如果计划里已经要求在步骤中提交、审查或补文档，就照计划执行，不要省略。

如果计划步骤与引用文档冲突，以已确认的 architecture / detail / flow / dataflow 文档为准，并立即回到计划审查，必要时先修计划再继续执行。

不要在任务刚做完时就提前宣称“计划完成”；默认要把最终完成结论留给收尾门禁。

### 第三步：阶段性复核

- 连续完成 2-3 个任务，或者完成一个明显的里程碑后，用 `superpowers:requesting-code-review` 做一次阶段性复核
- 如果审查指出阻塞问题，先修复再继续后续任务
- 如果只是非阻塞建议，记录后按优先级处理

### 第四步：默认收尾

当所有任务完成并通过计划要求的验证后，进入默认收尾顺序：

1. 用 `superpowers:verification-before-completion` 补齐最终结论所需的验证证据
2. 如需独立质量复核，用 `superpowers:requesting-code-review`
3. 进入 `superpowers:final-gate` 做第一轮一致性验收，并拉独立审查 agent 核对 architecture、detail、data flow、flow、exec plan 与代码是否完全一致
4. 如果第一轮 `final-gate` 返回 `blocked`，主 agent 必须先修改，再重新进入 `final-gate`
5. 如果第一轮 `final-gate` 返回 `need-info`，主 agent 必须先补齐缺失输入、范围或验证证据，再重新进入 `final-gate`
6. 只有当 `final-gate` 给出一致性 `pass` 后，才进入 `ai-slop-cleaner` 清理阶段
7. 清理阶段必须使用独立 subagent，并把范围限制在 final gate 已接受的代码范围或更窄的 changed-files；若为锁定行为必须补最小测试文件，只允许纳入最小必要测试范围
8. 清理 subagent 必须按 `ai-slop-cleaner` 的 regression-tests-first、最小 diff、最小作用域规则执行，不得借 cleanup 扩大为重构或改设计
9. 如果 cleanup 没有做出代码修改，可直接保留上一轮 final gate 的一致性 `pass`，进入最终收尾
10. 如果 cleanup 做出了任何代码修改，主 agent 必须补充 cleanup 后的新验证证据，并重新进入 `final-gate` 做完整一致性重审
11. 只有当 cleanup 后的最后一次 `final-gate` 也返回 `pass`，才能宣称“计划已经完成”

## 什么时候必须停下来

遇到下面情况要立刻停，先澄清再继续：

- 缺少依赖，导致关键步骤无法执行
- 计划中的步骤与代码现状明显不符
- 计划中的步骤与引用文档明显冲突
- 某一步说明不清，无法安全落地
- 计划要求的验证连续失败
- 发现计划本身需要改方向

不要硬猜，也不要在关键歧义下继续往前推。

## 重新回到计划审查的触发条件

以下情况要回到“读取并审查计划”这一步重新判断：

- 用户更新了计划
- 用户更新了 architecture / detail / flow / dataflow 文档
- 你发现计划中的关键假设已经失效
- 实现中暴露出上游设计缺口

## 红旗信号

**永远不要：**

- 不看计划就直接开写
- 不看任务引用的上游文档就直接开写
- 计划有明显缺口还硬执行
- 跳过验证
- 把“代码写了”当成“任务完成”
- 计划和上游文档冲突时，私自选择其中一个继续写
- 没经过默认收尾就宣称整体完成
- 在 `final-gate` 一致性 `pass` 之前提前进入 cleanup
- cleanup 改了代码却不重新回到 `final-gate`
- 未经用户明确同意就在 `main` / `master` 上开始实现

## 集成

**Required workflow skills:**
- **superpowers:using-git-worktrees** - 在执行计划前准备隔离工作区
- **superpowers:writing-plans** - 产出本 skill 要执行的计划
- **superpowers:requesting-code-review** - 阶段性复核与重要节点复核
- **superpowers:verification-before-completion** - 对最终结论补齐验证证据
- **superpowers:final-gate** - 默认最终验收
- **superpowers:ai-slop-cleaner** - 一致性通过后的受限 cleanup / deslop 阶段
