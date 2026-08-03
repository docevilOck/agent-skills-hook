---
name: ddev-gate
description: 在代码实现完成后、准备结束任务或进入发布前使用，用来核对代码实现是否与 spec 文档以及 detail 文档一致，并通过代码质量审查、清理、编码规范和注释审查后给出最终验收结论
---

# 实现最终验收门禁

## 作用

这个 skill 用于代码实现阶段的最终验收。

它不是普通代码审查，也不是只跑测试的验证门禁。它的核心任务根据项目语言分支：

按改动面大小分流（判定标准见「改动面路由」）：

- **大改动** → 走下方流式门禁：C 项目四段流程、非 C 项目五段流程
- **小改动** → 走 compact 整合审查：拉 1 个独立 subagent 一次性完成 一致性 + 编码规范与质量 + 注释 三合一审查，跳过 `ddev-clean`，输出一份结论

**C 项目（`.c` / `.h`）— 四段流程：**

1. **先拉独立审查 agent**，把**代码实现**与以下设计输入做逐项对照
2. **一致性通过后，再拉独立 subagent 调用 `ddev-clean`**，在受限范围内做垃圾代码清理和可维护性提升；若清理改了代码，再重新回到一致性验收
3. **cleaner 阶段结束后，拉独立 subagent 加载 `ddev-c-pro`**，统一完成编码规范审查 + 代码质量审查（安全、架构性能、死代码/重复）。C 项目不再单独调用 `ddev-code-review`，由 c-pro 吸收其 C 相关职责。若审查不通过，修改后重新回到一致性验收
4. **c-pro 审查通过后，拉独立 subagent 做注释/文档审查**：加载 `ddev-comment-gen`，对最终代码做注释完整性和规范性审查；若审查不通过，修改后重新回到一致性验收

**非 C 项目 — 五段流程：**

1. 一致性验收（同上）
2. `ddev-clean` 清理（同上）
3. `ddev-code-review` 代码质量审查（安全、性能、可维护性）；若审查不通过，修改后重新回到一致性验收
4. 编码规范审查：根据语言加载对应的 skill，无对应 skill 则跳过；若审查不通过，修改后重新回到一致性验收
5. 注释/文档审查：根据语言加载对应的 skill，无对应 skill 则跳过；若审查不通过，修改后重新回到一致性验收

第一段一致性验收要对照的设计输入包括：

- `ddev-spec` 产出的 spec 文档
- `ddev-detail` 产出的 detail 文档
- 必要时补充执行计划、验证结果和相关图文档

目标是明确回答：

- 实现是否忠实落地了 spec 设计
- 实现是否偏离了结构体、数据流、流程设计
- 执行计划是否正确引用、传递并落实了这些设计约束，而不是在计划阶段偷偷发明新设计
- 偏离是否合理、是否被显式更新到文档
- 这次改动是否可以给出最终验收结论

这里的设计一致性判断遵循同一条文档规则：spec、detail、exec plan 只定义”这次要做什么”。凡是文档里没有明确写到的实现、结构、流程、共享状态、旁路逻辑或验证动作，都按未获批准处理，而不是等待文档再额外写一段”明确不做”。

如果审查 agent 发现任何未被批准的差异，就必须审核不通过，打回主 agent 修改。主 agent 修改后，必须重新进入这个 skill，再拉审查 agent 重审。这个循环要一直持续到审查 agent 给出一致性 `pass`。

但一致性 `pass` 还不是最终放行：主 agent 还必须再拉一个独立 subagent，受限调用 `ddev-clean` 做清理。如果清理阶段产生任何代码修改，就必须重新进入这个 skill，再次拉独立审查 agent 做一致性重审。

一致性重审通过后，对 C 项目：拉独立 subagent 加载 `ddev-c-pro` skill，统一完成编码规范审查和代码质量审查（安全、架构性能、死代码/重复）。C 项目不再单独调用 `ddev-code-review`。对非 C 项目：先拉 `ddev-code-review` 做代码质量审查，再按语言加载编码规范审查 skill。如果审查不通过，修改后同样要重新进入这个 skill 从头验收。

