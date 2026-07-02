# agent-skills-hook

Claude Code / Codex CLI / OpenCode 三套 AI 编码运行时的共享配置与技能分发仓库。

## 做什么

- **单一配置源**：`config/` 维护三套运行时的入口指令、子代理定义、MCP 注册和插件配置，部署时通过符号链接 / Junction 同步到各自用户目录。
- **共享技能库**：`agents/skills/` 提供 60+ 个跨运行时共用的技能，由 `skill-forced-eval` 按请求自动匹配加载。
- **一键部署**：`linux/deploy.sh` 和 `windows/deploy.ps1` 自动完成链接创建、配置合并、MCP 注册、插件安装，部署前自动备份。

## 目录结构

```
agent-skills-hook/
├── config/                         # 单一配置源
│   ├── AGENTS.md                   # 仓库总则
│   ├── claude/CLAUDE.md            # Claude Code 全局指令
│   ├── codex/AGENTS.md             # Codex CLI 全局指令
│   ├── opencode/                   # OpenCode 配置 + 插件
│   └── shared/mcp_servers.json     # 共享 MCP 服务器定义
├── agents/skills/                  # 共享技能库
├── linux/deploy.sh                 # Linux 部署
├── windows/deploy.ps1              # Windows 部署
└── docs/                           # 计划 / 报告 / 规格文档
```

## 快速开始

### Linux

```bash
git clone <repo-url>
cd linux && chmod +x deploy.sh
./deploy.sh TARGET=all
```

### Windows

```powershell
git clone <repo-url>
cd windows
.\deploy.ps1 -Target "all"
```

部署后重启对应运行时即可生效。修改 `config/` 或 `agents/skills/` 后重新跑部署脚本更新。

部署前自动备份到 `~/.claude-backups/`、`~/.codex-backups/`、`~/.opencode-backups/`。

## 技能分类

### ddev 开发工作流（核心流水线）

端到端的规格驱动开发流程，从架构设计到最终验收。

| 技能 | 说明 |
|------|------|
| `ddev-arch` | 项目级架构规范初始化，建立模块边界与变更门禁 |
| `ddev-spec` | 编写 spec 文档（图优先），定义改动边界与流程 |
| `ddev-detail` | 梳理结构体定义、数据流和流程（图优先） |
| `ddev-diagram` | 手写 ASCII 架构图/流程图/数据流图到 .md |
| `ddev-pc-test` | 判断是否可在 PC 写测试 demo 验证，生成测试用例 |
| `ddev-plan` | 将 spec/detail 拆解为可执行实现步骤 |
| `ddev-exec` | 按计划顺序执行任务，含进度跟踪 |
| `ddev-gate` | 实现一致性最终验收（一致性→清理→规范 三阶段） |
| `ddev-clean` | 代码 slop 清理，死代码删除/去重/命名修正 |
| `ddev-c-pro` | C 语言设计规范、Doxygen 注释、命名与风格约束 |
| `ddev-doc-review` | 文档审查（独立子代理，五维度检查） |
| `ddev-decision-log` | 决策记录，贯穿全流程 |
| `code-review` | 代码审查，依赖 codegraph 做结构影响分析 |
| `comment-generator` | 为 C 函数生成 Doxygen 标准中文注释 |
| `compile-commands-init` | C/C++ 项目 compile_commands.json 与 clangd 配置 |
| `trace-flow` | 调用链追踪 |

### ddev 使用指南

ddev 是一套"先想清楚再动手"的规格驱动开发流程。典型用法：

```
ddev-arch        ← 项目初始化时跑一次，建立架构约束
    ↓
ddev-spec        ← 每次改动前：画边界 + 入口 + 流程
    ↓
ddev-detail      ← 需要时：细化结构体 / 数据流
    ↓
ddev-pc-test     ← 可选：能写 PC 测试就写，生成 demo
    ↓
ddev-plan        ← 拆成可执行任务清单
    ↓
ddev-exec        ← 逐个执行，自动跟踪进度
    ↓
ddev-gate        ← 三道关卡验收：一致性 → 清理 → C 规范
    ↓
完成
```

辅助技能全程可用：
- `ddev-diagram` — 任何阶段需要画图时调用
- `ddev-decision-log` — 做技术决策时记录
- `ddev-doc-review` — 文档写完后派独立子代理审查
- `code-review` — 代码改动后做质量/安全检查

实际使用时不需要每次都跑全流程。小改动可以直接 `ddev-spec → ddev-plan → ddev-exec → ddev-gate`。纯 bug 修复甚至可以跳过 spec，直接从 `ddev-plan` 开始。

### 代码审查、验证与调试

| 技能 | 说明 |
|------|------|
| `requesting-code-review` | 完成任务/功能后请求代码审查 |
| `receiving-code-review` | 接收审查反馈，技术严谨验证后实现 |
| `verification-before-completion` | 完成前验证——先跑命令确认输出，再宣称通过 |
| `systematic-debugging` | 系统化调试流程，修复前先定位根因 |
| `debug-locate-assistant` | C/C++ 回归定位，精确到 file:line/function |
| `visual-verdict` | 截图与参考图的视觉 QA 结构化对比 |
| `protocol-semantic-guard` | 协议/指令集语义守卫，改 wire protocol 时用 |
| `image-understanding` | 图片对比/视觉回归/UI diff 检测 |

