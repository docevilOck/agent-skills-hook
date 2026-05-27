---
name: implementation-final-gate
description: 在代码实现完成后、准备结束任务或进入发布前使用，用来核对代码实现是否与实现架构文档以及 detail 文档一致，并给出最终验收结论
---

# 实现最终验收门禁

## 作用

这个 skill 用于代码实现阶段的最终验收。

它不是普通代码审查，也不是只跑测试的验证门禁。它的核心任务分成两段：

1. **先拉独立审查 agent**，把**代码实现**与以下设计输入做逐项对照
2. **一致性通过后，再拉独立 subagent 调用 `ai-slop-cleaner`**，在受限范围内做垃圾代码清理和可维护性提升；若清理改了代码，再重新回到一致性验收

第一段一致性验收要对照的设计输入包括：

- `implementation-architecture-workflow` 产出的实现架构文档
- `implementation-struct-dataflow-workflow` 产出的 detail 文档
- 必要时补充执行计划、验证结果和相关图文档

目标是明确回答：

- 实现是否忠实落地了架构设计
- 实现是否偏离了结构体、数据流、流程设计
- 执行计划是否正确引用、传递并落实了这些设计约束，而不是在计划阶段偷偷发明新设计
- 偏离是否合理、是否被显式更新到文档
- 这次改动是否可以给出最终验收结论

这里的设计一致性判断遵循同一条文档规则：architecture、detail、exec plan 只定义“这次要做什么”。凡是文档里没有明确写到的实现、结构、流程、共享状态、旁路逻辑或验证动作，都按未获批准处理，而不是等待文档再额外写一段“明确不做”。

如果审查 agent 发现任何未被批准的差异，就必须审核不通过，打回主 agent 修改。主 agent 修改后，必须重新进入这个 skill，再拉审查 agent 重审。这个循环要一直持续到审查 agent 给出一致性 `pass`。

但一致性 `pass` 还不是最终放行：主 agent 还必须再拉一个独立 subagent，受限调用 `ai-slop-cleaner` 做清理。如果清理阶段产生任何代码修改，就必须重新进入这个 skill，再次拉独立审查 agent 做一致性重审。只有在**清理后的最终代码**也通过一致性验收后，主 agent 才能宣称“计划已经完成”。

## 何时使用

在以下场景使用：

- 一个实现任务完成后，需要做正式验收
- 准备声称“已经完成实现”或“已经满足设计”
- 准备把改动交给下游联调、测试、提交或发布
- 需要确认代码实现没有背离 architecture/detail 文档

如果只是想先检查有没有跑验证命令，优先用 `verification-before-completion`。

如果只是想让另一个视角找 bug，优先用 `requesting-code-review`。

如果目标是**实现与设计一致性验收**，并在通过后继续做一轮受限 deslop / maintainability cleanup，再复核一致性，用这个 skill。

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

如果拿到了 exec plan，还要检查它是否明确引用了 architecture / detail / flow / dataflow 文档，是否把这些文档里的约束正确传递给执行阶段；不能把 exec plan 当成脱离设计文档独立成立的真源。

## 范围确定规则

验收范围必须先定清楚，再开始对照。

优先级如下：

1. 用户明确指定的文件范围或提交范围
2. `writing-plans` 中列出的文件清单
3. 当前任务对应的 git diff / 工作区 diff
4. architecture/detail 文档中明确点名的实现文件

如果 exec plan 中列出的文件范围明显超出 architecture / detail / flow / dataflow 文档允许的边界，也要按范围异常处理，不能默认放行。

后续 `ai-slop-cleaner` 的作用范围默认也必须继承这份范围；如果能拿到更窄的 changed-files 列表，优先把清理范围进一步收敛到 changed files。

如果为了满足 `ai-slop-cleaner` 的 regression-tests-first 规则，必须补最小测试覆盖，则允许把**锁定既有行为所必需的最小测试文件**纳入 cleanup 附属范围；这些测试文件也必须计入 cleanup 范围说明和后续验证证据。

如果范围仍然不清楚，先输出 `need-info`，不要自己扩散成全仓库审查。

## 核心流程