c-pro / 编码规范审查通过后，还需再拉一个独立 subagent 做注释/文档审查。C 项目加载 `ddev-comment-gen` skill，对最终代码做注释完整性和规范性审查。其他语言项目根据实际语言加载对应的注释审查 skill。如果注释审查不通过，修改后同样要重新进入这个 skill 从头验收。

只有在**清理后的最终代码**通过一致性验收、**代码规范与质量审查**（C 项目由 c-pro 统一完成，非 C 项目由 code-review + 语言规范审查完成）和 **注释审查**均通过后，主 agent 才能宣称”计划已经完成”。

## 何时使用

在以下场景使用：

- 一个实现任务完成后，需要做正式验收
- 准备声称“已经完成实现”或“已经满足设计”
- 准备把改动交给下游联调、测试、提交或发布
- 需要确认代码实现没有背离 spec/detail 文档

如果只是想先检查有没有跑验证命令，优先用 `verification-before-completion`。

如果只是想让另一个视角找 bug，优先用 `ddev-code-review`。

如果目标是**实现与设计一致性验收**，并在通过后继续做一轮受限 deslop / maintainability cleanup，再经代码质量审查、编码规范审查和注释审查，最后复核一致性，用这个 skill。

如果主 agent 正准备宣称“已经完成计划”“已经按计划实现完成”“可以正式收尾”，这个 skill 是必经门禁。

## 输入要求

开始验收前，至少定位这些输入：

- 本次改动对应的 spec 文档路径
- 本次改动对应的 detail 文档路径
- 相关代码变更范围

能拿到的话，额外读取：

- `implementation-notes.md`（由 ddev-exec 在执行过程中写入，含 Design Decisions / Deviations / Tradeoffs / Open Questions）
- `task_plan.md`（由 ddev-exec 创建，含任务 checkbox 和 Errors 表）
- 结构图 / 流程图 / 数据流图
- `ddev-plan` 产出的执行计划
- 构建、测试、静态检查或人工验证结果

如果连 spec 或 detail 文档都没有，不能直接给通过结论。

如果无法唯一定位 spec 文档、detail 文档或本次改动范围，不要退化成泛化 code review。此时应立即停止一致性验收，并输出：

- `need-info`：信息暂时不足，但理论上可补齐
- `blocked`：当前上下文下无法继续定位或缺失关键设计输入

如果拿到了 exec plan，还要检查它是否明确引用了 spec / detail / flow / dataflow 文档，是否把这些文档里的约束正确传递给执行阶段；不能把 exec plan 当成脱离设计文档独立成立的真源。

## 范围确定规则

验收范围必须先定清楚，再开始对照。

优先级如下：

1. 用户明确指定的文件范围或提交范围
2. `ddev-plan` 中列出的文件清单
3. 当前任务对应的 git diff / 工作区 diff
4. spec/detail 文档中明确点名的实现文件

如果 exec plan 中列出的文件范围明显超出 spec / detail / flow / dataflow 文档允许的边界，也要按范围异常处理，不能默认放行。

后续 `ddev-clean` 的作用范围默认也必须继承这份范围；如果能拿到更窄的 changed-files 列表，优先把清理范围进一步收敛到 changed files。

`ddev-c-pro` 规范审查和 `ddev-comment-gen` 注释审查（C 项目）或其他语言的编码规范审查和注释审查的范围与 cleaner 一致，审查最终版本的代码文件。

如果为了满足 `ddev-clean` 的 regression-tests-first 规则，必须补最小测试覆盖，则允许把**锁定既有行为所必需的最小测试文件**纳入 cleanup 附属范围；这些测试文件也必须计入 cleanup 范围说明和后续验证证据。

如果范围仍然不清楚，先输出 `need-info`，不要自己扩散成全仓库审查。

## 改动面路由

进入核心流程前，先判定本次改动面大小，决定走 streaming（流式）还是 compact（整合）路线。

**判定「大改动」— 命中任一即走 streaming：**

