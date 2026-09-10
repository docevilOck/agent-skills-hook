---
name: ddev-gate
description: 在代码实现完成后、准备结束任务或进入发布前使用，用来验收代码实现与文档规划架构的一致性，并通过合并的代码评审（编码规范、质量、注释、清理）后给出最终验收结论
---

# 实现最终验收门禁

## 作用

这个 skill 用于代码实现阶段的最终验收。

它只做两件事；对**大改动**，同一轮**同时派发两个独立 subagent**：

- **一致性审查**：只核对代码实现与 spec / detail / `docs/architecture/` 文档规划的**架构**是否一致——模块边界与职责归属、接口位置与签名、调用与依赖方向、状态所有权、数据流与关键流程骨架、联动注册点。不做逐行细节对照，不做命名、风格、注释、代码质量判断。
- **代码评审**：合并原来的代码质量审查、编码规范审查、注释审查，并负责给出受限清理清单，输出一份只读结论。C 项目加载 `ddev-c-pro` + `ddev-comment-gen` + `ddev-clean`；非 C 项目加载 `ddev-code-review` + 对应语言规范 / 注释 skill（如有）+ `ddev-clean`。

两个 subagent 在同一轮并行派发。只要本轮发生过任何代码修改（一致性修正、代码修复、注释补齐、清理），就必须基于最终代码重新并行派发两个只读复审，直到出现一轮：**两个审查在同一份最终代码上都 `pass`，且该轮没有任何代码修改**。

一致性审查发现的架构偏离按「修正优先、记录兜底」处理：

- 能修正的，修正到与文档规划一致；
- 无法修正，或经过考虑决定不修正的，写入 `implementation-notes.md` 的 Deviations（偏离点、理由、影响范围），审查确认已记录后可通过；
- 既未修正、也未记录的偏离 → `blocked`。

**小改动（默认）** 走 compact 路线：拉 1 个独立 subagent，一次性完成一致性 + 代码评审（含清理建议），输出一份结论，不派发第二个 subagent。

> **与旧流程的区别**：gate 不再有独立 `ddev-clean` 流水线阶段，也不再有 c-pro → comment-gen 的分段审查。注释审查与清理评估都已并入代码评审 subagent；清理执行由主 agent 按 `ddev-clean` 规则完成。streaming 路线从「逐段流水线」改为「两个 subagent 并行 + 只读复审」。

## 何时使用

在以下场景使用：

- 一个实现任务完成后，需要做正式验收
- 准备声称“已经完成实现”或“已经满足设计”
- 准备把改动交给下游联调、测试、提交或发布
- 需要确认代码实现没有背离 spec / detail 文档规划的架构

如果只是想先检查有没有跑验证命令，优先用 `verification-before-completion`。

如果只是想让另一个视角找 bug，优先用 `ddev-code-review`。

如果主 agent 正准备宣称“已经完成计划”“已经按计划实现完成”“可以正式收尾”，这个 skill 是必经门禁。

## 输入要求

开始验收前，至少定位这些输入：

- 本次改动对应的 spec 文档路径
- 本次改动对应的 detail 文档路径（含 structures / dataflow / flows）
- 相关代码变更范围
- 本轮验证证据

能拿到的话，额外读取：

- `implementation-notes.md`（由 ddev-exec 在执行过程中写入，含 Design Decisions / Deviations / Tradeoffs / Open Questions）
- `task_plan.md`（由 ddev-exec 创建，含任务 checkbox 和 Errors 表）
- 结构图 / 流程图 / 数据流图
- `ddev-plan` 产出的执行计划（只用于确定范围和任务背景，不作为架构真源）
- 构建、测试、静态检查或人工验证结果

如果连 spec 或 detail 文档都没有，不能直接给通过结论。

如果无法唯一定位 spec 文档、detail 文档或本次改动范围，不要退化成泛化 code review。此时应立即停止验收，并输出：

- `need-info`：信息暂时不足，但理论上可补齐
- `blocked`：当前上下文下无法继续定位或缺失关键设计输入

执行计划只用于确定范围和理解任务背景；一致性审查不再要求 exec plan 的每个步骤都落地，也不再把 exec plan 当作独立设计真源。

## 范围确定规则

验收范围必须先定清楚，再开始对照。

优先级如下：

1. 用户明确指定的文件范围或提交范围
2. `ddev-plan` 中列出的文件清单
3. 当前任务对应的 git diff / 工作区 diff
4. spec / detail 文档中明确点名的实现文件

