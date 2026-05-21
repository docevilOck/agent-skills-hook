---
name: implementation-final-gate
description: 在代码实现完成后、准备结束任务或进入发布前使用，用来核对代码实现是否与实现架构文档以及 detail 文档一致，并给出最终验收结论
---

# 实现最终验收门禁

## 作用

这个 skill 用于代码实现阶段的最终验收。

它不是普通代码审查，也不是只跑测试的验证门禁。它的核心任务是**拉一个独立审查 agent**，把**代码实现**与以下设计输入做逐项对照：

- `implementation-architecture-workflow` 产出的实现架构文档
- `implementation-struct-dataflow-workflow` 产出的 detail 文档
- 必要时补充执行计划、验证结果和相关图文档

目标不是“看起来差不多”，而是明确回答：

- 实现是否忠实落地了架构设计
- 实现是否偏离了结构体、数据流、流程设计
- 偏离是否合理、是否被显式更新到文档
- 这次改动是否可以给出最终验收结论

如果审查 agent 发现任何未被批准的差异，就必须审核不通过，打回主 agent 修改。主 agent 修改后，必须重新进入这个 skill，再拉审查 agent 重审。这个循环要一直持续到审查 agent 给出 `pass`，主 agent 才能宣称“计划已经完成”。

## 何时使用

在以下场景使用：

- 一个实现任务完成后，需要做正式验收
- 准备声称“已经完成实现”或“已经满足设计”
- 准备把改动交给下游联调、测试、提交或发布
- 需要确认代码实现没有背离 architecture/detail 文档

如果只是想先检查有没有跑验证命令，优先用 `verification-before-completion`。

如果只是想让另一个视角找 bug，优先用 `requesting-code-review`。

如果目标是**实现与设计一致性验收**，用这个 skill。

如果主 agent 正准备宣称“已经完成计划”“已经按计划实现完成”“可以正式收尾”，这个 skill 是必经门禁。

## 输入要求

开始验收前，至少定位这些输入：

- 本次改动对应的架构文档路径
- 本次改动对应的 detail 文档路径
- 相关代码变更范围

能拿到的话，额外读取：

- 结构图 / 流程图 / 数据流图
- `writing-plans` 产出的执行计划
- 构建、测试、静态检查或人工验证结果

如果连 architecture 或 detail 文档都没有，不能直接给通过结论。

如果无法唯一定位 architecture 文档、detail 文档或本次改动范围，不要退化成泛化 code review。此时应立即停止一致性验收，并输出：

- `need-info`：信息暂时不足，但理论上可补齐
- `blocked`：当前上下文下无法继续定位或缺失关键设计输入

## 范围确定规则

验收范围必须先定清楚，再开始对照。

优先级如下：

1. 用户明确指定的文件范围或提交范围
2. `writing-plans` 中列出的文件清单
3. 当前任务对应的 git diff / 工作区 diff
4. architecture/detail 文档中明确点名的实现文件

如果范围仍然不清楚，先输出 `need-info`，不要自己扩散成全仓库审查。

## 核心流程

1. 主 agent 先定位 architecture 文档、detail 文档、exec plan、代码范围和本轮验证证据。
2. 主 agent 读取这些输入，整理成明确的审查上下文。
3. 主 agent 使用独立审查 agent 执行最终一致性验收。
4. 审查 agent 必须按“architecture -> detail -> exec plan -> code -> evidence”的顺序逐项对照。
5. 审查 agent 检查实现里是否出现文档或计划未批准的偏离。
6. 审查 agent 检查文档强调的约束是否真的落到了代码里，而不是只写在文档里。
7. 审查 agent 输出 `pass`、`need-info` 或 `blocked`。
8. 如果结论是 `blocked`，主 agent 必须先修改代码或补齐文档，再重新进入这个 skill，重新拉审查 agent 验收。
9. 只有当审查 agent 输出 `pass` 时，主 agent 才能宣称“已经按计划完成”。

如果没有新的、可归属到本轮结论的验证证据，最多输出 `need-info`，不能输出 `pass`。

## 审查 agent 要求

- 必须是独立视角，不能把主 agent 自己的口头总结当结论
- 必须显式核对 architecture、detail、exec plan、code、evidence 这五类输入
- 必须把 data flow、flow、结构体设计与代码逐项对上
- 发现任何未批准差异时，必须返回 `blocked`
- 不允许用“基本一致”“差不多符合”“核心没问题”这类模糊表述放行