1. 触发架构变更门禁：公共接口 / 协议 / 持久化格式 / 跨核交互 / 跨模块依赖 / 外部可见行为变更
2. 核心设计变更：结构体定义、数据流、状态机、关键流程（spec/detail 涉及这些）
3. diff 行数 > 300
4. `codegraph_impact` 影响半径超出本模块

否则 → **compact 路线**。

判定依据取 spec/detail 声明的范围与 git diff / `codegraph_impact` 实际影响面中的**较严者**。

`ponytail: diff 行数阈值是启发式，可按团队习惯调整；与第 1–2 条设计性质判定冲突时，以设计性质为准。`

## 核心流程

0. **Stop Gate 前置检查**：主 agent 读取 `task_plan.md` 和 `implementation-notes.md`，确认以下条件同时满足才能继续验收流程，否则返回 `blocked`：
   - 所有任务 checkbox 均为 `[x]`（completed）
   - Errors Encountered 表中所有错误均已解决（Resolution 列非空或已标记 Resolved）
   - `implementation-notes.md` 中存在且 Open Questions 已全部回答完毕（无未决项）
   - 若存在 `scripts/check-complete`，运行确认输出 "ALL PHASES COMPLETE"
0.5. **改动面路由**：按「改动面路由」判定本次改动面。
     - 命中任意「大改动」条件 → 走下方 **Streaming 路线**（步骤 1–30）。
     - 未命中 → 走 **Compact 路线（小改动）**（见「Compact 路线（小改动）」小节），完成后回到本流程的最终验收判断。
1. 主 agent 先定位 spec 文档、detail 文档、exec plan、`implementation-notes.md`、代码范围和本轮验证证据。
2. 主 agent 读取这些输入，整理成明确的审查上下文。
3. **主 agent 先读取 `implementation-notes.md`**，提取 Deviations 和 Open Questions：
   - Deviations 条目 → 直接映射为本轮一致性验收的重点偏离检查项
   - Design Decisions → 作为 spec 空白处的补充验收依据，审查 agent 需确认决策合理且未引入新的未批准设计
   - Open Questions → 若有未回答的，直接判定 `blocked`；若已回答，将其回答结论纳入验收范围
4. 主 agent 使用独立审查 agent 执行第一轮最终一致性验收。
5. 审查 agent 必须按"spec -> detail -> exec plan -> implementation-notes -> code -> evidence"的顺序逐项对照。
6. 审查 agent 先检查 exec plan 是否正确引用 spec / detail / flow / dataflow 文档，是否把这些约束传递成了可执行任务，而不是新增了文档中不存在的设计。
7. 审查 agent 检查实现里是否出现文档或计划未批准的偏离。
8. 审查 agent 检查文档强调的约束是否真的落到了代码里，而不是只写在文档里。
9. 审查 agent 输出 `pass`、`need-info` 或 `blocked`。
10. 如果结论是 `blocked`，主 agent 必须先修改代码或补齐文档，再重新进入这个 skill，重新拉审查 agent 验收。
11. 如果结论是 `need-info`，主 agent 必须先补齐缺失输入、范围或验证证据，不得进入 cleanup；补齐后重新进入这个 skill。
12. 只有当第一轮一致性结论为 `pass` 时，主 agent 才能进入清理阶段。
13. 主 agent 拉一个新的独立 subagent，在当前代码范围或更窄 changed-files 范围内调用 `ddev-clean`。
14. 清理 subagent 必须遵守 `ddev-clean` 的 regression-tests-first、显式 cleanup plan、分 smell 分 pass、最小 diff、最小作用域规则。
15. 如果清理 subagent 没有做出任何代码修改，主 agent 可直接保留第一轮一致性结论，进入最终收尾。
16. 如果清理 subagent 做出了代码修改，主 agent 必须补充这些修改对应的验证证据，并重新拉独立审查 agent，再做一次完整一致性验收。
17. 只有当**最后一次一致性验收**输出 `pass` 时，主 agent 才能进入代码规范与质量审查阶段。
18. **C 项目（`.c` / `.h`）**：主 agent 拉一个新的独立 subagent 加载 `ddev-c-pro` skill，对**当前代码范围**统一完成编码规范审查和代码质量审查（安全、架构性能、死代码/重复）。C 项目不再单独调用 `ddev-code-review`。
19. c-pro 审查 subagent 按 `ddev-c-pro` 中的设计规范、命名规范、风格偏好、安全、架构性能、死代码/重复逐项审查，对问题按 CRITICAL/HIGH/MEDIUM/LOW 分级。
20. c-pro 审查 subagent 输出 `pass` 或 `blocked`。存在 CRITICAL 或 HIGH → `blocked`。仅 MEDIUM/LOW → `pass`（在建议项中列出）。
21. 如果 c-pro 审查 `blocked`，主 agent 必须按清单修改代码，然后重新进入这个 skill（从一致性验收重新开始完整流程）。
22. 如果 c-pro 审查的修改涉及结构、接口或流程变更，必须在修改后回到一致性验收重审。
23. **非 C 项目**：先拉独立 subagent 加载 `ddev-code-review` skill 做代码质量审查，结论 `REQUEST CHANGES`（CRITICAL/HIGH）视为 `blocked`。通过后再按语言加载编码规范审查 skill（如存在），不通过则回到一致性验收。
24. 只有当代码规范与质量审查输出 `pass`（或合理跳过）时，主 agent 才能进入注释/文档审查阶段。
25. 主 agent 根据项目语言路由注释审查：
    - **C 项目**（`.c` / `.h`）：拉新的独立 subagent 加载 `ddev-comment-gen` skill，对**通过规范审查的最终代码**做注释审查
    - **其他语言项目**：如果没有对应的注释审查 skill，跳过此阶段（在结论中标注”本语言暂无注释审查 skill，已跳过”）