如果 exec plan 中列出的文件范围明显超出 spec / detail / flow / dataflow 文档允许的边界，也要按范围异常处理，不能默认放行。

代码评审（含清理建议）的作用范围必须继承这份范围；如果能拿到更窄的 changed-files 列表，优先进一步收敛到 changed files。

如果为了锁定既有行为必须补最小回归测试，允许把**最小必要测试文件**纳入清理附属范围；这些测试文件也必须计入清理范围说明和后续验证证据。

如果范围仍然不清楚，先输出 `need-info`，不要自己扩散成全仓库审查。

## 改动面路由

进入核心流程前，先判定本次改动面大小，决定走 streaming（流式 / 双 subagent 并行）还是 compact（整合）路线。

**默认 compact**：除命中「大改动」外，一律走 compact 整合审查。

**判定「大改动」— 命中任一即走 streaming：**

1. diff 行数 > 300
2. code-review-graph 查到的影响范围超出本模块（存在受影响的跨模块调用方 / 文件）
3. 结构性重构：跨多文件重建结构体、数据流、状态机或公共接口，而非单文件内局部增量

**以下不单独构成「大改动」，仍走 compact：**

- 触发架构变更门禁（如「语音包可独立 OTA」这类外部可见行为变更）——架构文档补充本身是计划内小改动
- 涉及数据流 / 关键流程的局部修改——只要实现是单文件内局部增量（如新增 static 函数 + 换查表来源），API 对外签名不变
- C + Python + 文档的复合改动——按合计 diff 行数与实际影响半径判定，不因跨语言自动升级

判定依据取 spec / detail 声明的范围与 git diff / code-review-graph 查到的调用点影响范围中的**较严者**。

`ponytail: diff 行数阈值是启发式，可按团队习惯调整；与第 3 条结构性重构判定冲突时，以重构性质为准。`

## 核心流程（Streaming 路线）

0. **Stop Gate 前置检查**：主 agent 读取 `task_plan.md` 和 `implementation-notes.md`，确认以下条件同时满足才能继续验收流程，否则返回 `blocked`：
   - 所有任务 checkbox 均为 `[x]`（completed）
   - Errors Encountered 表中所有错误均已解决（Resolution 列非空或已标记 Resolved）
   - `implementation-notes.md` 中存在且 Open Questions 已全部回答完毕（无未决项）
   - 若存在 `scripts/check-complete`，运行确认输出 "ALL PHASES COMPLETE"
1. 主 agent 定位 spec 文档、detail 文档、架构文档、代码范围、本轮验证证据、`implementation-notes.md` 和 `task_plan.md`，整理成明确的审查上下文。
2. 主 agent 先读取 `implementation-notes.md`，提取 Deviations 和 Open Questions：
   - Deviations 条目 → 作为一致性审查的重点检查项
   - Design Decisions → 作为 spec 空白处的补充验收依据，审查 agent 需确认决策合理且未引入新的未批准架构
   - Open Questions → 若有未回答的，直接判定 `blocked`；若已回答，将其回答结论纳入验收范围
3. **同一轮并行派发两个独立 subagent（提示词必须使用固定模板，禁止主 agent 自行生成）**。为保证两个审查读到同一份稳定代码，本轮两个 subagent 都只读、不修改文件；清理在评审返回后由主 agent 执行：
   - **A. 一致性审查**（只读）：直接使用 [streaming-reviewer-prompt.md](streaming-reviewer-prompt.md) 全文作为提示词，只填写其中的任务输入；只核对代码与文档规划架构的一致性，输出偏离清单。
   - **B. 代码评审**（只读）：直接使用 [code-reviewer-prompt.md](code-reviewer-prompt.md) 全文作为提示词，只填写其中的任务输入；按项目语言合并完成编码规范、代码质量、注释完整性审查，并按 `ddev-clean` 判断标准输出受限清理清单。
4. 等待两个 subagent 返回：
   - A 输出 `pass` / `need-info` / `blocked`，并给出架构偏离清单；每项偏离标注建议处置：**修正** 或 **记录**。
   - B 输出 `pass` / `blocked`，附问题分级（CRITICAL / HIGH / MEDIUM / LOW）、注释缺失清单、清理建议清单。
