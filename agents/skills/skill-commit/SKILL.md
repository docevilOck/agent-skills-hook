---
name: skill-commit
description: 全局 skill 提交规范。告知 AI 全局 skills 目录是符号链接，实际 git 仓库在何处，以及如何正确提交推送。触发词：skill 提交、提交 skill、skill commit、全局 skill、推送 skill、commit skill。
---

# skill-commit — 全局 Skill 提交规范

## 部署架构

全局 skills 目录通过**两层符号链接**指向实际的 git 仓库：

```
~/.claude/skills/          → ~/.config/opencode/skills/    (第一层)
                             → ~/code/agent-skills-hook/agents/skills/  (第二层, 实际路径)
```

| 路径 | 说明 |
|------|------|
| `~/.claude/skills/` | Claude Code 读取 skills 的入口，**符号链接，不是 git 仓库** |
| `~/.config/opencode/skills/` | OpenCode 中间层，**也是符号链接** |
| `~/code/agent-skills-hook/` | **实际的 git 仓库根目录**，skills 在 `agents/skills/` 子目录下 |

> ⚠️ 在 `~/.claude/skills/` 或 `~/.config/opencode/skills/` 下执行 git 命令会失败或操作错误的仓库，必须去实际路径操作。

## 仓库信息

| 项目 | 值 |
|------|-----|
| 实际路径 | `~/code/agent-skills-hook/` |
| 远程仓库 | `git@github.com:docevilOck/agent-skills-hook.git` |
| 分支 | `main` |
| Skills 目录 | `agents/skills/` |

## 提交流程

### 1. 创建/修改 skill 文件

直接在 `~/.claude/skills/<skill-name>/` 下操作即可（符号链接会透传到实际路径）：

```bash
# 创建新 skill
mkdir -p ~/.claude/skills/<skill-name>
# 编辑 SKILL.md
vim ~/.claude/skills/<skill-name>/SKILL.md
```

### 2. 到实际仓库提交

```bash
cd ~/code/agent-skills-hook

# 确认改动
git status

# 暂存 skill 目录（路径相对于仓库根）
git add agents/skills/<skill-name>/

# 提交（使用 Conventional Commits 格式，这是通用仓库）
git commit -m "feat(<skill-name>): <简短描述>"
```

### 3. 推送

```bash
git push origin main
```

## 完整示例

```bash
# 创建 skill 文件
mkdir -p ~/.claude/skills/my-new-skill
cat > ~/.claude/skills/my-new-skill/SKILL.md << 'EOF'
---
name: my-new-skill
description: 示例技能
---
# my-new-skill
...
EOF

# 提交并推送
cd ~/code/agent-skills-hook
git add agents/skills/my-new-skill/
git commit -m "feat(my-new-skill): 新增示例技能"
git push origin main
```

## 常见错误

| 错误操作 | 正确操作 |
|---------|---------|
| `cd ~/.claude/skills && git add ...` | `cd ~/code/agent-skills-hook && git add agents/skills/...` |
| `git commit -m "[CHG]..."` (V85X 格式) | 普通 Conventional Commits 格式 |
| 在 `.claude/skills/` 下 `git push` | 实际路径 `~/code/agent-skills-hook/` 下 push |
| 路径写 `skills/<name>/` | 路径写 `agents/skills/<name>/`（仓库内相对路径） |

## 注意事项

- 此仓库为通用仓库，**不使用 V85X 的 `[TYPE][SCOPE][PRODUCT]` 格式**，用标准 Conventional Commits
- 修改已有 skill 时，确认改动在 `git status` 中显示为 `agents/skills/<skill-name>/SKILL.md`
- 仓库中还有 `config/` 等其他目录，只提交 `agents/skills/` 下的 skill 相关改动