26. 注释审查 subagent 按对应 skill 中的审查维度逐文件、逐函数、逐结构体验证注释完整性。
27. 注释审查 subagent 输出 `pass` 或 `blocked`，`blocked` 时必须附带缺失项清单和补全建议。
28. 如果注释审查 `blocked`，主 agent 必须按清单补全注释，然后重新进入这个 skill（从一致性验收重新开始完整流程）。
29. 如果注释审查的修改涉及函数签名或行为变更，必须在修改后回到一致性验收重审。
30. 只有当代码规范与质量审查和注释审查均输出 `pass`（或合理跳过）时，主 agent 才能宣称”已经按计划完成”。

如果没有新的、可归属到本轮结论的验证证据，最多输出 `need-info`，不能输出 `pass`。

如果清理 subagent 产出的改动超出既定范围、引入新的抽象层、或让实现偏离 spec/detail/exec plan，也必须回到 `blocked`，不能因为”一致性阶段之前通过过”而继续放行。

## Compact 路线（小改动）

改动面路由判定为小改动时走本路线。核心原则：**一次整合审查取代四段流**，跳过 `ddev-clean`，保留独立视角。

C0. **前置检查**：同 Streaming 步骤 0（task_plan 全部完成、错误已解决、`implementation-notes.md` 存在且 Open Questions 已答完、check-complete 通过）。不满足 → `blocked`。
C1. 主 agent 定位 spec、detail、exec plan（如有）、`implementation-notes.md`、代码范围和本轮验证证据，读取并整理成审查上下文。
C2. 主 agent 读取 `implementation-notes.md`，提取 Deviations（映射为一致性重点检查项）、Design Decisions（作为 spec 空白处补充依据）、Open Questions（未答 → `blocked`）。
C3. 拉 **1 个独立 subagent** 做整合审查，提示模板见 [compact-reviewer-prompt.md](compact-reviewer-prompt.md)。该 agent 一次性完成：
    - **一致性对照**：按 spec → detail → exec plan → notes → code → evidence 顺序逐项对照，显式核对 Deviations，检查 exec plan 是否只做执行映射；**必须用 `codegraph_impact` 核对影响面**是否超出 spec/detail 声明范围
    - **编码规范与质量**：C 项目按 `ddev-c-pro` 维度（规范 + 安全 + 架构性能 + 死代码/重复），非 C 项目按语言对应 skill；问题按 CRITICAL/HIGH/MEDIUM/LOW 分级
    - **注释完整性**：C 项目按 `ddev-comment-gen` 维度逐文件核对；其他语言按对应注释审查 skill，无则跳过
    - 输出一份结论 `pass` / `need-info` / `blocked`，附差异归类、问题清单、缺失注释清单