5. 主 agent 汇总处置：
   - A 报出的偏离：可修正的立即修正到与文档一致；无法修正或决定不修正的，写入 `implementation-notes.md` 的 Deviations（偏离点、理由、影响范围）。
   - B 报出的阻塞项（CRITICAL / HIGH）和缺失注释：按其清单修复、补齐。
   - B 的清理建议清单：由主 agent 按 `ddev-clean` 的 regression-tests-first、显式清理计划、分 smell 分 pass、最小 diff、最小作用域规则执行。直接在主 agent 内加载 `ddev-clean` 执行，或派发清理 subagent；派发时必须原样使用 [ddev-clean/reviewer-prompt.md](../ddev-clean/reviewer-prompt.md) 全文作为提示词，只填写任务输入，禁止自行生成提示词。清理后补充对应验证证据。
   - 任何代码修改后，补充对应的验证证据（沿用 cleanup 前的旧证据不算）。
6. **复审规则**：只要本轮发生过任何代码修改（主 agent 的修复或清理），就必须基于最终代码**重新并行派发 A + B 做只读复审**。复审轮两个 subagent 都不得再修改代码，只验证最终状态；发现新问题就报 `blocked`，由主 agent 修复后再来一轮。
7. 重复步骤 6，直到出现一轮：A 与 B 都 `pass`，且该轮没有任何代码修改。此时主 agent 才能给最终 `pass`。
8. 下列情况直接 `blocked`：
   - A 报出的架构偏离既未修正，也未写入 `implementation-notes.md` 记录；
   - B 存在未处理的 CRITICAL / HIGH，或注释缺失未补齐；
   - 清理过程改变了文档已批准的架构、接口或行为，且未回退、未重新走双审；
   - 两个审查无法在同一份最终代码上同时通过。
9. 如果没有新的、可归属到本轮结论的验证证据，最多输出 `need-info`，不能输出 `pass`。

## Compact 路线（小改动）

改动面路由判定为小改动时走本路线。核心原则：**1 个独立 subagent 一次性完成两个维度**，不派发第二个 subagent，不单独调用 `ddev-clean`。

C0. **前置检查**：同 Streaming 步骤 0。不满足 → `blocked`。
C1. 主 agent 定位 spec、detail、架构文档、代码范围、本轮验证证据、`implementation-notes.md` 和 `task_plan.md`，读取并整理成审查上下文。
C2. 主 agent 读取 `implementation-notes.md`，提取 Deviations（作为一致性重点检查项）、Design Decisions（作为 spec 空白处补充依据）、Open Questions（未答 → `blocked`）。
C3. 拉 **1 个独立 subagent** 做整合审查：**直接使用 [compact-reviewer-prompt.md](compact-reviewer-prompt.md) 全文作为提示词，只填写其中的任务输入，禁止主 agent 自行生成或改写提示词**。该 agent **只读**，一次性完成：
    - **一致性对照**：只核对代码与文档规划架构的一致性（模块边界、接口、依赖方向、状态归属、数据流/流程骨架），输出偏离清单并标注建议处置（修正 / 记录）；**先用 code-review-graph 看影响面与需审查文件、`grep` 兜底**，影响面超出 spec/detail 声明范围视为偏离
    - **代码评审**：按项目语言合并编码规范、代码质量（安全、架构性能、死代码/重复）、注释完整性；同时给出可选的清理建议清单，但不执行清理
    - 输出一份结论 `pass` / `need-info` / `blocked`，附偏离清单、问题分级、注释缺失清单、清理建议
C4. 主 agent 汇总处置：
    - 架构偏离：能修正的修正；无法修正或决定不修正的，写入 `implementation-notes.md` 的 Deviations
    - CRITICAL / HIGH 问题：修复；缺失注释：补齐
    - 清理建议默认不阻塞；主 agent 决定是否按 `ddev-clean` 规则处理。若派发清理 subagent，必须原样使用 [ddev-clean/reviewer-prompt.md](../ddev-clean/reviewer-prompt.md) 全文作为提示词；若处理了代码，补验证证据后从 C3 重跑整合审查
C5. 只要本轮发生过任何代码修改，必须基于最终代码重跑 C3 做只读复审，直到出现一轮：整合审查 `pass` 且该轮无代码修改。
C6. `blocked` → 主 agent 按清单修改，重新进入本 skill，从 C1 重跑 Compact 路线（不升级为 Streaming）。
C7. `need-info` → 补齐缺失输入 / 范围 / 验证证据后从 C3 重跑。
C8. `pass` → 满足「结论规则」中 compact 条件后，主 agent 才能宣称"已经按计划完成"。