### 嵌入式与硬件调试

| 技能 | 说明 |
|------|------|
| `embedded-debug-workflow` | 改代码→编译刷写→串口抓日志 闭环联调 |
| `embedded-workflow-cache-init` | 初始化嵌入式调试缓存（VID/PID、固件产物、传输参数） |
| `serial-log-debug` | Windows 串口日志捕获、收发、TX/RX 追踪 |
| `repo-firmware-flasher` | 基于仓库代码推导刷写参数并执行刷写 |
| `repo-usb-communicator` | 定位 USB 设备参数，脚本打开/收发数据 |
| `kingstvis-socket` | KingstVIS 逻辑分析仪 SocketAPI 采集/导出 |

### 文档与内容创作

| 技能 | 说明 |
|------|------|
| `doc-coauthoring` | 结构化文档协作写作流程 |
| `docx` | Word 文档创建/编辑/批注/修订 |
| `pdf` | PDF 抽取/创建/合并/表单填写 |
| `pptx` | PPT 创建/编辑/布局/演讲者备注 |
| `guizang-ppt-skill` | 横向翻页网页 PPT（杂志风/瑞士风两种主题） |
| `presentation-design` | 演示文稿设计与评估 |
| `defuddle` | 网页干净 Markdown 提取，去广告导航 |
| `algorithmic-art` | p5.js 算法艺术生成 |
| `json-canvas` | Obsidian JSON Canvas 文件创建/编辑 |
| `xlsx` | Excel 创建/编辑/公式/数据分析 |
| `xlsx-manipulation` | openpyxl 编程操作 Excel |

### 数据采集与分析

| 技能 | 说明 |
|------|------|
| `mediacrawler` | 小红书/抖音/B站/微博 多平台数据爬取 |
| `bilibili-analyzer` | B站视频下载→拆帧→AI 分析→专题文档 |
| `china-news-crawler` | 微信公众号/今日头条/网易/搜狐/腾讯新闻提取 |
| `hv-analysis` | 横纵分析法深度研究（历时+共时双轴） |

### 版本控制与工程规范

| 技能 | 说明 |
|------|------|
| `git-commit-standard` | 标准提交流程（版本号递进+固件产物+README 更新） |
| `git-commit-template` | Conventional Commits 提交模板 |
| `model-version-locator` | 固件仓库机型宏和版本号定位 |
| `repository-encoding-normalizer` | 源码仓库 UTF-8 统一 + 编译时 GBK 自动转换 |

### Obsidian 集成

| 技能 | 说明 |
|------|------|
| `obsidian-cli` | Obsidian vault 交互、笔记管理、插件开发调试 |
| `obsidian-markdown` | Obsidian Flavored Markdown（wikilinks/callouts/properties） |
| `obsidian-bases` | Obsidian Bases 视图/过滤器/公式/汇总 |

### 浏览器与 Web

| 技能 | 说明 |
|------|------|
| `agent-browser` | 浏览器自动化 CLI（导航/填表/截图/数据提取） |
| `webapp-testing` | Playwright 本地 Web 应用测试与调试 |

### 元技能与基础设施

| 技能 | 说明 |
|------|------|
| `skill-forced-eval` | **核心调度器**——每轮请求强制评估匹配技能 |
| `tool-routing` | 工具路由规则（codegraph/ctx/grep 选择策略） |
| `skill` | 技能管理：列表/添加/删除/搜索/编辑 |
| `find-skills` | 查找和安装社区技能 |
| `skill-recorder` | 技能使用信号记录（corrected/friction） |
| `skill-optimizer` | 基于信号集群优化 skill（8 步管线） |
| `skill-init` | skill-optimizer 系统初始化 |
| `writing-skills` | 创建/编辑/验证 skills 和 SKILL.md |
| `using-superpowers` | 执行类 skills 使用说明 |
| `using-git-worktrees` | 隔离 git worktree 创建与验证 |
| `plan` | 战略规划（含可选访谈流程） |
| `grill-me` | 高强度追问——逐项压实计划/设计的关键分支 |
| `neat-freak` | 会话结束知识洁癖清理——同步文档与代码 |
| `pdf_demo_skill` | PDF 处理能力演示 |

## 更新与回滚

修改 `config/` 或 `agents/skills/` 后重新运行部署脚本即可生效。

回滚：从 `~/.claude-backups/` / `~/.codex-backups/` / `~/.opencode-backups/` 拷回目标目录覆盖。

## 前置依赖

部署脚本自动检查并安装：
- **codegraph**：`npm i -g @colbymchenry/codegraph`
- **uv**（Windows）：pip 安装
- **opencode CLI**：缺失时跳过插件安装

进入新仓库后需手动执行 `codegraph init -i <repo>` 建立索引。
