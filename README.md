# agent-skills-hook

Claude Code / Codex CLI / OpenCode 三套 AI 编码运行时的共享配置与技能分发仓库。

## 做什么

- **单一配置源**：`config/` 目录维护三套运行时的入口文档（CLAUDE.md / AGENTS.md）、子代理定义、MCP 服务器注册和插件配置，部署时通过符号链接 / Junction 同步到各自用户目录，改一处全生效。
- **共享技能库**：`agents/skills/` 提供 60+ 个跨运行时共用的技能（skills），覆盖文档写作、代码审查、嵌入式调试、项目管理、媒体爬取等场景，由 `skill-forced-eval` 按请求自动匹配加载。
- **一键部署**：`linux/deploy.sh` 和 `windows/deploy.ps1` 自动完成链接创建、配置合并、MCP 注册、插件安装，部署前自动备份现有配置。
- **离线模型**：`semble_offline_bundle/` 预置 Semble 语义搜索模型的离线缓存，部署时自动恢复到 Hugging Face 缓存目录。

## 目录结构

```
agent-skills-hook/
├── AGENTS.md                       # 仓库总则（部署到 ~/.claude/AGENTS.md）
├── config/                         # 单一配置源
│   ├── AGENTS.md                   # 共享入口（部署到 ~/.claude/AGENTS.md）
│   ├── claude/
│   │   ├── CLAUDE.md               # Claude Code 全局指令
│   │   └── agents/                 # Claude Code 子代理定义（.md）
│   ├── codex/
│   │   ├── AGENTS.md               # Codex CLI 全局指令
│   │   └── agents/                 # Codex 子代理定义（.toml）
│   ├── opencode/
│   │   ├── AGENTS.md               # OpenCode 全局指令
│   │   ├── opencode.json           # OpenCode 主配置（模型 / MCP / 插件）
│   │   ├── dcp.jsonc               # DCP 插件配置
│   │   └── agents/                 # OpenCode 子代理定义（.md）
│   └── shared/
│       └── mcp_servers.json        # 共享 MCP 服务器定义
├── agents/skills/                  # 共享技能库（60+ skills）
├── linux/deploy.sh                 # Linux 部署脚本（软链接）
├── windows/deploy.ps1              # Windows 部署脚本（SymbolicLink / Junction）
├── scripts/
│   └── session-catchup.py          # 会话续接脚本
├── semble_offline_bundle/          # Semble 离线模型缓存
└── docs/                           # 计划 / 报告 / 规格文档
```

## 快速开始

```bash
git clone <repo-url>
```

### Linux

```bash
cd linux && chmod +x deploy.sh

# 部署全部运行时
./deploy.sh TARGET=all

# 或指定目标
./deploy.sh TARGET=claude
./deploy.sh TARGET=codex
./deploy.sh TARGET=opencode
```

### Windows

```powershell
cd windows

# 部署全部运行时
.\deploy.ps1 -Target "all"

# 或指定目标
.\deploy.ps1 -Target "claude"
.\deploy.ps1 -Target "codex"
.\deploy.ps1 -Target "opencode"
```

部署后重启对应运行时即可生效。

## 部署内容

| 运行时 | 部署项 |
|--------|--------|
| Claude Code | `~/.claude/AGENTS.md`、`CLAUDE.md`、`skills/`（Junction→`agents/skills/`）、`agents/`（Junction→`config/claude/agents/`）、MCP 服务器（user scope） |
| Codex CLI | `~/.codex/AGENTS.md`、`skills/`（Junction→`agents/skills/`）、`agents/`（Junction→`config/codex/agents/`）、MCP 服务器 |
| OpenCode | `~/.config/opencode/AGENTS.md`、`opencode.json`（深合并）、`dcp.jsonc`（深合并）、`skills/`（Junction→`agents/skills/`）、`agents/`（Junction→`config/opencode/agents/`）、插件安装 |

所有运行时共享同一份 `mcp_servers.json`（codegraph + semble + context-mode），部署脚本会通过各运行时的 CLI 自动注册。`opencode.json` 和 `dcp.jsonc` 采用深合并策略，不会覆盖用户本地的私有配置（如 provider / API Key）。

## 更新与回滚

修改 `config/` 或 `agents/skills/` 后重新运行部署脚本即可。

部署前自动备份到：
- Linux：`~/.codex-backups/`、`~/.opencode-backups/`、`~/.claude-backups/`
- Windows：`$env:USERPROFILE\.codex-backups\`、`$env:USERPROFILE\.opencode-backups\`、`$env:USERPROFILE\.claude-backups\`

从对应备份目录拷回目标用户目录即可恢复。

## 前置依赖

部署脚本会自动检查并安装缺失依赖：
- **codegraph**：通过 `npm i -g @colbymchenry/codegraph` 安装
- **semble**：Linux 通过 pip 安装，Windows 通过 uvx 运行
- **uv**（Windows）：若不存在则通过 pip 安装
- **opencode CLI**：插件安装需要，缺失时跳过

进入新仓库后需手动执行 `codegraph init -i <repo>` 建立索引。
