---
name: ddev-decision-log
description: 标准化决策记录。当用户做出技术方案选择、命名规范决定、工作流调整、策略取舍等决策时自动触发；用户也可手动调用说"记录决策""记下来""记住这个"来触发。被 ddev-spec、ddev-detail、ddev-doc-review、ddev-gate 联动调用落盘到 findings/ 或 daily/。
---

# 决策记录

将用户决策和审查验收结论标准化落盘，分两个目标位置：项目内的 `findings/`（本次改动的设计决策）、全局的 `daily/`（跨项目的用户偏好决策）。

## 触发条件

**自动触发（由 skill-forced-eval 匹配）：**
- 用户说"记录一下""记下来""记住这个""以后都这样"
- 用户做出修改 spec/detail 文档方向的选择
- 用户在工作流中对方案有明确的取舍表达

**手动触发：**
- 用户说"记录决策"
- 用户说"把刚才那个决策记下来"

**被 ddev 工作流联动触发：**
- `ddev-spec`：spec 做方向性修改时、反复改后定版时
- `ddev-detail`：发现结构冲突、数据流约束时
- `ddev-doc-review`：审查完成后
- `ddev-gate`：验收 pass/blocked 时

## 核心流程

1. 识别目标位置：当前项目有 task_plan.md / spec 文档 → `findings/`，否则 → `daily/`
2. 推断阶段子目录和类型标签，向用户一句话确认
3. 按类型选择格式写出文件
4. 若写入 `daily/`，检查是否需要更新 `patterns.md`

## 文件位置

```
findings/                    ← 项目内，某次代码改动的设计决策
├── spec/                   ← ddev-spec 决策
├── detail/                 ← ddev-detail 发现
├── review/                 ← ddev-doc-review 审查结论
└── gate/                   ← ddev-gate 验收结论

~/.config/opencode/daily/   ← 全局，跨项目的用户偏好决策
└── patterns.md             ← 定期总结的用户偏好模式
```

## 标准化格式

### 通用决策格式（spec/detail/daily 使用）

```markdown
# <主题>

> 日期：YYYY-MM-DD | 项目：<project> | 类型：<标签>

## 背景
<为什么会有这个决策，上下文是什么>

## 决策
<做了什么选择，具体内容>

## 原因
<为什么这样选，排除了什么，约束是什么>
```

### 审查报告格式（review/gate 使用）

审查类文件直接写入审查报告原文（含表格），不强制转换为三段式。元数据行标注类型为 `审查` 或 `验收`。

```markdown
# doc-review 审查报告

> 日期：2026-06-22 | 项目：agent-skills-hook | 类型：审查

## 问题清单
...
## 审查结论
通过 / 有条件通过 / 需要修改
```

两种格式并存，根据调用方自动选择。

## 类型标签参考

| 标签 | 适用场景 |
|------|---------|
| `编码规范` | 命名、风格、代码组织 |
| `技术方案` | 架构、库、工具选择 |
| `工作流` | 流程、顺序、触发条件 |
| `设计决策` | spec/detail 阶段的设计取舍 |
| `审查` | ddev-doc-review 审查结论 |
| `验收` | ddev-gate 验收结论 |
| `文档体系` | 文档结构、格式规范 |

## 被联动调用时的接口约定

调用方 Skill 在调用本 skill 时，应明确传递：
- 目标位置：`findings` 或 `daily`
- 子目录：spec / detail / review / gate
- 主题和类型标签
- 内容：决策原文或审查报告

## daily/ 的 patterns.md 自动维护

每次写入 `daily/` 后检查：
- 文件数是否比上次 patterns.md 更新时多了 10+ 条
- 如果是 → 对所有决策做分类汇总，更新 patterns.md

## 辅助脚本

- `scripts/append-findings.sh` — 在 findings/ 下创建决策文件（带时间戳和分类）
- 脚本位于 skill 安装目录下，由本 skill 内部使用

## 约束

- 不管理流程状态，不读/写 task_plan.md
- 只负责决策记录的标准化落盘
- 写入 `findings/` 时确保目录已存在，不存在则先创建
- 文件名格式：`findings/<subdir>/YY-MM-DD_<topic>.md` 或 `daily/YY-MM-DD_<topic>.md`
