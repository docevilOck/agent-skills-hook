---
name: requesting-code-review
description: 在完成任务、实现重要功能或准备合并前使用，用来确认工作满足要求
---

# 请求代码审查

派发 `superpowers:code-reviewer` 子代理，在问题扩散前抓住它们。审查者会拿到专门构造的评估上下文，而不是你的会话历史。这样能让审查者专注于产出本身，而不是你的思考过程，同时也保留你自己的上下文供后续工作使用。

**核心原则：** 尽早审查，频繁审查。

## 何时请求审查

**必须：**
- 在 `executing-plans` 中，每完成 2-3 个任务或一个里程碑都要审查
- 完成一个主要功能后审查
- 合并到 main 之前审查

**可选但很有价值：**
- 卡住时审查（换个视角）
- 重构前审查（先看基线）
- 修复复杂 bug 之后审查

## 如何请求

**1. 获取 git SHA：**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. 派发 code-reviewer 子代理：**

使用 Task 工具，类型选 `superpowers:code-reviewer`，并填写 `code-reviewer.md` 里的模板

**占位符：**
- `{WHAT_WAS_IMPLEMENTED}` - 你刚完成了什么
- `{PLAN_OR_REQUIREMENTS}` - 它应该实现什么
- `{BASE_SHA}` - 起始提交
- `{HEAD_SHA}` - 结束提交
- `{DESCRIPTION}` - 简短摘要

**3. 处理反馈：**
- 立刻修复 Critical 问题
- 在继续之前修复 Important 问题
- Minor 问题先记下来，后面再处理
- 如果审查者错了，就用理由反驳

## 示例

```
[刚完成任务 2：添加验证函数]

你：我先请求代码审查，再继续。

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[派发 superpowers:code-reviewer 子代理]
  WHAT_WAS_IMPLEMENTED: 会话索引的验证和修复函数
  PLAN_OR_REQUIREMENTS: `docs/superpowers/plans/deployment-plan.md` 中的任务 2
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
  DESCRIPTION: 新增 `verifyIndex()` 和 `repairIndex()`，覆盖 4 类问题

[子代理返回]：
  Strengths: 架构清晰，使用了真实测试
  Issues:
    Important: 缺少进度提示
    Minor: 上报间隔用了魔法数字（100）
  Assessment: 可以继续

你：[修复进度提示]
[继续任务 3]
```

## 与工作流集成

**Subagent-Driven Development:**
- 每个任务完成后都要审查
- 在问题叠加之前抓住它们
- 修完再进入下一任务

**Executing Plans:**
- 每个批次（3 个任务）后审查
- 拿到反馈后先应用，再继续

**Ad-Hoc Development:**
- 合并前审查
- 卡住时审查

## 红旗信号

**永远不要：**
- 因为“很简单”就跳过审查
- 忽略 Critical 问题
- 带着未修的 Important 问题继续
- 和正确的技术反馈争辩

**如果审查者错了：**
- 用技术理由反驳
- 展示能证明它工作的代码或测试
- 请求澄清

模板见：`requesting-code-review/code-reviewer.md`