Compact 路线同样要求 spec、detail、代码范围、验证证据齐全，缺任何一项都不能给 `pass`。Compact 整合审查 agent 只读，不得在审查过程中修改代码。

## 审查 agent 要求

> **通用规则**：所有审查 agent 评估改动影响面时，一律**先用 `code-review-graph` 看影响面与需审查文件**，再 `grep` / `read` 兜底。图缺失（无 `.code-review-graph/`）时先 `code-review-graph build`。

> **提示词模板硬性要求**：streaming 路线必须直接把 [streaming-reviewer-prompt.md](streaming-reviewer-prompt.md) 全文用作一致性审查提示词，把 [code-reviewer-prompt.md](code-reviewer-prompt.md) 全文用作代码评审提示词；compact 路线必须直接把 [compact-reviewer-prompt.md](compact-reviewer-prompt.md) 全文用作整合审查提示词。主 agent 只填写模板里的「任务输入」，禁止自行生成、概括、改写或拼装审查提示词；模板缺失或无法读取时停止派发并报告，不得用现场生成的提示词替代。

### 一致性审查 agent 要求

- 必须是独立视角，只读，不能把主 agent 自己的口头总结当结论
- **只审查架构一致性**：模块边界与职责、接口位置与签名、调用/依赖方向、状态所有权、数据流与关键流程骨架、联动注册点、文档批准的共享状态与全局变量边界
- 必须显式核对 spec、detail / 架构文档、代码事实三类输入，以及 `implementation-notes.md` 中的 Deviations
- **先用 code-review-graph 看影响面与需审查文件、`grep` 兜底**：确认实际影响范围与文档声明一致；存在文档未声明的受影响模块或新增跨模块耦合 → 视为偏离
- 每个偏离必须给出：文档依据、代码事实、位置、建议处置（修正 / 记录）
- 不检查 exec plan 的逐步落地，不检查命名、风格、注释、测试覆盖、代码质量；这些分别归文档计划和代码评审负责
- 不允许用“基本一致”“差不多符合”“核心没问题”这类模糊表述放行
- 如果本轮代码已经过清理或修复，必须按**最终代码**重做对照，不能沿用上一轮结论

一致性审查必须原样使用提示模板 [streaming-reviewer-prompt.md](streaming-reviewer-prompt.md)，主 agent 只填写模板中的任务输入，不得自行生成提示词。

### 代码评审 agent 要求

必须是独立视角，不能复用一致性审查 agent 的结论。按项目语言路由，**一次性合并**以下维度，输出一份结论：

- **C 项目（`.c` / `.h`）**：加载 `ddev-c-pro`（编码规范 + 代码质量：安全、架构性能、死代码/重复）+ `ddev-comment-gen`（注释完整性）+ `ddev-clean`（清理项识别，只出清单）。不再单独调用 `ddev-code-review`，也不再有单独 c-pro / comment-gen 阶段。
- **非 C 项目**：加载 `ddev-code-review`（代码质量）+ 对应语言编码规范 skill（如有）+ 对应注释审查 skill（如有）+ `ddev-clean`（清理项识别，只出清单）。没有对应 skill 的维度在结论中标注“已跳过”。
- **先用 code-review-graph 看影响面与需审查文件、`grep` 兜底**：确认审查范围覆盖所有受影响文件。
- **问题分级**：CRITICAL（安全漏洞 / 崩溃）> HIGH（Bug / 严重异味）> MEDIUM（技术债）> LOW（建议）。存在 CRITICAL 或 HIGH → `blocked`；仅 MEDIUM / LOW → `pass`（在建议项中列出）。
- **注释完整性**：缺失或不足 → `blocked`，并附逐项缺失清单和补全建议。
- **清理**：按 `ddev-clean` 的判断标准输出清理清单，不执行清理。清单不得建议改变行为、接口、文档已批准的架构或数据流。主 agent 在评审返回后按 `ddev-clean` 规则执行（regression-tests-first、显式清理计划、分 smell 分 pass、最小 diff、最小作用域），并补充验证证据；执行后基于最终代码重新并行派发两个审查。
- **任何轮次都只读**：代码评审 subagent 不修改代码；复审轮重点验证上一轮修复 / 清理的最终状态。
- 不允许用"基本规范""大体符合""基本齐全"等模糊表述放行。
- 如果代码经过修复或清理，必须基于最终版本重新审查，不能沿用前次结论。

