# 小改动 compact 整合审查任务

你的任务是做一次**三合一整合审查**，范围限定为本次小改动。你一次性完成一致性验收、编码规范与质量审查、注释完整性审查三个维度，输出一份结论。

这是 compact 路线：改动面小，不再分四段流式审查。但审查标准与 streaming 路线各阶段一致，不能因为"改动小"而放水。

## 审查要求

你必须逐项核对：

1. spec 文档
2. implementation struct / dataflow / flow detail 文档
3. 执行计划（exec plan）——视为上游 design 文档的执行映射，不是独立设计真源
4. 当前实现代码范围
5. 本轮验证证据
6. `implementation-notes.md`（如有）：Deviations → 逐条验收；Design Decisions → 作为 spec 空白处补充依据；Open Questions → 未回答判 `blocked`

### 维度一：一致性对照

- 先判断 exec plan 是否只是在做执行映射，而不是替上游文档新增设计决策
- 检查实现是否出现文档/计划未批准的偏离
- 检查文档强调的约束是否真的落到代码里
- **先用 code-review-graph 看影响面与需审查文件，`grep` 兜底**：
  - 影响哪些调用方（call sites）
  - 波及范围是否与 spec/detail 声明范围一致
  - 是否存在文档未声明的受影响模块（存在 → `blocked`）
- 结构体、数据流、流程与代码逐项对上

### 维度二：编码规范与质量

- C 项目按 `ddev-c-pro` 维度审查：编码规范（全局变量、参数封装、命名、错误处理、内存 ownership）、安全（缓冲区溢出、注入、硬编码凭据、整数溢出）、架构性能（N+1、算法复杂度、重复分配）、死代码/重复
- 非 C 项目按语言对应编码规范 skill 审查，无则跳过
- 问题按 CRITICAL / HIGH / MEDIUM / LOW 分级

### 维度三：注释完整性

- C 项目按 `ddev-comment-gen` 维度逐文件核对：文件头 @file、公开函数 Doxygen、结构体/枚举成员行内注释、关键逻辑说明注释、注释与代码行为一致性、注释语言（必须中文）
- 其他语言无对应注释审查 skill 则跳过，注明"已跳过"

## 结论规则

只输出三种结论之一：

- `pass`：三个维度均无 CRITICAL/HIGH 问题、无注释缺失、无未批准偏离，且存在本轮验证证据
- `need-info`：缺少必要输入或证据，补齐后仍可继续
- `blocked`：一致性发现未批准偏离，或存在 CRITICAL/HIGH 问题，或注释缺失需要补

不允许用"基本一致""大体符合"等模糊表述放行。

## 输出格式

结论：`pass|need-info|blocked`

对照范围：
- architecture / detail / exec plan / code / evidence / implementation-notes：...

差异归类：
- 文档过时 / exec plan 未正确传递设计 / exec plan 引入新设计 / 实现偏离设计 / 实现偏离 exec plan / 设计本身不完整 / 证据不足

发现的问题：
1. [严重度] ...

编码规范与质量结论：
- 问题分级汇总（CRITICAL/HIGH/MEDIUM/LOW 各几条）

注释完整性结论：
- 是否核对、缺失项清单（如有）

已确认一致的关键点：
- ...

需要主 agent 修改的项：
- ...

影响面评估：
- 关键符号：[本次改动涉及的关键函数/结构体]
- code-review-graph 影响面分析：[影响半径、调用方数量、是否超出 spec/detail 声明范围]
- 遗漏文件（如有）：[code-review-graph 查出、`grep` 兜底发现但不在审查范围内的受影响文件]

未覆盖风险：
- ...

下一步：
- `blocked` → 明确写"主 agent 必须先修改这些项，再重新进入 ddev-gate compact 路线"
- `need-info` → 明确写要补什么
