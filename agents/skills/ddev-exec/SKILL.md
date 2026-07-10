---
name: ddev-exec
description: 在当前会话里按已写好的实现计划顺序执行任务时使用
---

# 执行计划

读取计划，先做批判性检查，再按顺序执行所有任务，并在完成后进入默认收尾。执行时不只看计划本身，还要把计划引用的 architecture / detail / flow / dataflow 文档一并作为实现依据。

**开始时声明：** “我正在使用 ddev-exec skill 来执行这个计划。”

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

### 第二步：按 Wave 执行

执行模型从"逐个任务串行"改为"Wave 内并行、Wave 间串行"。

#### Wave 调度流程

```
读取并行执行计划 → 确定 Wave 分组
  │
  ├─ Wave 1（无依赖任务组）
  │    ├── Agent(Task 1, isolation=worktree)  ─┐
  │    ├── Agent(Task 2, isolation=worktree)  ─┤ 并行派发
  │    └── Agent(Task 3, isolation=worktree)  ─┘
  │    │  等待全部完成
  │    ▼
  │   收集结果 → 更新 tracking files → 检查错误
  │
  ├─ Wave 2（依赖 W1 产出）
  │    ├── Agent(Task 4)  ─┐
  │    └── Agent(Task 5)  ─┘ 并行派发
  │    │  等待全部完成
  │    ▼
  │   收集结果 → 更新 tracking files
  │
  └─ Wave 3 ...
       └── Agent(Task 6) → 完成
```

#### 派发规则

1. **每个并行任务派发一个 General 子代理**，使用 `Agent` 工具，设置 `run_in_background: false`
2. 同一 Wave 内的所有 Agent **一次性全部派发**（多个 Agent 工具调用在同一轮发出）
3. 每个 Agent 的 prompt 包含：任务目标、引用文档摘要、文件范围、实现约束
4. **文件隔离**：如果同一 Wave 内两个任务可能冲突（极少见），对其中一方使用 `isolation: "worktree"`
5. 等待当前 Wave 的所有 Agent 完成后，收集结果，再进入下一 Wave

#### 子代理 Prompt 模板

```
按以下规格执行 Task N：

**目标：** <任务目标>

**必读文档（摘要已内联）：**
- spec: <关键约束/接口/数据结构>
- detail: <状态枚举/错误码/字段约束>

**文件范围：**
- 新建: <path>
- 修改: <path:line-range>

**实现约束：**
- <来自计划的具体约束>
- 不要修改本任务文件范围外的任何文件
- 完成后返回：修改了哪些文件、验证结果、未覆盖风险

**引用设计要点：**
<从上游文档提取的关键定义、签名、枚举值等>
```

#### 结果收集

每个 Wave 完成后，主代理必须：

1. 逐个检查 Agent 返回值：是否成功、是否有冲突
2. 更新 `task_plan.md`：标记对应任务 checkbox 为 `[x]`
3. 更新 `progress.md`：记录每个任务的产出和验证结果
4. 更新 `implementation-notes.md`：汇总每个 Agent 的 Design Decisions / Deviations
5. 如果任何 Agent 失败，暂停并分析原因后再决定是否重试

#### 单任务执行（无并行机会时）

如果计划中所有任务都有顺序依赖（只有一个 Wave），或计划没有并行执行计划，退回逐个任务执行：

1. 标记任务为 `in_progress`
2. 先阅读该任务引用的文档和图，确认输入、输出、状态、接口与流程约束
3. **读取目标文件当前内容（强制）**：对于本任务要修改的每个文件，先用 Read 读取其当前完整内容。确认：
   - 文件当前结构与计划中的预期一致
   - 计划要修改的行号/区域与文件实际内容匹配
   - 不存在未在计划中声明的并发修改或结构变化
   - 如果文件现状与计划预期不符，先停下来评估是否需要更新计划，不得盲目覆盖
4. 严格按计划步骤执行，不要擅自跳步，也不要脱离引用文档补设计
5. 运行该任务要求的验证
6. 做任务内一致性核对，确认实现结果与引用文档一致
7. 记录结果与未覆盖风险
8. 任务完成后再标记为 `completed`

如果计划里已经要求在步骤中提交、审查或补文档，就照计划执行，不要省略。