代码评审必须原样使用提示模板 [code-reviewer-prompt.md](code-reviewer-prompt.md)，主 agent 只填写模板中的任务输入，不得自行生成或改写提示词。

### Compact 整合审查 agent 要求

（compact 路线专用；Streaming 路线使用上方两个独立 agent）

- 必须是独立视角，只读，不能复用主 agent 的口头总结
- **一次性完成两个维度的审查**，输出一份结论：
  1. **一致性**：只核对代码与文档规划架构的一致性（模块边界、接口、依赖方向、状态归属、数据流/流程骨架）；显式核对 Deviations 的处置状态；**先用 code-review-graph 看影响面与需审查文件、`grep` 兜底**，影响面超出 spec/detail 声明范围视为偏离
  2. **代码评审**：按项目语言合并编码规范、代码质量、注释完整性；问题按 CRITICAL / HIGH / MEDIUM / LOW 分级；缺失注释 → `blocked`；清理只给建议清单，不执行
- 结论只允许 `pass` / `need-info` / `blocked`
- 不允许用"基本一致""大体符合"等模糊表述放行
- 如果代码经过主 agent 修复或按建议清理后重审，必须基于最终版本重新审查，不能沿用前次结论

compact 整合审查必须原样使用提示模板 [compact-reviewer-prompt.md](compact-reviewer-prompt.md)，主 agent 只填写模板中的任务输入，不得自行生成或改写提示词。

## 重点检查项

默认重点检查（架构一致性）：

- 模块边界、模块职责是否与 spec / `docs/architecture/` 一致
- 接口位置、调用方向、接入点是否与 spec 设计一致
- 结构体归属、字段 ownership、状态所有权是否与 detail / structures 文档一致
- 数据流入口、转换、出口，以及关键流程骨架、状态迁移、错误路径是否与 detail 文档一致
- 联动注册点（分发表、回调表、枚举映射、构建目标等）是否与 spec 的联动修改清单一致
- 是否新增了文档未批准的跨模块依赖、共享可变状态或业务全局变量
- 是否破坏文档约定的 `static` 私有边界、`switch` / 表驱动 / 状态机结构
- 架构偏离是否已修正，或已写入 `implementation-notes.md` 的 Deviations

不再由一致性审查负责的项：

- exec plan 的每个步骤是否落地（属于执行记录）
- 命名、风格、编码规范（属于代码评审）
- 注释完整性（属于代码评审）
- 测试覆盖、构建结果（属于验证证据，由主 agent 在结论中核对）

对于嵌入式 C / 纯 C 项目，额外重点检查：

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

compact 路线同样只允许这三种结论；两个审查维度由 1 个整合 subagent 一次性覆盖。

### `pass`

只有在以下条件同时满足时才能给：

- 已找到并核对 spec 文档
- 已找到并核对 detail / 架构文档
- 已明确本轮验收对应的代码范围
- **一致性**：代码与文档规划的架构一致，或每一处偏离都已修正、或已写入 `implementation-notes.md` 的 Deviations 且理由和影响范围清楚
- **代码评审**：无未处理的 CRITICAL / HIGH；注释完整（或该语言无对应 skill 并已标注“已跳过”）；清理建议清单已给出（或无需清理）；如主 agent 执行了清理，清理未改变文档已批准的架构、接口、行为和范围，并已补充验证证据
- **最终轮**：最后一轮中一致性审查与代码评审在同一份最终代码上都 `pass`，且该轮没有任何代码修改；若此前发生过修改，已完成只读复审
- 本轮存在新的验证证据，且证据与结论匹配
- 未覆盖风险已明确说明
- task_plan.md 存在且所有 checkbox 已完成、所有错误已解决、check-complete 验证通过，且 `implementation-notes.md` 中 Open Questions 已全部回答完毕
- 如果 `implementation-notes.md` 中存在 Deviations，每一项都已给出结论（已修正 / 已接受并记录 / 需补文档）

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

- 找不到 spec 文档或 detail 文档
- `implementation-notes.md` 不存在，或其中 Open Questions 仍有未回答项
- 无法定位本轮改动对应的实现范围
- 代码偏离文档规划的架构，且既未修正、也未写入 `implementation-notes.md`
- 一致性审查与代码评审无法在同一份最终代码上同时通过
- 代码评审存在 CRITICAL / HIGH 问题未处理
- 注释审查发现缺失且未补齐
- 清理过程改变了文档已批准的架构、接口或行为，且未回退、未重新走双审
- 结论依赖关键证据，但证据不存在
- task_plan.md 或 Stop Gate 前置条件不满足

