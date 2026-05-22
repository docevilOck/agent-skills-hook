# agent-skills-hook

## 简介
这是一个把"Hook 机制"落地到 Codex CLI / OpenCode / Claude Code 的配置仓库，目标是：
- 提高 AI 对 skills 的触发与使用概率
- 固定会话起止输出（`SessionStart` / `Stop`）
- 在危险命令前给出 execpolicy 安全提示
- 强化嵌入式 C 开发工作流，优先覆盖 Make/CMake、构建诊断、固件审查与硬件影响分析

## 功能
- 会话启动提示（`SessionStart`）
- 每次请求前强制技能评估（`Skill Forced Eval`）
- 危险命令前缀提示（execpolicy rules）
- 任务完成收尾总结（`Stop`）
- Codex / Claude Code 的轻量优先协作路由
- OpenCode 的基础配置与默认部署
- 面向嵌入式 C 的 agent 分工：规划、实现、构建修复、固件审查、硬件影响审查

## 目录结构

```
agent-skills-hook/
├── config/                   # 单一配置源（自包含）
│   ├── AGENTS.md            # 共享入口
│   ├── claude/CLAUDE.md     # Claude Code 配置
│   ├── codex/AGENTS.md      # Codex CLI 配置
│   ├── opencode/AGENTS.md   # OpenCode 配置
│   ├── opencode/opencode.json # OpenCode 主配置
│
├── linux/deploy.sh          # Linux 部署脚本（软链接）
├── linux/cache_semble_model.sh # 导出本机 Semble 模型缓存
├── windows/deploy.ps1       # Windows 部署脚本（复制）
├── windows/cache_semble_model.ps1 # 导出本机 Semble 模型缓存
├── third_party/semble/      # Semble 模型缓存镜像
│
├── agents/skills/           # 共享技能库
│
└── README.md
```

### 设计原则
- **单一配置源**：所有运行时配置位于 `config/`，避免双线维护
- **自包含文件**：每个入口文件包含完整规则，不依赖外部引用
- **平台差异仅在部署**：Linux 用软链接，Windows 用复制，配置内容完全相同

## 快速开始

### 1. 初始化 Skills Submodule

```bash
git submodule update --init --recursive agents/skills
```

### 2. 部署配置

#### Linux

```bash
cd linux
chmod +x deploy.sh

# 默认部署所有运行时
./deploy.sh TARGET=all

# 或指定目标
./deploy.sh TARGET=codex      # 仅 Codex
./deploy.sh TARGET=opencode   # 仅 OpenCode
./deploy.sh TARGET=claude     # 仅 Claude Code
```

#### Windows

```powershell
cd windows

# 默认部署所有运行时
.\deploy.ps1 -Target "all"

# 或指定目标
.\deploy.ps1 -Target "codex"
.\deploy.ps1 -Target "opencode"
.\deploy.ps1 -Target "claude"
```

### 3. 重启运行时

部署后重启对应运行时生效：
- Codex CLI: 重启终端或重新运行 `codex`
- OpenCode: 重启 OpenCode
- Claude Code: 重启 Claude Code

## 嵌入式 C 工作流

当前仓库的默认协作方式偏向嵌入式开发：

- 小改动默认直接处理，避免把简单工作流变重。
- 遇到 Make/CMake、交叉编译、链接、启动文件、宏或包含路径问题时，优先升级给 `build_resolver`。
- 遇到 ISR、`volatile`、共享状态、寄存器访问、缓冲区、超时等固件风险时，要求经过 `firmware_reviewer`。
- 遇到 GPIO、时钟、UART、SPI、I2C、CAN、DMA、timer、board-support 等改动时，要求经过 `hardware_impact`。
- 多文件功能、状态机、初始化时序或模块边界调整时，先拆解，再落地，最后回归审查。

### 嵌入式相关 Skills

- `embedded-workflow-cache-init`
  - 初始化项目内 `.agents/cache` 的 embedded 工作流缓存。
  - 适用于先落盘 `VID/PID`、刷写参数、固件产物路径，或在已提供逻辑分析仪映射/测试方法时初始化 KingstVIS 相关缓存。
- `repo-firmware-flasher`
  - 从仓库事实提取刷写参数，生成和复用下载配置，并执行探测、分包或刷写。
- `embedded-debug-workflow`
  - 编排“改代码 -> 编译 -> 刷写 -> 串口抓取 -> 可选 USB/逻辑分析”闭环调试流程。
- `kingstvis-socket`
  - 通过 SocketAPI 驱动 KingstVIS 进行抓取和导出，优先生成 CSV 供 AI 分析。