如果计划步骤与引用文档冲突，以已确认的 architecture / detail / flow / dataflow 文档为准，并立即回到计划审查，必要时先修计划再继续执行。

不要在任务刚做完时就提前宣称“计划完成”；默认要把最终完成结论留给收尾门禁。

### 第三步：阶段性与 Wave 后复核

- **Wave 内复核**：每个 Wave 的所有 Agent 完成后，主代理做快速一致性检查——各 Agent 产出是否冲突、是否与引用文档一致
- 连续完成 2-3 个 Wave，或完成明显里程碑后，用 `ddev-code-review` 做阶段性复核
- 若审查指出阻塞问题，先修复再继续后续 Wave
- 若只是非阻塞建议，记录后按优先级处理

### 第四步：默认收尾

当所有任务完成并通过计划要求的验证后，进入默认收尾顺序：

1. 用 `verification-before-completion` 补齐最终结论所需的验证证据
2. 如需独立质量复核，用 `ddev-code-review`
3. 进入 `ddev-gate` 做第一轮一致性验收，并拉独立审查 agent 核对 architecture、detail、data flow、flow、exec plan 与代码是否完全一致
4. 如果第一轮 `ddev-gate` 返回 `blocked`，主 agent 必须先修改，再重新进入 `ddev-gate`
5. 如果第一轮 `ddev-gate` 返回 `need-info`，主 agent 必须先补齐缺失输入、范围或验证证据，再重新进入 `ddev-gate`
6. 只有当 `ddev-gate` 给出一致性 `pass` 后，才进入 `ddev-clean` 清理阶段
7. 清理阶段必须使用独立 subagent，并把范围限制在 final gate 已接受的代码范围或更窄的 changed-files；若为锁定行为必须补最小测试文件，只允许纳入最小必要测试范围
8. 清理 subagent 必须按 `ddev-clean` 的 regression-tests-first、最小 diff、最小作用域规则执行，不得借 cleanup 扩大为重构或改设计
9. 如果 cleanup 没有做出代码修改，可直接保留上一轮 final gate 的一致性 `pass`，进入最终收尾
10. 如果 cleanup 做出了任何代码修改，主 agent 必须补充 cleanup 后的新验证证据，并重新进入 `ddev-gate` 做完整一致性重审
11. 只有当 cleanup 后的最后一次 `ddev-gate` 也返回 `pass`，才能宣称“计划已经完成”

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
- **不看目标文件当前内容就直接开写**
- 计划有明显缺口还硬执行
- 跳过验证
- 把”代码写了”当成”任务完成”
- 计划和上游文档冲突时，私自选择其中一个继续写
- 没经过默认收尾就宣称整体完成
- 在 `ddev-gate` 一致性 `pass` 之前提前进入 cleanup
- cleanup 改了代码却不重新回到 `ddev-gate`
- 未经用户明确同意就在 `main` / `master` 上开始实现
- **并行红线**：让两个 Agent 修改同一文件、让依赖未完成的任务提前执行、跨 Wave 并行（后一 Wave 依赖前一 Wave 产物）

## planning-with-files 状态追踪

执行过程中必须维护三份持久化文件，确保上下文穿越和断点恢复。

### 文件职责

| 文件 | 用途 | 何时创建 |
|------|------|---------|
| `task_plan.md` | 任务追踪：从 exec plan 提取 Task N 生成 checkbox 列表 + Errors 表 | 第一步完成后自动创建 |
| `progress.md` | 执行日志：每任务完成后记录产出和验证结果 | 首次写入时创建 |
| `implementation-notes.md` | 实现笔记：每任务完成后按 4 维度记录 AI 推理过程 | 首次任务完成后自动创建 |
| `findings/` | 上游设计决策（由 ddev-spec/detail/doc-review 写入，本阶段只读） | 已存在 |

### 第一步后：创建 task_plan.md

审查计划通过后，从 exec plan 文档中提取所有 Task N，生成 `task_plan.md`。格式：

```markdown
# 任务执行追踪

> 来源计划：docs/plans/26-06-20_xxx/exec_plans/feature-name.md
> 创建时间：2026-06-20
> 目标：<一句话目标>

## Current Task
- **Task**: Task 1 — 错误码枚举定义
- **Status**: in_progress

## Tasks

- [ ] Task 1 — 错误码枚举定义
- [ ] Task 2 — 上下文结构体
- [ ] Task 3 — 状态机实现
- [ ] Task 4 — API 接口暴露
- [ ] Task 5 — 单元测试

## Errors Encountered
| Error | Attempt | Task | Resolution |
|-------|---------|------|------------|
```

