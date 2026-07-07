---
name: skill-commit
description: 全局 skill 提交规范。告知 AI 全局 skills 目录通常是符号链接，如何自动定位实际 git 仓库并正确提交推送。触发词：skill 提交、提交 skill、skill commit、全局 skill、推送 skill、commit skill。
---

# skill-commit — 全局 Skill 提交规范

## 核心原则

全局 skills 目录（`~/.claude/skills/`）**通常是符号链接**，指向某个 git 仓库内的子目录。创建/修改 skill 文件可以直接在 `~/.claude/skills/<name>/` 下操作（符号链接透明），但 **git 操作必须去实际仓库根目录执行**。

本 skill 告诉 AI 如何自动发现这些路径，适配任意机器、任意 OS 的部署方式。

## 第一步：自动探测仓库信息

在提交任何 skill 改动前，AI 必须先探测以下信息：

```bash
# 1. 解析 ~/.claude/skills/ 的实际路径（穿透所有符号链接）
#    Linux/macOS: readlink -f 或 realpath
#    Windows Git Bash: 同样支持 readlink -f
SKILLS_REAL=$(readlink -f ~/.claude/skills 2>/dev/null || realpath ~/.claude/skills 2>/dev/null)

# 如果 ~/.claude/skills 不是符号链接，它自身可能就是 git 仓库
# 直接用这个路径

# 2. 找到包含此目录的 git 仓库根目录
REPO_ROOT=$(cd "$SKILLS_REAL" && git rev-parse --show-toplevel 2>/dev/null)

# 3. 计算 skills 在仓库内的相对子目录
SKILLS_SUBDIR=$(cd "$SKILLS_REAL" && git rev-parse --show-prefix 2>/dev/null)
# 例如输出: agents/skills/  或  skills/  或为空（skills 就在仓库根目录）

# 4. 确认远程和分支
cd "$REPO_ROOT"
git remote -v          # 获取 remote 名称和 URL
git branch --show-current   # 当前分支名
```

**探测后必须向用户展示**：

```
Skills 实际路径:  /home/user/code/agent-skills-hook/agents/skills
Git 仓库根目录:   /home/user/code/agent-skills-hook
Skills 子目录:    agents/skills/
Remote:           origin  git@github.com:user/repo.git
分支:             main
```

## 第二步：创建/修改 skill 文件

直接在 `~/.claude/skills/<skill-name>/` 下操作即可，符号链接会透传到实际仓库：

```bash
mkdir -p ~/.claude/skills/<skill-name>
# 编辑 ~/.claude/skills/<skill-name>/SKILL.md
```

## 第三步：提交

**必须在第一步探测到的 `$REPO_ROOT` 下执行 git 操作：**

```bash
cd "$REPO_ROOT"

# 确认改动（相对路径从 $SKILLS_SUBDIR 开始）
git status

# 暂存
git add "${SKILLS_SUBDIR}<skill-name>/"

# 提交。优先检查仓库是否有自定义提交规范（CLAUDE.md / CONTRIBUTING.md），
# 没有则用 Conventional Commits
git commit -m "<message>"
```

## 第四步：推送

```bash
cd "$REPO_ROOT"
git push origin <branch>
```

## 故障排查

| 症状 | 处理 |
|------|------|
| `readlink -f` 不识别 | 换 `realpath`，都不行则 `ls -la ~/.claude/skills` 手动看指向 |
| `~/.claude/skills` 不是符号链接 | 它自身可能就是一个 git 仓库，直接用 `git rev-parse --show-toplevel` 在它里面执行 |
| `git rev-parse --show-toplevel` 失败（不在 git 仓库中） | 沿目录树向上找 `.git` 目录，或检查 skills 是否通过其他方式部署（如直接拷贝） |
| Skills 就在仓库根目录（`$SKILLS_SUBDIR` 为空） | `git add <skill-name>/` 即可，不需要前缀 |
| 多个 remote | 用 `git remote -v` 确认 push 目标，通常是 `origin` |

## 跨平台注意事项

- **Linux**：`readlink -f` 和 `realpath` 都可用
- **macOS**：`readlink` 没有 `-f`，用 `realpath`（需 coreutils）或 `python3 -c "import os; print(os.path.realpath('...'))"`
- **Windows (Git Bash)**：`readlink -f` 通常可用；如不行用 `cygpath` 或手动 `ls -la` 解析
- JSON 等配置文件中的 `~` 展开：用 `$HOME` 或 `${HOME}` 替代