### 通用 Skills

- `grill-me`
  - 对计划或设计进行逐题追问式梳理，直到关键分支和依赖被逐步澄清。
  - 仅在用户明确点名 `grill-me` 或明确要求“grill me”时使用；默认不自动触发。

## 验证与回滚

### 验证部署

当前各运行时都会使用自己的用户级配置目录：Codex 部署 `AGENTS.md`、`agents/`、`skills/`，OpenCode 部署 `AGENTS.md`、`opencode.json`、`skills/`，并同步 `~/.claude/skills`，Claude Code 部署 `AGENTS.md`、`CLAUDE.md`、`skills/`。

## Semble 部署

- 部署脚本现在会自动检查本机是否已有 `semble`
- 若未安装，会自动执行 `python -m pip install "semble[mcp]"`
- 若仓库内存在 `third_party/semble/huggingface/hub/models--minishlab--potion-code-16M`
  - 会自动同步到本机 `~/.cache/huggingface/hub/`
- 会自动确保 `Codex` 用户级 MCP 已配置 `semble`
- 会自动确保 `Qoder` 用户级 `settings.json` 中包含 `mcpServers.semble`
- 会自动把 `config/opencode/opencode.json` 合并到 `~/.config/opencode/opencode.json`
- 会自动为 `Semble` 注入 `HF_HUB_DISABLE_SYMLINKS=1`，绕过 Windows 上 Hugging Face cache symlink 问题
- 这样模型通常只需联网下载一次，后续机器可直接复用仓库内缓存

首次把本机缓存导入仓库：

```powershell
.\windows\cache_semble_model.ps1
```

```bash
./linux/cache_semble_model.sh
```

**Linux（软链接）**：
```bash
ls -la ~/.codex/skills ~/.codex/agents ~/.codex/AGENTS.md
ls -la ~/.config/opencode/skills ~/.config/opencode/AGENTS.md ~/.config/opencode/opencode.json
ls -la ~/.claude/skills ~/.claude/CLAUDE.md
```

**Windows（复制）**：
```powershell
Test-Path "$env:USERPROFILE\.codex\AGENTS.md"
Test-Path "$env:USERPROFILE\.codex\agents"
Test-Path "$env:USERPROFILE\.config\opencode\AGENTS.md"
Test-Path "$env:USERPROFILE\.config\opencode\opencode.json"
Test-Path "$env:USERPROFILE\.claude\CLAUDE.md"
```

### 回滚

备份目录位于：
- Linux: `~/.codex-backups/`, `~/.opencode-backups/`, `~/.claude-backups/`
- Windows: `$env:USERPROFILE\.codex-backups\`, 等

恢复备份：
```bash
# Linux
cp -a ~/.codex-backups/agent-skills-hook-<timestamp>/codex/* ~/.codex/
```

```powershell
# Windows
Copy-Item "$env:USERPROFILE\.codex-backups\agent-skills-hook-<timestamp>\codex\*" "$env:USERPROFILE\.codex\" -Recurse -Force
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `config/AGENTS.md` | 共享入口，定义仓库总则 |
| `config/claude/CLAUDE.md` | Claude Code 运行时配置（自包含） |
| `config/codex/AGENTS.md` | Codex CLI 运行时配置（自包含） |
| `config/opencode/AGENTS.md` | OpenCode 运行时配置（自包含） |
| `config/opencode/opencode.json` | OpenCode 主配置 |
| `linux/deploy.sh` | Linux 部署脚本（软链接方式） |
| `windows/deploy.ps1` | Windows 部署脚本（复制方式） |

## 维护说明

更新配置只需修改 `config/` 目录下的文件，然后重新运行部署脚本即可。

- Codex 部署维护 `~/.codex/AGENTS.md`、`agents/`、`skills/`
- Codex 代理定义从 `config/codex/agents` 部署到 `~/.codex/agents`
- OpenCode 部署维护 `~/.config/opencode/AGENTS.md`、`opencode.json`、`skills/`
- `config/opencode/opencode.json` 只保存共享配置模板，不保存 provider/API Key；部署脚本会把这些字段深合并到本地配置，保留未被模板覆盖的私有配置。
- Claude Code 部署维护 `~/.claude/AGENTS.md`、`CLAUDE.md`、`skills/`

- Linux 用户：修改后重新运行 `linux/deploy.sh`（软链接自动指向新内容）
- Windows 用户：修改后重新运行 `windows/deploy.ps1`（复制新内容）