C4. **跳过 `ddev-clean`**。整合审查发现的低危可清理项（MEDIUM/LOW）直接列入问题清单不阻塞；主 agent 决定是否顺手清理，若清理改了代码，补验证证据后回到 C3 重审。
C5. `blocked` → 主 agent 按清单修改，重新进入本 skill，从 C1 重跑 Compact 路线（不升级为 Streaming）。
C6. `need-info` → 补齐缺失输入 / 范围 / 验证证据后从 C3 重跑。
C7. `pass` → 满足「结论规则」中 compact 条件后，主 agent 才能宣称"已经按计划完成"。

Compact 路线同样要求 spec、detail、代码范围、验证证据齐全，缺任何一项都不能给 `pass`。

## 审查 agent 要求

- 必须是独立视角，不能把主 agent 自己的口头总结当结论
- 必须显式核对 spec、detail、exec plan、implementation-notes、code、evidence 这六类输入
- 必须显式核对 Deviations 条目，逐条验收偏离是否已被文档接受或有合理理由
- 必须显式核对 exec plan 是否只是执行映射，还是偷偷承担了新的设计决策
- 必须把 data flow、flow、结构体设计与代码逐项对上
- **必须使用 `codegraph_impact` 评估改动影响面**：对关键符号做影响半径分析，确认实际影响范围与 spec/detail 声明的范围一致；若存在文档未声明的受影响模块，视为偏离
- 发现任何未批准差异时，必须返回 `blocked`
- 不允许用”基本一致””差不多符合””核心没问题”这类模糊表述放行
- 如果本轮代码已经过 `ddev-clean` 清理，必须按**清理后的最终代码**重做对照，不能沿用清理前结论

审查提示模板见 [streaming-reviewer-prompt.md](streaming-reviewer-prompt.md)。

## 代码规范与质量审查 agent 要求（C 项目）

- 必须是独立视角，不能复用一致性验收 agent 的结论
- 必须加载 `ddev-c-pro` skill，统一完成编码规范审查和代码质量审查（已吸收 `ddev-code-review` 的 C 相关职责）
- C 项目不再单独调用 `ddev-code-review`
- **必须使用 `codegraph_impact` 评估改动影响面**：确认审查范围内外的符号依赖，避免遗漏受影响的文件
- 审查维度：
  - **编码规范**：全局变量是否必要、参数是否过多未封装、命名是否遵循模块前缀规范、错误处理是否用显式返回码、内存 ownership 是否明确
  - **代码质量（安全）**：硬编码凭据、缓冲区溢出、注入风险、路径遍历、整数溢出、敏感数据泄露
  - **代码质量（架构性能）**：跨模块 N+1 模式、不合理算法选择、不必要的重复内存分配
  - **代码质量（死代码/重复）**：未被调用的符号、不可达分支、跨文件 DRY 违规
- 对问题按严重程度分级：CRITICAL（安全漏洞/崩溃）> HIGH（Bug/严重异味）> MEDIUM（技术债）> LOW（建议）
- 存在 CRITICAL 或 HIGH 问题 → `blocked`。仅 MEDIUM/LOW → `pass`（在建议项中列出）
- 不允许用"基本规范""大体符合"等模糊表述放行
- 如果本轮代码已经是审查修改后的代码，必须基于最终版本重新审查，不能沿用前次结论

c-pro 审查提示模板见 [reviewer-prompt.md](../ddev-c-pro/reviewer-prompt.md)。

> **非 C 项目**：先调用 `ddev-code-review` 做代码质量审查，再按语言调用编码规范审查 skill。无对应编码规范审查 skill 则跳过，在验收结论中注明。

## 注释/文档审查 agent 要求（C 项目）

