---
name: skill-init
description: 初始化 skill-optimizer 系统 — 将 optimizer-agent 和 gate-agent 部署到平台配置，追加每轮信号记录 checklist 到 AGENTS.md。仅当用户明确说"初始化 skill-optimizer"或"setup skill-optimizer"时使用。必须手动触发，禁止自动调用。
---

# Skill Init — 初始化 Skill Optimizer

一次性部署，将 skill-optimizer 基础设施安装到当前平台。

## 触发条件

用户必须明确说以下之一：
- "初始化 skill-optimizer"
- "setup skill-optimizer"

**本 skill 不可被自动调用或由其他 skill 代理触发，必须由用户主动发起。**

## 平台检测

读取已有配置文件来判断平台：
- `opencode.json`（项目级或全局）→ OpenCode
- `.claude/settings.json` 或 `CLAUDE.md` → Claude Code
- `.codex-plugin/` → Codex

## 步骤

### 第一步：定位 skill-optimizer 模板

根据检测到的平台，读取对应 skills 目录中的 skill-optimizer SKILL.md：

| 平台 | skills 路径 |
|------|------------|
| OpenCode | `~/.config/opencode/skills/skill-optimizer/SKILL.md` |
| Claude Code | `~/.claude/skills/skill-optimizer/SKILL.md` |
| Codex | `~/.codex/skills/skill-optimizer/SKILL.md` |

从中提取子代理定义模板：

```
optimizer-agent: {description（描述）, tools（工具）, model（模型）}
gate-agent: {description（描述）, tools（工具）, model（模型）}
```

### 第二步：部署子代理定义

将子代理定义写入平台对应配置文件：

- **OpenCode**：追加到 `opencode.json` 的 `agent.optimizer-agent` 和 `agent.gate-agent` 下，或在 `.opencode/agents/` 下新建 `optimizer-agent.md` + `gate-agent.md`
- **Claude Code**：在 `.claude/agents/` 下新建 `optimizer-agent.md` + `gate-agent.md`
- **Codex**：在 `.codex-plugin/agents/` 下新建 `optimizer-agent.md` + `gate-agent.md`

默认代理模板（来自 skill-optimizer SKILL.md）：

```json
{
  "optimizer-agent": {
    "description": "Skill optimization agent. Analyzes signal clusters, produces triage output and edit suggestions.",
    "tools": ["Read", "Grep", "Glob"],
    "model": "inherit"
  },
  "gate-agent": {
    "description": "Skill gate judge agent. Evaluates whether skill edits resolve historical signal clusters (parallel per cluster).",
    "tools": ["Read"],
    "model": "inherit"
  }
}
```

### 第三步：读取 checklist 模板

读取平台 skills 目录中的 `skill-recorder/SKILL.md`（路径同第一步），从中定位信号 JSON schema 和 checklist 模板。

### 第四步：追加 checklist 到全局指令

将以下内容保守追加到全局指令文件（AGENTS.md / CLAUDE.md 等）**末尾**，换行后再追加，不修改已有内容。用边界标记包裹：

```markdown
<!-- skill-optimizer block -->
## Skill Signal Recording（每轮信号记录）

每轮响应结束后，检查最新一次 exchange（本轮用户输入 + 我的响应）：
1. 用户是否给出了可执行的具体指导（纠正、指方向、"用 X 方式做"）？
   → 调用 skill-recorder，记 type=corrected
2. 我是否重复同类操作 >= 2 次、用户说了"太慢了"、
   或者我绕过 skill 缺口靠猜测才走通？
   → 调用 skill-recorder，记 type=friction
3. 信号格式：见 skill-recorder SKILL.md 中的 JSON schema
4. skill 归属：回看最近 2-3 轮对话中加载了哪些 skill
   → 一目了然？直接归属。模糊？弹出选项让用户选
5. 以上都没有 → 跳过
<!-- /skill-optimizer block -->
```

### 第五步：报告

输出摘要：
- 检测到的平台：`OpenCode` / `Claude Code` / `Codex`
- 已部署代理：`optimizer-agent` + `gate-agent` → `<路径>`
- checklist 已追加到：`<AGENTS.md 或等价文件路径>`
- 下一步："每轮信号记录已激活。随时说'优化 XX skill'即可触发优化。"

## 约束

- 仅手动触发
- 仅追加到 AGENTS.md，不覆盖已有内容
- 始终用 `<!-- skill-optimizer block -->` 边界标记包裹
- 禁止被其他 skill 自动调用