审查提示模板见 [final-gate-reviewer-prompt.md](final-gate-reviewer-prompt.md)。

## 重点检查项

默认重点检查：

- 模块边界是否与架构文档一致
- 接口位置、调用方向、接入点是否与架构设计一致
- 结构体是否与 detail 文档定义一致
- 数据流、状态流、错误流是否与 detail 文档一致
- 关键分支是否按设计落地，而不是实现时擅自改成别的结构
- 是否新增了文档未说明的共享可变状态
- 是否出现文档未允许的业务全局变量
- 是否把本应拆分的职责重新塞回大函数
- 是否出现未在设计中说明的长链 `if/else`

对于嵌入式 C / 纯 C，额外重点检查：

- 运行时状态是否确实收敛到 `context` / session / handle 结构体
- 状态值是否使用 `enum` 或等价显式语义，而不是魔法数字
- 分发方式是否符合设计时选定的守卫式返回、`switch`、表驱动或状态机
- `static` 私有函数边界是否与文档设计一致
- 错误码、异常出口和资源清理路径是否与设计一致

详细检查清单见 [acceptance-checklist.md](references/acceptance-checklist.md)。

标准输出样例见 [example-acceptance-output.md](examples/example-acceptance-output.md)。

## 结论规则

只允许输出这三种最终结论：

- `pass`
- `need-info`
- `blocked`

### `pass`

只有在以下条件同时满足时才能给：

- 已找到并核对 architecture 文档
- 已找到并核对 detail 文档
- 已明确本轮验收对应的代码范围
- 代码实现与设计一致，或偏离已被明确接受并补充到文档
- 代码实现与 exec plan 一致，关键步骤没有漏做、错做或擅自改做
- 本轮存在新的验证证据，且证据与结论匹配
- 未覆盖风险已明确说明

### `need-info`

用于信息不足但还不构成硬阻塞的情况，例如：

- 缺少部分 detail 文档
- 缺少关键验证结果
- 没有新的验证证据，无法支撑 `pass`
- 改动范围无法唯一确定
- 某些实现意图在代码里存在，但文档没有明确写
- 设计与实现差异无法判断是故意还是遗漏

判定原则：

- 还能通过补文档、补范围、补验证证据继续推进的，用 `need-info`
- 当前虽然不能给 `pass`，但继续核对仍然有意义的，用 `need-info`

### `blocked`

用于无法验收或明显不通过的情况，例如：

- 找不到 architecture 文档或 detail 文档
- 无法定位本轮改动对应的实现范围
- 实现明显背离设计，且没有文档更新
- 实现明显背离 exec plan
- 实现与 data flow / flow / 结构体设计不一致
- 关键设计约束未落地
- 结论依赖关键证据，但证据不存在

判定原则：

- 关键设计基线缺失、互相冲突或当前上下文下无法建立时，用 `blocked`
- 在补齐前提之前继续审查没有意义的，用 `blocked`
- 只要需要打回主 agent 改代码或改文档后再审，也用 `blocked`

## 输出格式

最终输出必须包含：

1. 验收结论：`pass` / `need-info` / `blocked`
2. 对照范围：看了哪些 architecture / detail / code / 验证材料
3. 差异归类：文档过时 / 实现偏离设计 / 设计本身不完整 / 证据不足
4. 发现的问题：按严重度列出与设计不一致之处
5. 已确认一致的关键点：只列最重要的几项
6. 未覆盖风险：明确还没验证到哪里

如果没有发现不一致，也不能只说“通过”，仍要说明对照了什么。

如果需求结论依赖真实目标板、外设、时序、功耗、波形或现场观察，而本轮没有对应人工或现场证据，不能给 `pass`。

如果审查结论是 `blocked`，输出里必须明确列出“需要主 agent 修改的项”，这样主 agent 才能按项修复并重新送审。

## 与其他 skill 的关系

- 上游通常来自 `implementation-architecture-workflow`
- detail 输入通常来自 `implementation-struct-dataflow-workflow`
- 如需补验证证据，联动 `verification-before-completion`
- 如需独立质量复核，联动 `requesting-code-review`
- 默认在 `executing-plans` 的末尾作为最终收口门禁

## 最低要求

没有 architecture 文档、没有 detail 文档、没有代码对照，就不要假装做了最终验收。

验收的重点是**实现是否符合 architecture、detail 和 exec plan**，不是只看“代码能不能跑”。