- 必须是独立视角，不能复用编码规范审查 agent 的结论
- 必须加载 `ddev-comment-gen` skill，按其中定义的审查维度逐文件、逐函数、逐结构体验证注释完整性
- **必须使用 `codegraph_impact` 评估改动影响面**：确认所有目标文件的公开 API、结构体、枚举均已纳入审查
- 重点检查：文件头 @file 注释、公开函数 Doxygen 完整性、结构体/枚举成员行内注释、关键逻辑说明注释、注释与代码行为一致性、注释语言（必须中文）
- 只审查注释规范层面，不重复做编码规范或架构一致性判断
- 发现缺失或不足必须返回 `blocked`，并附带逐项缺失清单和补全建议文本
- 不允许用"基本齐全""大体符合"等模糊表述放行

comment-gen 审查提示模板见 [reviewer-prompt.md](../ddev-comment-gen/reviewer-prompt.md)。

> **非 C 项目**：如果没有对应的注释审查 skill，合理跳过本阶段。在验收结论中注明"本语言暂无注释审查 skill，已跳过"。

## ddev-clean 清理 agent 要求

- 必须是独立视角，在自己的受限范围内工作
- 必须加载 `ddev-clean` skill，遵守 regression-tests-first、显式 cleanup plan、最小 diff、最小作用域规则
- **必须使用 `codegraph_impact` 评估清理影响面**：在删除/重命名符号前，确认没有外部调用方；清理操作不得波及范围外代码
- 清理范围默认继承一致性验收的范围，如果能拿到更窄 changed-files 列表则进一步收敛
- 如果清理产生代码修改，主 agent 必须补验证证据并重新进入一致性验收
- 如果清理没有代码修改，直接保留一致性验收结论

cleaner 提示模板见 [reviewer-prompt.md](../ddev-clean/reviewer-prompt.md)。

## ddev-code-review 代码审查 agent 要求

- 必须是独立视角，不能复用一致性验收或清理 agent 的结论
- 必须加载 `ddev-code-review` skill，按 4 阶段流程执行：识别变更 → codegraph 结构影响分析 → 深度审查 → 结构化报告
- **必须使用 `codegraph_impact` 评估改动影响面**：确认变更波及半径，交叉验证调用链
- 审查维度：安全（硬编码凭据、注入风险）、代码质量（函数长度、复杂度、DRY）、性能（N+1、算法复杂度）、最佳实践（错误处理、日志、测试）、可维护性（耦合度、硬编码配置）
- 输出结论：`APPROVE` / `REQUEST CHANGES` / `COMMENT`，`REQUEST CHANGES`（CRITICAL/HIGH 问题）视为 `blocked`
- 不允许跨入编码规范审查领域（命名、风格、注释交由后续 ddev-c-pro / ddev-comment-gen 负责）

code-reviewer 提示模板见 [reviewer-prompt.md](../ddev-code-review/code-reviewer.md)。

## Compact 整合审查 agent 要求

（compact 路线专用；Streaming 路线使用上方各阶段独立 agent）

- 必须是独立视角，不能复用主 agent 的口头总结
- **一次性完成三个维度的审查**，输出一份结论：
  1. **一致性**：显式核对 spec、detail、exec plan、implementation-notes、code、evidence 六类输入；逐条核对 Deviations；检查 exec plan 是否只做执行映射；**必须使用 `codegraph_impact` 评估影响面**，影响面超出 spec/detail 声明范围视为偏离
  2. **编码规范与质量**：C 项目按 `ddev-c-pro` 维度（规范、安全、架构性能、死代码/重复），非 C 项目按语言对应 skill；问题按 CRITICAL/HIGH/MEDIUM/LOW 分级，存在 CRITICAL/HIGH → `blocked`
  3. **注释完整性**：C 项目按 `ddev-comment-gen` 维度逐文件核对，缺失 → `blocked` 并附缺失清单；其他语言无对应 skill 则跳过
- 结论只允许 `pass` / `need-info` / `blocked`
- 不允许用"基本一致""大体符合"等模糊表述放行
- 如果代码经过主 agent 修复后重审，必须基于最终版本重新审查，不能沿用前次结论

