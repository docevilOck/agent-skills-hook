---
name: ddev-code-review
description: 在 ddev-gate 工作流中执行代码质量审查。覆盖安全、性能、可维护性，按严重程度分级输出。
---

# ddev-code-review — 代码质量审查

## 作用

ddev-gate 工作流的代码质量审查阶段。覆盖安全、代码质量、性能、最佳实践和可维护性，按严重程度分级输出报告。

## 使用时机

由 `ddev-gate` skill 在清理阶段之后、编码规范审查之前调度。也可独立触发于以下场景：
- 用户请求 "review this code"
- 合并 PR 前
- 完成重要功能后

> **C 项目注意**：`ddev-gate` 工作流中 C 项目不再单独调用本 skill。代码质量审查职责已由 `ddev-c-pro` 吸收（统一完成规范审查 + 代码质量审查）。非 C 项目仍走 `ddev-code-review` + 语言规范审查的分离流程。独立触发（用户直接要求 review）时 C 项目可正常使用。

## 配套技能

结构影响分析必须以 `code-review-graph` MCP 为主力。开始审查前先确认仓库根已生成 `.code-review-graph/`（无则先 `code-review-graph build`）。`mcp__crg__*` 工具不可用时才回退到 `grep`/`read`。

## 工作方式

将深度分析委派给 `code-reviewer` agent。该 agent 按下面的 4 阶段流水线执行：

### 阶段 1：识别变更
- 运行 `git diff`（或 `git diff --staged`）找出变更文件与符号
- 运行 `git log` 理解近期提交背景
- 确定范围：整份 diff、指定文件，或定向审查

### 阶段 2：用 code-review-graph 做结构影响分析（强制，且最先做）
在读取任何源码文件之前，先用 code-review-graph 确立影响面和需要审查的文件。code-review-graph 是主力工具；`grep`/`read` 仅作兜底。

| 步骤 | 工具 | 用途 |
|------|------|------|
| 2.0 | `mcp__crg__get_minimal_context_tool` | 任务入口：~100 tokens，返回风险分 + 相关 communities/flows + 建议的下一步工具 |
| 2.1 | `mcp__crg__query_graph_tool`（`callers_of`/`callees_of`/`references_to`/`imports_of`） | 追改动的波及半径——谁调它 / 它调谁 / 谁引用它 |
| 2.2 | `mcp__crg__get_review_context_tool` | 影响半径 + 需审查的文件清单 + 相关源码片段 + 审查指引 |
| 2.3 | `grep` | 兜底/细化：定位图中未覆盖的定义与调用点 |
| 2.4 | `Read` | 读包围函数/结构体和数据流路径 |

**规则**：未先用 code-review-graph 确立影响面之前，禁止开始逐文件代码审查。图驱动审查范围，揭示浅层 grep 漏掉的隐藏风险。若图缺失（`status: not_ready`），先跑 `code-review-graph build`；仅当确实无图时才回退 grep。

### 阶段 3：深度审查类别
- **安全（Security）** —— 硬编码凭据、注入风险、XSS、CSRF、权限绕过、路径遍历、敏感数据泄露
- **代码质量（Code Quality）** —— 函数规模、复杂度、嵌套深度、DRY 违规、死代码、命名
- **性能（Performance）** —— N+1 查询、缺少缓存、O(n²) 算法、不必要的分配、内存泄漏
- **最佳实践（Best Practices）** —— 错误处理、日志、API 契约、测试覆盖、文档
- **可维护性（Maintainability）** —— 耦合（用 grep 调用点搜索交叉核对）、内聚、可测试性、硬编码配置

### 阶段 4：报告
带严重程度分级的结构化输出，含 file:line 证据、具体修复建议与是否批准的建议。

## 严重程度分级