### 第二步中：每任务读写规则

**每个任务开始时**：
1. 读取 `task_plan.md` 确认目标和当前任务
2. 读取 `findings/index.md` 了解上游设计决策上下文（如有）

**每个任务完成后**：
1. 标记 `task_plan.md` 中该任务的 checkbox 为 `[x]`
2. 更新 `Current Task` 为下一个任务
3. 追加 `implementation-notes.md`，按 4 维度记录本任务的推理过程
4. 写入 `progress.md`，格式：

```markdown
### Task N — <任务名> ✅
- 新建/修改的文件列表
- 验证命令和结果
- 如有错误，简要说明
```

**错误发生时**：
- 写入 `task_plan.md` 的 Errors Encountered 表
- 遇到无法自行修复的错误，停止并上报用户

### implementation-notes.md 写入规则

每个任务完成后，必须在 `implementation-notes.md` 中追加本轮实现过程中出现的推理记录。格式：

```markdown
# Implementation Notes

> 来源计划：docs/plans/YY-MM-DD_xxx/exec_plans/feature-name.md
> 创建时间：2026-07-08

## Design Decisions
> spec/detail 文档未覆盖、AI 在实现过程中自行做出的设计选择

### Task N — <任务名>
- **决策**：<做了什么选择>
- **触发原因**：<spec 中哪个点没说清楚，导致必须自己做判断>
- **影响范围**：<哪些文件/接口受此决策影响>

## Deviations
> 故意偏离 spec/detail/plan 的实现，及偏离理由

### Task N — <任务名>
- **偏离点**：<文档要求 A，实际实现为 B>
- **理由**：<为什么偏离>
- **影响范围**：<哪些文件/接口受影响>

## Tradeoffs
> 考虑过但最终放弃的替代方案，及放弃原因

### Task N — <任务名>
- **替代方案**：<描述考虑过的方案>
- **放弃原因**：<为什么不选>
- **当前方案**：<实际采用的方案简述>

## Open Questions
> 拿不准、需要用户集中定夺的问题（攒着，不零散打断）

### Task N — <任务名>
- **问题**：<描述不确定点>
- **当前处理**：<临时用了什么方式>
- **建议**：<你认为应该怎么处理>
```

四个维度中，Design Decisions 和 Deviations 为**强制维度**——每个任务完成后必须至少检查这两类。Tradeoffs 和 Open Questions 为**按需维度**——有则必写，无则标注"无"。不得跳过整个文件。

Open Questions 中的问题在 ddev-gate 验收阶段会作为未决项被检查，因此在进入默认收尾前必须全部回答完毕。

### 第四步前：Stop Gate 前置检查

进入默认收尾前，验证 `task_plan.md` 中所有 Tasks 均已 `[x]`，且 `implementation-notes.md` 中 Open Questions 已全部回答完毕。未全部完成的不进入第四步。

### 断点恢复

会话中断后重新开始时：

0. 运行 `python scripts/session-catchup.py` 获取 5-Question Reboot Test 摘要
1. 读取 `task_plan.md` 定位当前 Wave 和未完成的任务
2. 读取 `progress.md` 了解已完成 Wave 和任务的产出和验证结果
3. 读取 `implementation-notes.md` 了解已完成任务中的设计决策、偏离和未决问题
4. 从当前 Wave 的第一个未完成任务继续——已完成的任务不重复执行

## 集成

**状态追踪文件：**
- 读取 `task_plan.md` — 每任务开始前确认目标，每任务完成后更新 checkbox
- 写入 `progress.md` — 每任务完成后记录产出和验证结果
- 写入 `implementation-notes.md` — 每任务完成后按 4 维度记录推理过程
- 读取 `findings/index.md` — 了解上游 spec/detail/doc-review 设计决策

**Required workflow skills:**
- **ddev-plan** - 产出本 skill 要执行的计划
- **ddev-code-review** - 阶段性复核与重要节点复核
- **verification-before-completion** - 对最终结论补齐验证证据
- **ddev-gate** - 默认最终验收
- **ddev-clean** - 一致性通过后的受限 cleanup / deslop 阶段
