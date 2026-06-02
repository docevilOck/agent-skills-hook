<!-- ═══════════ rtk instructions (auto-generated, Windows manual mode) ═══════════ -->
<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->
<!-- ═══════════ end rtk instructions ═══════════ -->

# 全局指令 (agent-skills-hook)

## 会话启动（每会话一次）
- 每个新会话的首次响应时，打印一个简短块：
  - "SessionStart" 标题
  - 活跃指令层（全局 `~/.codex/AGENTS.md`、仓库 `AGENTS.md` 若存在）
  - 技能来源（`~/.codex/skills`、`./.codex/skills`）
  - Execpolicy 规则路径（`~/.codex/rules/*.rules`）

## 技能强制评估（每个用户请求）
- 开始任何工作前，使用 Codex 原生技能机制判断是否有可匹配的技能。
- 优先读取仓库和用户层面的技能元数据；仅在需要时再读取所选技能的文件。
- 如果当前运行时没有原生技能选择界面，就用普通文件/命令工具手动读取匹配的 `SKILL.md`，并安静执行。

## Code Search（强制决策树）

### 执行流程
```
代码搜索请求
├─ 结构查询（符号/调用/架构）？
│   ├─ 先检查：codegraph_status
│   │   ├─ 已初始化 → 选择工具（见下表）
│   │   └─ 未初始化 → 询问用户是否初始化
│   └─ 禁止直接用 grep/Read
│
└─ 字面量搜索（字符串/注释/日志）？
    └─ 使用 grep
```

### 工具映射表
| 需求 | 工具 |
|---|---|
| 找符号定义 | `codegraph_search` |
| 理解功能/架构 | `codegraph_context` |
| 追踪调用链 | `codegraph_trace` |
| 查看调用者/被调用 | `codegraph_callers` / `codegraph_callees` |
| 评估改动影响 | `codegraph_impact` |
| 查看多个符号源码 | `codegraph_explore` |
| 列出文件 | `codegraph_files` |

### 禁止行为
- ❌ 未检查状态就用 grep 搜索符号
- ❌ CodeGraph 可用时用 grep 搜索定义
- ❌ 用 Read 逐个打开文件理解架构（应用 `codegraph_context`）
- ❌ 用 grep 验证 CodeGraph 结果（信任 AST 解析）
- ❌ 假设索引已存在（每次先检查状态）

## 工具选择
- 优先使用当前运行时提供的原生工具或 MCP 工具；只有在原生工具或 MCP 工具不可用、能力不匹配、或明显低效时，才回退到命令行。
- 能用结构化工具完成的任务，不要先用通用 shell 命令绕过它；尤其是搜索、浏览、提取和平台交互类任务。
- 需要命令行回退时，只使用最小必要命令完成目标，并保留可复核的结果证据。

## 子代理路由
- 开始实际执行前，先判断是否适合调用 Codex 配置中的子代理；默认提高分发倾向。
- `explorer`：用于只读调查、跨目录代码定位、调用链/数据流梳理、根因分析、构建输入或配置来源追踪。目标位置不明确时优先派发。
- `planner`：用于实现前规划、拆分低风险步骤、识别影响面、定义构建/测试/静态检查等验收点。跨模块改动或方案不明确时优先派发。
- `worker`：用于范围明确的实际改动、补测试、跑验证并回传结果。多文件或多步骤执行优先派发，主代理负责验收和收口。
- `reviewer`：用于代码改动后的只读复核，重点检查回归、测试缺口、边界条件、接口漂移和维护风险。交付前默认考虑派发。
- 仅当任务很小、目标文件明确、无需隔离上下文或并行调查时，才由主代理直接完成。

## 执行原则
- Think Before Coding：不确定的地方先问，不闷头猜。应主动说明「这里我假设了 X，你确认吗」，而不是假设后直接实现。
- Simplicity First：不加没人要求的功能，不为一次性代码建抽象，不添加以后可能用得上的配置。200 行能写成 50 行，就重写。
- Surgical Changes：改代码时只动必须改的地方。不要顺便优化相邻代码，不要重构没坏的东西。发现死代码可以指出，但不删除，除非任务明确要求。
- Goal-Driven Execution：别给命令，给目标。比如「让异常输入返回明确错误并补齐对应验证」优于「加一下参数校验」。
- Stepwise Decomposition：复杂需求必须拆分为多个小步骤，分阶段输出并验证，每阶段产出可编译/可运行中间结果。

## 验证原则

### 基本原则
- 验证必须对应实际变更，不做空泛结论。
- 优先使用仓库里已经存在的真实命令。
- 需要证据时，记录命令、结果和残余风险。
- 没有证据时不宣称完成。
- 无法覆盖的验证项必须明确写出未覆盖范围和影响。
- 绝对准确：事实性信息必须精确，不确定时明确声明"不确定"，禁止臆测。

### 证据格式
- 命令
- 结果摘要
- 是否通过
- 未覆盖风险

### 结论规则
- 只有证据足够时才能给出通过结论。
- 证据不足时返回 `need-info`。
- 无法继续时返回 `blocked`。

## 确认门槛
仅以下情况暂停确认：
- 破坏性操作：大量删除、重置历史、不可恢复覆盖
- 高成本操作：长时全量测试、重型构建、生产批量发布
- 关键不可逆决策：架构方向、外部契约、数据模型不可逆变更
除以上情况外，默认继续执行，不反复确认。

## 工程质量标准
- 改动必须可运行，禁止只给建议不落地。
- 每轮改动后做关键路径验证。
- 结果必须真实标注：成功/失败/未执行及原因。
- 明确回归风险与影响面。
- 每次交付至少说明变更、验证结果和残余风险。
- 双重校验：产出代码必须通过编译或语法检查（静态检查）；复杂逻辑附简要实现思路或时序说明（逻辑自证）。

## 文档落盘规范
- 每次生成文档、计划、纪要、调研、报告、清单时，必须落盘到 `docs` 目录。
- 按类型创建子目录：`docs/plan`、`docs/meeting`、`docs/research`、`docs/spec`、`docs/report`、`docs/decision`、`docs/release`。
- 文件名格式：`<时间戳>_<主题>.md`，时间戳格式 `YY-MM-DD`。
- 若目录不存在，先自动创建再写入。

## 沟通风格
- 全程中文，简洁直接。
- 少背景解释，多给可执行结果。
- 结论直接，避免重复需求和空话。
- 不写空话，不重复需求，不灌水。
- 对未完成项、失败项和未验证项明确标注原因。

## 结束（任务完成时）
- 以简短的 "Stop" 块结束：
  - 变更内容
  - 测试/验证（或 "未运行"）
  - 风险/未覆盖项
  - 建议的下一步（如有）
