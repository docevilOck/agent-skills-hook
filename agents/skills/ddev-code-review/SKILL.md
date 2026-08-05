---
name: ddev-code-review
description: 在 ddev-gate 工作流中执行代码质量审查。使用 codegraph 做结构影响分析，覆盖安全、性能、可维护性，按严重程度分级输出。
---

# ddev-code-review — 代码质量审查

## 作用

ddev-gate 工作流的代码质量审查阶段。使用 codegraph 做结构影响分析，覆盖安全、代码质量、性能、最佳实践和可维护性，按严重程度分级输出报告。

## When to Use

由 `ddev-gate` skill 在清理阶段之后、编码规范审查之前调度。也可独立触发于以下场景：
- 用户请求 "review this code"
- 合并 PR 前
- 完成重要功能后

> **C 项目注意**：`ddev-gate` 工作流中 C 项目不再单独调用本 skill。代码质量审查职责已由 `ddev-c-pro` 吸收（统一完成规范审查 + 代码质量审查）。非 C 项目仍走 `ddev-code-review` + 语言规范审查的分离流程。独立触发（用户直接要求 review）时 C 项目可正常使用。

## Companion Skills

Always load `tool-routing` alongside this skill to ensure correct codegraph/grep dispatch during structural analysis.

## What It Does

Delegates to the `code-reviewer` agent for deep analysis. The agent follows a 4-phase pipeline:

### Phase 1: Identify Changes
- Run `git diff` (or `git diff --staged`) to find changed files and symbols
- Run `git log` to understand recent commit context
- Determine scope: entire diff, specific files, or targeted review

### Phase 2: Structural Impact Analysis (MANDATORY — use codegraph)
Before reading any source file, understand the architecture:

| Step | Tool | Purpose |
|------|------|---------|
| 2a | `codegraph_codegraph_context` | For each changed symbol, get architectural context: entry points, related symbols, key code |
| 2b | `codegraph_codegraph_impact` | Assess change radius — what downstream code could be affected |
| 2c | `codegraph_codegraph_callers` | Trace who calls changed symbols — identify all integration points |
| 2d | `codegraph_codegraph_search` | Find related symbols by name — catch hidden coupling |
| 2e | `codegraph_codegraph_trace` | For data flow changes, trace from entry point to sink |

**Rule**: Never start code-level review without first completing Phase 2. The structural analysis drives scope and reveals hidden risks that grep alone misses.

### Phase 3: Deep Review Categories
- **Security** — Hardcoded secrets, injection risks, XSS, CSRF, auth bypass, path traversal, sensitive data exposure
- **Code Quality** — Function size, complexity, nesting depth, DRY violations, dead code, naming
- **Performance** — N+1 queries, missing caching, O(n²) algorithms, unnecessary allocations, memory leaks
- **Best Practices** — Error handling, logging, API contracts, test coverage, documentation
- **Maintainability** — Coupling (cross-check with codegraph callers graph), cohesion, testability, hardcoded config

### Phase 4: Report
Structured output with severity ratings, file:line evidence, concrete fixes, and approval recommendation.

## Severity Rating

| Severity | Meaning | Action |
|----------|---------|--------|
| **CRITICAL** | Security vulnerability, data loss, crash | Must fix before merge |
| **HIGH** | Bug, major code smell, perf regression | Should fix before merge |
| **MEDIUM** | Minor issue, technical debt | Fix when possible |
| **LOW** | Style, nitpick, suggestion | Consider fixing |

## Agent Delegation

Dispatch to the `code-reviewer` agent with a prompt covering all 4 phases:

```markdown
CODE REVIEW TASK

Scope: [files changed from git diff, or specific files/dirs]

PHASE 1 — Identify: Run git diff, list changed files and symbols.
PHASE 2 — Structural Analysis (MANDATORY): For each changed symbol, use:
  - codegraph_codegraph_context to understand architecture
  - codegraph_codegraph_impact to assess change radius
  - codegraph_codegraph_callers to find integration points
  - codegraph_codegraph_trace for data flow paths
PHASE 3 — Deep Review: Check security, quality, performance, best practices, maintainability.
PHASE 4 — Report: Structured output (see Output Format below).
```

## Output Format

Every review MUST end with this exact structure:

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

## Review Checklist

### Security
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs sanitized
- [ ] SQL/NoSQL injection prevention
- [ ] XSS prevention (escaped outputs)
- [ ] CSRF protection on state-changing operations
- [ ] Authentication/authorization properly enforced

### Code Quality
- [ ] Functions < 50 lines (guideline)
- [ ] Cyclomatic complexity < 10
- [ ] No deeply nested code (> 4 levels)
- [ ] No duplicate logic (DRY principle)
- [ ] Clear, descriptive naming
- [ ] **No magic numbers** — 所有非 0/1/-1 的字面量必须定义为命名常量（`#define`/`enum`/`static const`），并在注释中说明取值依据。超时毫秒数、缓冲区大小、重试次数、状态值、寄存器地址等一律不得裸写数字；缓冲区/容量等大数字（≥1024）必须写成 `128 * 1024` / `16 * 1024 * 1024` 这种可读乘法表达式 + 命名常量，禁止直接裸写 `16384`/`4194304` 等大数

### Performance
- [ ] No N+1 query patterns
- [ ] Appropriate caching where applicable
- [ ] Efficient algorithms (avoid O(n²) when O(n) possible)
- [ ] No unnecessary re-renders (React/Vue)

### Best Practices
- [ ] Error handling present and appropriate
- [ ] Logging at appropriate levels
- [ ] Documentation for public APIs
- [ ] Tests for critical paths
- [ ] No commented-out code

## Approval Criteria

**APPROVE** — No CRITICAL or HIGH issues, minor improvements only
**REQUEST CHANGES** — CRITICAL or HIGH issues present
**COMMENT** — Only LOW/MEDIUM issues, no blocking concerns

## Best Practices

- **Review early** — Catch issues before they compound
- **Review often** — Small, frequent reviews better than huge ones
- **Address CRITICAL/HIGH first** — Fix security and bugs immediately
- **Consider context** — Some "issues" may be intentional trade-offs
- **Learn from reviews** — Use feedback to improve coding practices