判定原则：

- 关键设计基线缺失、互相冲突或当前上下文下无法建立时，用 `blocked`
- 在补齐前提之前继续审查没有意义的，用 `blocked`
- 只要需要打回主 agent 改代码或改文档后再审，也用 `blocked`

## 输出格式

最终输出必须包含：

1. 验收结论：`pass` / `need-info` / `blocked`
2. 对照范围：看了哪些 spec / detail / 架构文档 / implementation-notes / code / 验证材料
3. 并行审查摘要：
   - 一致性审查结论：架构是否一致
   - 代码评审结论：问题分级汇总（CRITICAL / HIGH / MEDIUM / LOW 各几条）、注释完整性、清理建议数量与执行情况
4. 架构偏离处置表：

   | 偏离点 | 文档依据 | 处置（已修正 / 已记录 / 未处理） | 位置 |
   |--------|----------|----------------------------------|------|

5. 发现的问题：按严重度列出
6. 已确认一致的关键点：只列最重要的几项
7. 未覆盖风险：明确还没验证到哪里
8. 清理与修复说明：是否改过代码、范围是什么、验证证据是什么、是否已完成只读复审
9. 如果结论是 `blocked`，明确列出“需要主 agent 修改的项”，以便按项修复并重新送审

**compact 路线**：第 3–4 项合并为一份「整合审查结论」，一次性输出一致性 + 代码评审两个维度的结果和偏离处置表。

如果没有发现不一致，也不能只说“通过”，仍要说明对照了什么。

如果需求结论依赖真实目标板、外设、时序、功耗、波形或现场观察，而本轮没有对应人工或现场证据，不能给 `pass`。

## 与其他 skill 的关系

- 上游通常来自 `ddev-spec`、`ddev-detail`、`ddev-plan`、`ddev-exec`
- 如需补验证证据，联动 `verification-before-completion`
- **一致性审查**由本 skill 直接派发独立 subagent
- **代码评审**合并以下 skill 的职责，由本 skill 派发的代码评审 subagent 统一加载：
  - `ddev-code-review`（非 C 项目的代码质量维度；也可独立触发）
  - `ddev-c-pro`（C 项目的编码规范 + 代码质量维度）
  - `ddev-comment-gen`（C 项目的注释审查维度）
  - 对应语言的编码规范 / 注释 skill（非 C 项目，如有）
  - `ddev-clean`（清理项识别维度；清理执行由主 agent 按需调用，也可独立触发）
- **compact 路线**：小改动由 1 个整合审查 subagent 一次性覆盖一致性 + 代码评审；不单独调用 `ddev-clean`
- 默认在 `ddev-exec` 的末尾作为最终收口门禁

### ⚠️ 阶段交接硬门禁

**本 skill 完成后，禁止 agent 自动进入任何后续阶段（ddev-archive / git commit / 发布 / 部署 等）。**

- gate 最终 `pass` 后，向用户报告完整的验收结论（一致性、代码评审、清理）。
- 提示用户可选后续操作（如"是否提交代码？""是否进入 ddev-archive 归档？"），但**必须等待用户明确确认**。
- 用户未明确说"提交""归档""发布""推送"等指令前，停留在 gate 结论输出阶段，不自行推进。
- gate 内部的「并行审查 → 修复/清理 → 只读复审」循环为自动化流程，不受此限制。

## 最低要求

没有 spec 文档、没有 detail 文档、没有代码对照，就不要假装做了最终验收。

验收的重点是：**实现是否符合文档规划的架构** + **合并后的代码评审是否通过**，不是只看"代码能不能跑"。

streaming 路线必须真正做到两个 subagent 并行派发；最终放行对象必须是两个只读复审 subagent 在同一份最终代码上共同 `pass` 的那一版代码，不是任何中间版本。

清理评估已并入代码评审（清理执行由主 agent 按 `ddev-clean` 规则完成），不再有独立 `ddev-clean` 阶段；注释审查也已并入代码评审（C 项目通过 `ddev-comment-gen` 维度覆盖），两者都必须通过才能给最终 `pass`。

**compact 路线**：同样必须有 spec、detail、代码范围、验证证据；整合 subagent 通过（覆盖一致性、代码评审、清理建议）才能给最终 `pass`，不因改动小而降低底线。
