# agent-skills-hook

维护 Claude Code、Codex CLI、OpenCode 的共享技能库（skills）与协作提示词配置。

## 目录结构

```
agent-skills-hook/
├── config/                       # 单一配置源（自包含）
│   ├── AGENTS.md                 # 共享入口，仓库总则
│   ├── claude/CLAUDE.md          # Claude Code 配置
│   ├── codex/AGENTS.md           # Codex CLI 配置
│   ├── opencode/AGENTS.md        # OpenCode 配置
│   ├── opencode/opencode.json    # OpenCode 主配置（插件、MCP、模型等）
├── agents/skills/                # 共享技能库
├── linux/deploy.sh               # Linux 部署（软链接）
├── windows/deploy.ps1            # Windows 部署（Junction 链接）
└── README.md
```

## 部署

### Linux

```bash
git clone <repo-url>
cd linux && chmod +x deploy.sh
./deploy.sh TARGET=all                 # 含 context-mode
SKIP_CONTEXT_MODE=1 ./deploy.sh        # 跳过 context-mode
```

### Windows

```powershell
git clone <repo-url>
cd windows
.\deploy.ps1 -Target "all"             # 含 context-mode
.\deploy.ps1 -SkipContextMode          # 跳过 context-mode
```

部署将：
- 安装 `context-mode`（npm 全局包，为 OpenCode 提供 `ctx_*` 上下文管理工具）
- `AGENTS.md` 和 `CLAUDE.md` 复制到各运行时用户目录
- `skills/` 通过 Junction（Windows）或软链接（Linux）指向仓库 `agents/skills/`
- `opencode.json` 深合并到 `~/.config/opencode/opencode.json`
- `agents/` 目录复制到 `~/.codex/agents/`（Codex）

## 更新

修改 `config/` 目录下的文件后，重新运行部署脚本即可生效。

## 回滚

备份位于 `~/.codex-backups/`、`~/.opencode-backups/`、`~/.claude-backups/`。
