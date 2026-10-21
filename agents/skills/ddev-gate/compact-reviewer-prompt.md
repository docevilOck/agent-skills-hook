# 小改动 compact 整合审查任务

> **你的身份**：你是主 agent 派发的**独立只读审查 subagent**，不是主 agent。
>
> **你禁止**：① 修改、新建、删除任何文件（含 `spec/`、`progress.md`、`implementation-notes.md` 等计划文档）；② 调用 subagent 派发工具或自行派生审查；③ 替主 agent 决定修复、重跑审查、提交或归档；④ 自行概括/改写本文件。
>
> 你只做本文件描述的这一项审查，且只回传一份带分级与证据的结论。

> 本模板用于 ddev-gate **compact 路线**。streaming 路线使用两个并行 subagent：[streaming-reviewer-prompt.md](streaming-reviewer-prompt.md)（一致性）+ [code-reviewer-prompt.md](code-reviewer-prompt.md)（代码评审）。

## 任务输入（由派发方填写，已就绪）

| 输入 | 值 |
|------|-----|
| spec 文档 | `[路径]` |
| detail / 架构文档 | `[structures / dataflow / flows / docs/architecture 路径]` |
| 代码范围 | `[changed files / diff]` |
| implementation-notes | `[路径；含 Deviations]` |
| 验证证据 | `[本轮构建 / 测试 / 人工验证结果；标注 repro 或 static]` |
| 改动面清单 | `[gate-scope.yaml 路径；缺失时标 derived]` |
| 机械闸摘要 | `[MECH: M1=.. M2=.. M3=..；命中明细]` |
| 上一轮未闭环 DEV-ID | `[或 无]` |

以下输入由派发方提供；缺失或与代码事实不符时，判 `need-info` 并在结论中指明缺哪一项。

## 输入说明

- 五个输入由主 agent 在上方表格中填写。
- 缺少 spec、detail / 架构文档或代码范围时，直接输出 `need-info` 或 `blocked`，不要退化成泛化 review。
- 本轮为只读整合审查，审查过程中不得修改任何代码。

## 维度一：架构一致性

只核对代码与文档规划的架构是否一致，核对范围：

- 模块边界与职责归属
- 接口位置、接口签名、公开/私有边界
- 调用方向与依赖方向
- 结构体归属、字段所有权、状态所有权
- 数据流与关键流程骨架（入口、转换、出口、状态迁移、错误路径）
- 联动注册点
- 文档明确批准的共享状态与业务全局变量边界

做法：

- **先用 `grep`/`read` 看影响面与需审查文件**：确认影响半径、调用方数量，以及是否超出 spec / detail 声明的范围；存在文档未声明的受影响模块或新增跨模块依赖 → 架构偏离
- **IMPACT 对账（必做）**：`git diff --name-only` + `git status --porcelain` 的实际文件集 vs `gate-scope.yaml` 的 planned_files / callers；反查得到的未声明受影响文件计入 delta；输出 `IMPACT: checked=<n> delta=<n>`，delta>0 不得 `pass`
- 逐项给出“文档要求”与“代码事实”的映射
- 显式核对 `implementation-notes.md` 中的 Deviations：逐条给 `DEV-ID` 与已修正 / 已记录 / 未处理

偏离处置规则：

- 能修正的偏离：给出精确修改建议
- 无法修正或主 agent 已决定不修正的偏离：确认是否已写入 `implementation-notes.md` 的 Deviations（偏离点、理由、影响范围）；已记录 → 视为已接受
- 既未修正、也未记录的偏离 → `blocked`
- 文档没写、属于实现自由度的内容不算偏离；Design Decisions 不能兜底未经批准的架构变更

不检查：exec plan 逐步落地、命名风格、注释格式、测试覆盖——命名/质量/注释在维度二处理，exec plan 只用于确定范围。

## 维度二：行为评审（不是规范扫描）

只报会改变行为的缺陷，按项目语言路由 skill 补充判断依据：