| 严重级别 | 含义 | 处置 |
|----------|------|------|
| **CRITICAL** | 安全漏洞、数据丢失、崩溃 | 合并前必须修复 |
| **HIGH** | Bug、严重代码异味、性能回退 | 合并前应当修复 |
| **MEDIUM** | 小问题、技术债 | 尽量修复 |
| **LOW** | 风格、吹毛求疵、建议 | 酌情考虑修复 |

## 委派给 code-reviewer agent

把覆盖全部 4 个阶段的提示词发给 `code-reviewer` agent：

```markdown
CODE REVIEW TASK

Scope: [files changed from git diff, or specific files/dirs]

PHASE 1 — Identify: Run git diff, list changed files and symbols.
PHASE 2 — Structural Impact Analysis (MANDATORY, FIRST): Before reading any source, use code-review-graph:
  - mcp__crg__get_minimal_context_tool — task entry (risk, communities/flows, suggested tools)
  - mcp__crg__query_graph_tool — callers_of / callees_of / references_to to assess change radius
  - mcp__crg__get_review_context_tool — impact radius + affected files + source snippets
  - Fall back to grep / Read only when the graph is unavailable (missing .code-review-graph/).
PHASE 3 — Deep Review: Check security, quality, performance, best practices, maintainability.
PHASE 4 — Report: Structured output (see Output Format below).
```

## 输出格式

每次审查必须以如下结构结尾：

```
CODE REVIEW REPORT
==================

Files Reviewed: <N>
Total Issues: <N>

CRITICAL (<N>)
--------------
<#> file:line
   Issue: <description>
   Risk: <impact>
   Fix: <concrete solution>

HIGH (<N>)
----------
...

MEDIUM (<N>)
------------
...

LOW (<N>)
---------
...

RECOMMENDATION: APPROVE | REQUEST CHANGES | COMMENT
```

## 审查清单

### 安全
- [ ] 无硬编码凭据（API key、密码、token）
- [ ] 所有用户输入均已清洗
- [ ] SQL/NoSQL 注入防护
- [ ] XSS 防护（输出已转义）
- [ ] 状态变更操作已做 CSRF 防护
- [ ] 认证/授权已正确执行

### 代码质量
- [ ] 函数 < 50 行（参考值）
- [ ] 圈复杂度 < 10
- [ ] 无深度嵌套（> 4 层）
- [ ] 无重复逻辑（DRY 原则）
- [ ] 命名清晰、有描述性
- [ ] **无魔法数字** —— 所有非 0/1/-1 的字面量必须定义为命名常量（`#define`/`enum`/`static const`），并在注释中说明取值依据。超时毫秒数、缓冲区大小、重试次数、状态值、寄存器地址等一律不得裸写数字；缓冲区/容量等大数字（≥1024）必须写成 `128 * 1024` / `16 * 1024 * 1024` 这种可读乘法表达式 + 命名常量，禁止直接裸写 `16384`/`4194304` 等大数

### 性能
- [ ] 无 N+1 查询模式
- [ ] 适用处已加缓存
- [ ] 算法高效（能用 O(n) 时避免 O(n²)）
- [ ] 无多余重渲染（React/Vue）

### 最佳实践
- [ ] 错误处理存在且恰当
- [ ] 日志级别适当
- [ ] 公开 API 有文档
- [ ] 关键路径有测试
- [ ] 无注释掉的代码

## 批准标准

**APPROVE** —— 无 CRITICAL 或 HIGH 问题，仅有小改进
**REQUEST CHANGES** —— 存在 CRITICAL 或 HIGH 问题
**COMMENT** —— 仅 LOW/MEDIUM 问题，无阻塞性顾虑

## 最佳实践

- **尽早审查** —— 在问题叠加前就抓住
- **经常审查** —— 小批量、高频的审查优于一次性大审查
- **先处理 CRITICAL/HIGH** —— 立即修复安全问题和 bug
- **考虑上下文** —— 有些"问题"可能是刻意的取舍
- **从审查中学习** —— 用反馈改进编码习惯