compact 整合审查提示模板见 [compact-reviewer-prompt.md](compact-reviewer-prompt.md)。

## 重点检查项

默认重点检查：

- 模块边界是否与 spec 文档一致
- 接口位置、调用方向、接入点是否与 spec 设计一致
- 结构体是否与 detail 文档定义一致
- 数据流、状态流、错误流是否与 detail 文档一致
- exec plan 是否正确引用了 spec / detail / flow / dataflow 文档，而不是脱离这些文档自定义约束
- exec plan 中的任务、文件范围和验证动作，是否都能追溯到已确认设计
- 关键分支是否按设计落地，而不是实现时擅自改成别的结构
- 是否新增了文档未说明的共享可变状态
- 是否出现文档未允许的业务全局变量
- 是否把本应拆分的职责重新塞回大函数
- 是否出现未在设计中说明的长链 `if/else`

对于 C 项目，代码规范审查由 `ddev-c-pro` skill 专门负责，注释审查由 `ddev-comment-gen` skill 专门负责，此处一致性验收不重复做风格/注释/命名审查。对于非 C 项目，编码规范和注释审查按对应语言的 skill 路由（如无对应 skill 则跳过）。

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

compact 路线同样只允许这三种结论，且三合一整合审查一次性覆盖一致性、编码规范与质量、注释三个维度，无需分段输出。

### `pass`

只有在以下条件同时满足时才能给：

- 已找到并核对 spec 文档
- 已找到并核对 detail 文档
- 已明确本轮验收对应的代码范围
- 若存在 exec plan，则已确认它正确引用并传递了上游设计约束，没有在计划阶段引入新的未批准设计
- 代码实现与设计一致，或偏离已被明确接受并补充到文档
- 代码实现与 exec plan 一致，关键步骤没有漏做、错做或擅自改做
- 本轮存在新的验证证据，且证据与结论匹配
- 未覆盖风险已明确说明
- task_plan.md 存在且所有 checkbox 已完成、所有错误已解决、check-complete 验证通过，且 `implementation-notes.md` 中 Open Questions 已全部回答完毕
- 若经历过 `ddev-clean` 清理，则清理后的最终代码也已重新完成一致性验收
- 代码规范与质量审查已通过（C 项目由 `ddev-c-pro` 统一完成，非 C 项目由 `ddev-code-review` + 语言规范审查完成）
- 若项目为 C 代码（`.c` / `.h`），则 `ddev-comment-gen` 注释审查已通过；若为其他语言，则对应的注释审查已通过或已合理跳过
- **compact 路线**：上述涉及 `ddev-clean`、`ddev-c-pro` / `ddev-code-review`、注释审查的条目，由三合一整合审查一次性覆盖；`ddev-clean` 明确跳过

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
- exec plan 与 spec / detail / flow / dataflow 文档冲突，或 exec plan 自行引入了新的未批准设计
- 实现明显背离设计，且没有文档更新
- 实现明显背离 exec plan
- 实现与 data flow / flow / 结构体设计不一致
- 关键设计约束未落地
- 结论依赖关键证据，但证据不存在
- `ddev-clean` 修改了代码，但清理后的实现还没有重新完成一致性验收
- 代码规范与质量审查 `blocked`，且修改后尚未重新完成完整门禁流程（C 项目为 `ddev-c-pro` 审查 blocked，非 C 项目为 `ddev-code-review` 或语言规范审查 blocked）
- 注释/文档审查 `blocked`，且修改后尚未重新完成完整门禁流程

判定原则：

- 关键设计基线缺失、互相冲突或当前上下文下无法建立时，用 `blocked`
- 在补齐前提之前继续审查没有意义的，用 `blocked`
- 只要需要打回主 agent 改代码或改文档后再审，也用 `blocked`

## 输出格式

最终输出必须包含：

1. 验收结论：`pass` / `need-info` / `blocked`
2. 对照范围：看了哪些 spec / detail / implementation-notes / code / 验证材料
3. 差异归类：文档过时 / 实现偏离设计 / 设计本身不完整 / 证据不足
   - 若 `implementation-notes.md` 中存在 Deviations 条目，必须在差异归类或发现的问题中对每一项偏离给出验收结论（已接受 / 需修正 / 需补文档）