- 安全：硬编码凭据、缓冲区溢出、注入、路径遍历、整数溢出、敏感数据泄露
- 行为：崩溃 / 空指针 / 越界 / OOM 路径 / 返回值未检查 / 错误路径 / 资源泄漏 / 并发竞态 / 未实现 / 逻辑错误
- 假修复对账（复审轮）：主 agent 声明的修复逐条给 已落地 / 未落地 / 无法核对

分级：CRITICAL（安全漏洞/崩溃）> HIGH（Bug）> MEDIUM（技术债）> LOW（建议）。**只有 CRITICAL / HIGH 行为问题阻塞。**

**注释维度**：机械闸 M2 已覆盖的项（`@file`/`@brief`、Doxygen、英文注释、术语泄漏、`#if 0`、冗余 `extern`）不重复列，只写"M2 命中 N 项，已修 x / backlog y"。你只报脚本判不出的**注释与代码行为矛盾**（给矛盾对 + 位置），这是唯一可阻塞的注释项；裁量类注释（成员注释、冗余）不评。

**清理建议**：首轮 / 复审轮不输出；终轮统一给一份 backlog（死代码 / 重复 / 命名不一致 / 魔术数字 / 过长函数 / 冗余注释），标注是否需先补回归测试。

## 结论规则

只输出三种结论之一：

- `pass`：架构一致（或偏离已修正/已记录）、无 CRITICAL/HIGH 行为问题、无注释与代码行为矛盾、`IMPACT delta=0`、本轮有 `repro` 级验证证据
- `need-info`：缺少必要输入 / 证据，或 delta>0 需补审，补齐后仍可继续
- `blocked`：存在未修正且未记录的架构偏离，或存在 CRITICAL/HIGH 行为问题，或注释与代码行为矛盾

不允许用“基本一致”“大体符合”等模糊表述放行。

## 输出格式

第一行必须是机读头（单一 token）：

```
VERDICT: pass | need-info | blocked
SEV: C=<n> H=<n> M=<n> L=<n>
IMPACT: checked=<n> delta=<n>
ROUND: <n>/3
EVIDENCE: repro | static
SCOPE: scope_source=plan|derived

对照范围：
- spec: ...
- detail/架构: ...
- code: ...
- implementation-notes: ...
- evidence: ...

架构偏离清单：

| # | 偏离点 | 文档依据 | 代码事实/位置 | 建议处置 | 状态 |
|---|--------|----------|---------------|----------|------|
| 1 | ... | ... | ... | 修正 / 记录 | 未处理 / 已修正 / 已记录 / 待记录 |

若没有偏离，写“无”。

Deviations 闭环（必填，无则写“无”）：

| DEV-ID | 上轮状态 | 本轮判定 | 依据 |
|---|---|---|---|

代码评审结论：
- 问题分级汇总：CRITICAL N 条 / HIGH N 条 / MEDIUM N 条 / LOW N 条
- 违规项（blocked 时必填）：
  | # | 文件:行号 | 维度 | 严重程度 | 问题描述 | 修改建议 |
  |---|-----------|------|----------|----------|----------|
- 已跳过维度：[...]

注释维度：
- M2 摘要：命中 N 项，已修 x / backlog y
- 语义矛盾（唯一可阻塞项）：[文件:行 + 注释原文 + 代码事实]

终轮 backlog（仅终轮填写；其余轮写“本轮不输出”）：
- [文件:行号] [smell 类型] [建议] [需先补回归测试]

影响面评估：
- 关键符号：...
- 影响面分析（`grep`/`read`）：[影响半径、调用方数量、是否超出文档声明范围]
- 遗漏文件（如有）：...

已确认一致的关键点：
- ...

需要主 agent 修改的项：
- ...

未覆盖风险：
- ...

下一步：
- `blocked` → 明确写“主 agent 必须先修正偏离/问题，再基于最终代码重跑 ddev-gate compact 路线”
- `need-info` → 明确写要补什么
```
