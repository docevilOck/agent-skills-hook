---
name: ddev-clean
description: Run an anti-slop cleanup/refactor/deslop workflow
---

# AI Slop Cleaner Skill

Reduce AI-generated slop with a regression-tests-first, smell-by-smell cleanup workflow that preserves behavior and raises signal quality.

## When to Use

Use this skill when:
- A code path works but feels bloated, noisy, repetitive, or over-abstracted
- A user asks to “cleanup”, “refactor”, or “deslop” AI-generated output
- Follow-up implementation left duplicate code, dead code, weak boundaries, missing tests, or unnecessary wrapper layers
- You need a disciplined cleanup workflow without broad rewrites

## GPT-5.4 Guidance Alignment

- Keep outputs concise and evidence-dense unless risk or the user requests more detail.
- Treat newer user instructions as local workflow updates without discarding earlier non-conflicting constraints.
- Keep using inspection, tests, diagnostics, and verification until the cleanup is grounded.
- Proceed automatically through clear, reversible cleanup steps; ask only when a choice materially changes scope or behavior.

## Scoped File Lists and Ralph Workflow

- This skill can accept a **file list scope** instead of a whole feature area.
- When the caller provides a changed-files list (for example, Ralph session-owned edits), keep the cleanup strictly bounded to those files.
- In the **Ralph workflow**, the mandatory deslop pass should run this skill on Ralph's changed files only, in standard mode unless the caller explicitly requests otherwise.

## 与 ddev-gate 的关系

- `ddev-clean` 不再是 ddev-gate 的独立流水线阶段；**清理项识别**已并入 gate 的代码评审 subagent（只出清单，只读）。
- **清理执行**由主 agent 在收到代码评审结论后按需进行：加载本 skill 直接执行，或派发受限清理 subagent。范围是代码评审给定的 changed-files 或更窄的文件列表。
- 只有在完成编码规范 / 质量 / 注释审查结论之后才执行清理，避免边审边改。
- 目标是在**不改变**文档已批准的架构、detail、数据流、接口和行为的前提下，删除 slop 并提升可维护性。
- 如果为锁定行为必须补测试，只允许纳入锁定既有行为所必需的最小测试文件，不得借此扩大实现范围。
- 清理产生任何代码修改后，必须补充验证证据；主 agent 必须基于最终代码重新并行派发一致性审查与代码评审做只读复审。
- 如果维护性问题真正需要架构或流程变更才能解决，停止并上报，不要借 cleanup 做重构。

## Procedure

1. **Lock behavior with regression tests first**
   - Identify the behavior that must not change
   - Add or run targeted regression tests before editing cleanup candidates
   - If behavior is currently untested, create the narrowest test coverage needed first

2. **Create a cleanup plan before code**
   - List the specific smells to remove
   - Bound the pass to the requested files/scope
   - If a file list scope is provided, keep the pass restricted to that changed-files list
   - Order fixes from safest/highest-signal to riskiest
   - Do not start coding until the cleanup plan is explicit

3. **Categorize issues before editing**
   - **Duplication** — repeated logic, copy-paste branches, redundant helpers
   - **Dead code** — unused code, unreachable branches, stale flags, debug leftovers
   - **Needless abstraction** — pass-through wrappers, speculative indirection, single-use helper layers
   - **Boundary violations** — hidden coupling, leaky responsibilities, wrong-layer imports or side effects
   - **Missing tests** — behavior not locked, weak regression coverage, gaps around edge cases

4. **Execute passes one smell at a time**
   - **Pass 1: Dead code deletion**
   - **Pass 2: Duplicate removal**
   - **Pass 3: Naming/error handling cleanup**
   - **Pass 4: Test reinforcement**
   - Re-run targeted verification after each pass
   - Avoid bundling unrelated refactors into the same edit set

5. **Run quality gates**
   - Regression tests stay green
   - Lint passes
   - Typecheck passes
   - Relevant unit/integration tests pass
   - Static/security scan passes when available
   - Diff stays minimal and scoped
   - No new abstractions or dependencies unless explicitly required

6. **Finish with an evidence-dense report**
   - Changed files
   - Simplifications made
   - Tests/diagnostics/build checks run
   - Remaining risks
   - Residual follow-ups or consciously deferred cleanup

## Output Format

```text
AI SLOP CLEANUP REPORT
======================

Scope: [files or feature area]
Behavior Lock: [targeted regression tests added/run]
Cleanup Plan: [bounded smells and order]

Passes Completed:
1. Pass 1: Dead code deletion - [concise fix]
2. Pass 2: Duplicate removal - [concise fix]
3. Pass 3: Naming/error handling cleanup - [concise fix]
4. Pass 4: Test reinforcement - [concise fix]

Quality Gates:
- Regression tests: PASS/FAIL
- Lint: PASS/FAIL
- Typecheck: PASS/FAIL
- Tests: PASS/FAIL
- Static/security scan: PASS/FAIL or N/A

Changed Files:
- [path] - [simplification]

Remaining Risks:
- [none or short deferred item]
```

## Scenario Examples

**Good:** The user says `continue` after tests already lock behavior and the next smell pass is clear. Continue with the next bounded cleanup pass.

**Good:** The user narrows the scope to a specific file after planning. Keep the regression-tests-first workflow, but apply the new scope locally.

**Bad:** Start rewriting architecture before protecting behavior with tests.

**Bad:** Collapse multiple smell categories into one large refactor with no intermediate verification.

## Gate 审查模式

当本 skill 被 ddev-gate 流程在代码评审返回后加载时，必须使用 `reviewer-prompt.md` 作为任务模板执行受限清理。该模板定义了清理输入、scope 约束、regression-tests-first 规则和输出格式。清理完成后，主 agent 会基于最终代码重新并行派发一致性审查与代码评审做只读复审。

## 进度记录

当本 skill 被 ddev-exec 或 ddev-gate 工作流调用时，清理完成后须将 diff 摘要写入项目根目录的 `progress.md`：

- 记录清理前后的变更文件数和行数（新增/删除）
- 记录各 Pass 通过的 Quality Gates 结果（PASS/FAIL）
- 如有 defer 的风险项，一并记录
- 写到最后一次执行日志后，追加时间戳