1. 主 agent 先定位 architecture 文档、detail 文档、exec plan、代码范围和本轮验证证据。
2. 主 agent 读取这些输入，整理成明确的审查上下文。
3. 主 agent 使用独立审查 agent 执行第一轮最终一致性验收。
4. 审查 agent 必须按“architecture -> detail -> exec plan -> code -> evidence”的顺序逐项对照。
5. 审查 agent 先检查 exec plan 是否正确引用 architecture / detail / flow / dataflow 文档，是否把这些约束传递成了可执行任务，而不是新增了文档中不存在的设计。
6. 审查 agent 检查实现里是否出现文档或计划未批准的偏离。
7. 审查 agent 检查文档强调的约束是否真的落到了代码里，而不是只写在文档里。
8. 审查 agent 输出 `pass`、`need-info` 或 `blocked`。
9. 如果结论是 `blocked`，主 agent 必须先修改代码或补齐文档，再重新进入这个 skill，重新拉审查 agent 验收。
10. 如果结论是 `need-info`，主 agent 必须先补齐缺失输入、范围或验证证据，不得进入 cleanup；补齐后重新进入这个 skill。
11. 只有当第一轮一致性结论为 `pass` 时，主 agent 才能进入清理阶段。
12. 主 agent 拉一个新的独立 subagent，在当前代码范围或更窄 changed-files 范围内调用 `ai-slop-cleaner`。
13. 清理 subagent 必须遵守 `ai-slop-cleaner` 的 regression-tests-first、显式 cleanup plan、分 smell 分 pass、最小 diff、最小作用域规则。
14. 如果清理 subagent 没有做出任何代码修改，主 agent 可直接保留第一轮一致性结论，进入最终收尾。
15. 如果清理 subagent 做出了代码修改，主 agent 必须补充这些修改对应的验证证据，并重新拉独立审查 agent，再做一次完整一致性验收。
16. 只有当**最后一次一致性验收**输出 `pass` 时，主 agent 才能宣称“已经按计划完成”。

如果没有新的、可归属到本轮结论的验证证据，最多输出 `need-info`，不能输出 `pass`。

如果清理 subagent 产出的改动超出既定范围、引入新的抽象层、或让实现偏离 architecture/detail/exec plan，也必须回到 `blocked`，不能因为“一致性阶段之前通过过”而继续放行。

## 审查 agent 要求

- 必须是独立视角，不能把主 agent 自己的口头总结当结论
- 必须显式核对 architecture、detail、exec plan、code、evidence 这五类输入
- 必须显式核对 exec plan 是否只是执行映射，还是偷偷承担了新的设计决策
- 必须把 data flow、flow、结构体设计与代码逐项对上
- 发现任何未批准差异时，必须返回 `blocked`
- 不允许用“基本一致”“差不多符合”“核心没问题”这类模糊表述放行
- 如果本轮代码已经过 `ai-slop-cleaner` 清理，必须按**清理后的最终代码**重做对照，不能沿用清理前结论

审查提示模板见 [final-gate-reviewer-prompt.md](final-gate-reviewer-prompt.md)。

## 重点检查项

默认重点检查：

- 模块边界是否与架构文档一致
- 接口位置、调用方向、接入点是否与架构设计一致
- 结构体是否与 detail 文档定义一致
- 数据流、状态流、错误流是否与 detail 文档一致
- exec plan 是否正确引用了 architecture / detail / flow / dataflow 文档，而不是脱离这些文档自定义约束
- exec plan 中的任务、文件范围和验证动作，是否都能追溯到已确认设计
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
- 若存在 exec plan，则已确认它正确引用并传递了上游设计约束，没有在计划阶段引入新的未批准设计
- 代码实现与设计一致，或偏离已被明确接受并补充到文档
- 代码实现与 exec plan 一致，关键步骤没有漏做、错做或擅自改做
- 本轮存在新的验证证据，且证据与结论匹配
- 未覆盖风险已明确说明
- 若经历过 `ai-slop-cleaner` 清理，则清理后的最终代码也已重新完成一致性验收

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
- exec plan 与 architecture / detail / flow / dataflow 文档冲突，或 exec plan 自行引入了新的未批准设计
- 实现明显背离设计，且没有文档更新
- 实现明显背离 exec plan
- 实现与 data flow / flow / 结构体设计不一致
- 关键设计约束未落地
- 结论依赖关键证据，但证据不存在
- `ai-slop-cleaner` 修改了代码，但清理后的实现还没有重新完成一致性验收

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
7. 如果进入过 `ai-slop-cleaner`，要明确说明：清理是否改代码、清理范围是什么、清理后是否已重新验收

如果没有发现不一致，也不能只说“通过”，仍要说明对照了什么。

如果需求结论依赖真实目标板、外设、时序、功耗、波形或现场观察，而本轮没有对应人工或现场证据，不能给 `pass`。

如果审查结论是 `blocked`，输出里必须明确列出“需要主 agent 修改的项”，这样主 agent 才能按项修复并重新送审。

## 与其他 skill 的关系

- 上游通常来自 `implementation-architecture-workflow`
- detail 输入通常来自 `implementation-struct-dataflow-workflow`
- 如需补验证证据，联动 `verification-before-completion`
- 如需独立质量复核，联动 `requesting-code-review`
- 如需在一致性通过后做垃圾代码清理和可维护性提升，联动 `ai-slop-cleaner`
- 默认在 `executing-plans` 的末尾作为最终收口门禁

## 最低要求

没有 architecture 文档、没有 detail 文档、没有代码对照，就不要假装做了最终验收。

验收的重点是**实现是否符合 architecture、detail 和 exec plan**，不是只看“代码能不能跑”。

如果进入了 `ai-slop-cleaner` 清理阶段，最终放行对象是**清理后的最终代码**，不是清理前那一版代码。