4. 发现的问题：按严重度列出与设计不一致之处
5. 已确认一致的关键点：只列最重要的几项
6. 未覆盖风险：明确还没验证到哪里
7. 如果进入过 `ddev-clean`，要明确说明：清理是否改代码、清理范围是什么、清理后是否已重新验收
8. 代码规范与质量审查结论：是否已审查、审查结果、发现的 CRITICAL/HIGH/MEDIUM/LOW 问题数。C 项目由 `ddev-c-pro` 统一输出此结论；非 C 项目分别列出 `ddev-code-review` 和语言规范审查结论。若 blocked 则附修改项清单。若项目语言无对应审查 skill 则注明"已跳过"
9. 注释/文档审查结论：是否已审查、审查结果、若 blocked 则附缺失项清单；若项目语言无对应审查 skill 则注明"已跳过"

**compact 路线**：上述第 7–9 项合并为一份「整合审查结论」，一次性输出一致性、规范与质量、注释三个维度的结果。

如果没有发现不一致，也不能只说“通过”，仍要说明对照了什么。

如果需求结论依赖真实目标板、外设、时序、功耗、波形或现场观察，而本轮没有对应人工或现场证据，不能给 `pass`。

如果审查结论是 `blocked`，输出里必须明确列出“需要主 agent 修改的项”，这样主 agent 才能按项修复并重新送审。

## 与其他 skill 的关系

- 上游通常来自 `ddev-spec`
- detail 输入通常来自 `ddev-detail`
- 如需补验证证据，联动 `verification-before-completion`
- 如需独立质量复核，联动 `ddev-code-review`（非 C 项目）
- 如需在一致性通过后做垃圾代码清理和可维护性提升，联动 `ddev-clean`
- 如需在清理后做代码规范与质量审查，C 项目联动 `ddev-c-pro`（已吸收代码质量审查），非 C 项目联动 `ddev-code-review` + 对应语言编码规范 skill
- 如需在规范与质量审查通过后做注释完整性和规范性审查，联动对应语言的注释审查 skill（C 项目联动 `ddev-comment-gen`）
- **compact 路线**：小改动不联动 `ddev-clean`，三合一整合审查一次性覆盖一致性 + 规范质量 + 注释；大改动才走上述完整链路
- 默认在 `ddev-exec` 的末尾作为最终收口门禁

### ⚠️ 阶段交接硬门禁

**本 skill 完成后，禁止 agent 自动进入任何后续阶段（ddev-archive / git commit / 发布 / 部署 等）。**

- gate 最终 `pass` 后，向用户报告完整的验收结论（一致性、代码质量、注释审查）。
- 提示用户可选后续操作（如"是否提交代码？""是否进入 ddev-archive 归档？"），但**必须等待用户明确确认**。
- 用户未明确说"提交""归档""发布""推送"等指令前，停留在 gate 结论输出阶段，不自行推进。
- gate 内部的 gate → clean → c-pro/code-review → comment-gen 循环为自动化流程，不受此限制。

## 最低要求

没有 spec 文档、没有 detail 文档、没有代码对照，就不要假装做了最终验收。

验收的重点是**实现是否符合 spec、detail 和 exec plan**，不是只看”代码能不能跑”。

如果进入了 `ddev-clean` 清理阶段，最终放行对象是**清理后的最终代码**，不是清理前那一版代码。

对于 C 代码项目，`ddev-c-pro`（统一完成规范与代码质量审查）和 `ddev-comment-gen` 注释审查是必经环节，两者均通过才能给最终 `pass`。对于其他语言项目，`ddev-code-review` 代码质量审查 + 语言规范审查 + 注释审查按存在情况逐一通过后放行；如无对应 skill，应标注"已跳过"而非静默略过。

**compact 路线**：同样必须有 spec、detail、代码范围、验证证据；三合一整合审查通过（C 项目覆盖 c-pro 与 comment-gen 维度）才能给最终 `pass`，不因改动小而降低底线。
