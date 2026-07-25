# agent-skills-hook 技能库

本目录包含 60+ 个共享技能（skills），为 Claude Code、Codex CLI、OpenCode 提供专业领域的工作流和工具集成。

## 加载机制

技能通过系统指令中的「技能强制评估」自动匹配并加载。每次用户请求时，系统根据请求内容匹配最相关的技能（最多 5 个）并自动加载。

**自动加载**（默认）：大多数技能会根据用户请求中的关键词自动触发，无需手动指定。

**手动调用**（⚠️ 需注意）：部分技能标注了「禁止自动加载」或「仅限手动调用」，这些技能**不会**被「技能强制评估」自动匹配，必须由用户明确说出指定的触发词才会加载。详见下方「手动调用技能」章节。

---

## 一、文档与写作

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `doc-coauthoring` | 结构化文档协同撰写流程：提案、技术规格、决策文档、说明文档等。通过迭代精炼完成高质量文档。 | 自动 — 提到"写文档""创建提案""起草规格"等 |
| `docx` | .docx 文档创建、编辑、分析。支持修订跟踪、批注、格式保留和文本提取。 | 自动 — 需要处理 .docx 文件时 |
| `pdf` | PDF 操作工具集：提取文本/表格、创建新 PDF、合并/拆分、表单填充。 | 自动 — 需要处理 PDF 时 |
| `pdf_demo_skill` | PDF 处理能力演示。 | 自动 |
| `pptx` | .pptx 演示文稿创建、编辑、分析。支持布局、批注、演讲者备注。 | 自动 — 需要处理 .pptx 文件时 |
| `presentation-design` | 演示文稿设计与评估。触发词：presentation、slides、talk、PowerPoint、Keynote、reveal.js。 | 自动 |
| `xlsx` | 电子表格创建、编辑、分析。支持公式、格式化、数据分析和可视化。 | 自动 — 需要处理 .xlsx/.xlsm/.csv 等 |
| `xlsx-manipulation` | 用 openpyxl 库程序化操作 Excel 文件。 | 自动 |
| `guizang-ppt-skill` | 生成横向翻页网页 PPT（单 HTML 文件）。含 WebGL 背景、章节幕封、数据大字报、图片网格等模板。提供两种风格：电子杂志×电子墨水和瑞士国际主义。 | 自动 — 提到"杂志风 PPT""瑞士风 PPT""web deck"等 |
| `ddev-diagram` | 按规范手写 ASCII 架构图、流程图、数据流图、对比图到 .md 文件，不经过 PlantUML。 | 自动 — 需要绘制架构图、流程图等 |
| `ddev-plan` | 将已有规格或多步骤任务需求映射为可执行的实现计划，明确任务、约束和验证标准。 | 手动 — 用户明确调用 `ddev-plan` 时 |
| `writing-skills` | 创建、编辑、验证 skills 的统一工作流，确保 skill 易于发现、阅读和长期维护。 | 自动 — 创建/编辑/重构 SKILL.md 时 |

## 二、代码质量

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `code-review` | 综合代码审查：质量、安全性、可维护性，带严重程度分级反馈。 | 自动 — 需要代码审查时 |
| `requesting-code-review` | 在完成任务、实现重要功能或准备合并前，派发审查子代理确认工作满足要求。 | 自动 — 任务完成/准备合并时 |
| `receiving-code-review` | 接收代码审查反馈时的技术评估与验证流程，避免表面附和或盲目照做。 | 自动 — 收到审查反馈时 |
| `ddev-clean` | AI 生成代码的反 slop 清理重构工作流，逐臭味清理并保持行为不变。 | 自动 — 需要清理/重构 AI 生成代码 |
| `ddev-comment-gen` | C 项目注释审查节点。在 ddev-c-pro 通过后，逐文件/函数/结构体核验 Doxygen 注释完整性，缺失则补全。 | 自动 — C 项目 c-pro 审查通过后 |
| `systematic-debugging` | 系统性调试方法论：在提出修复之前先定位根因，避免随手打补丁掩盖底层问题。 | 自动 — 遇到 bug、测试失败或异常行为时 |
| `verification-before-completion` | 完成前强制验证：必须先运行验证命令并确认输出，再做任何成功声明。 | 自动 — 准备声称工作已完成/已修复时 |
| `protocol-semantic-guard` | 协议和指令集相关代码变更的语义守卫。修改有线协议、命令编码、解析表、标签、属性、枚举等时使用。 | 自动 — 修改协议/指令集相关代码时 |
| `neat-freak` | 会话结束后对项目文档（CLAUDE.md、README.md、docs/）和 agent 记忆进行洁癖级审查与同步。触发词：sync up、tidy up docs、整理文档、收尾、同步一下、整理一下等。 | 自动 |
| `ddev-spec` | 代码修改前编写 spec 文档，用图表达改动边界、模块关系、接入点和主流程。仅用于代码改动场景。 | 手动 — 用户明确调用 `ddev-spec` 时 |
| `ddev-detail` | spec 文档确认后，以图优先方式梳理结构体定义、数据流和流程。仅用于代码改动场景。 | 手动 — 用户明确调用 `ddev-detail` 时 |
| `ddev-gate` | 代码实现完成后核对是否与 spec 文档及 detail 文档一致，给出最终验收结论。 | 联动 — 仅允许由 `ddev-exec` 默认收尾阶段加载 |
| `visual-verdict` | 结构化视觉 QA 判定，用于截图与参考图的对比验证。 | 自动 — 需要视觉对比判定时 |
| `image-understanding` | 视觉回归与图像理解：截图对比、差异检测、CI 检查（通过 Playwright 或 Chromatic）。 | 自动 — 需要图片对比/视觉测试时 |
| `ddev-doubt` | 对 AI 的结论、分析或建议进行系统性质疑和对抗性审查。派发独立子代理以对抗立场拆解 AI 产出。触发词：质疑这个结论、帮我挑刺、挑战AI说法、doubt。 | 自动 |

### 实现工作流（ddev-spec → ddev-detail → ddev-plan → ddev-exec → ddev-gate 管线）

以下五个技能组成一条从设计到验收到执行的完整实现管线，适用于代码改动（新增、重构、修复）场景。

**触发约束：** `ddev-spec` / `ddev-detail` / `ddev-plan` / `ddev-exec` 均禁止自动加载，只有用户明确点名时才允许使用；`ddev-gate` 同样禁止自动匹配，且禁止用户手动调用，仅允许由 `ddev-exec` 在默认收尾阶段联动加载。

```
需求确认
  │
  ▼
① ddev-spec                          ← 出 spec 文档：改动边界、模块关系、接入点、主流程
  │                                          产出 → docs/plans/YY-MM-DD_name/spec/
  │  图怎么画？ → 调 ddev-diagram
  │
  ▼ spec 文档确认后
② ddev-detail                       ← 细化实现细节：结构体定义、数据流、关键流程
  │                                          产出 → docs/plans/YY-MM-DD_<topic>/detail/
  │                                          ├─ overview.md
  │                                          ├─ structures/<name>.md（结构关系图与结构定义）
  │                                          ├─ dataflow/<name>.md（数据流图）
  │                                          └─ flows/<name>.md（关键流程图）
  │
  ▼ detail 确认后 → ddev-plan 拆解执行计划 → ddev-exec 驱动编码
  │
  ▼ 代码写完
③ ddev-gate                 ← 最终验收门禁（四段循环）
     ├─ 第一段：拉独立审查 agent，对照 architecture + detail 文档逐项核对代码实现
     │          ├─ 一致 → pass，进入第二段
     │          └─ 不一致 → 打回修改，修改后重新进入本 skill
     ├─ 第二段：拉独立 subagent 调用 ddev-clean 做垃圾代码清理
     │          ├─ 清理未改代码 → 保留结论，进入第三段
     │          └─ 清理改了代码 → 重新回到第一段做一致性重审
     ├─ 第三段：拉独立 subagent 做编码规范审查（C 项目加载 ddev-c-pro，其他语言按需路由）
     │          ├─ 通过 → pass，进入第四段
     │          └─ 不通过 → 打回修改，修改后重新进入本 skill
     └─ 第四段：拉独立 subagent 做注释/文档审查（C 项目加载 ddev-comment-gen，其他语言按需路由）
                ├─ 通过 → 最终 pass，任务完成
                └─ 不通过 → 补全注释，修改后重新进入本 skill
```

| 阶段 | 技能 | 核心职责 | 关键约束 |
|------|------|----------|----------|
| ① 设计 | `ddev-spec` | 在编码前用图讲清改动边界、模块关系、接入点和主流程 | 仅允许用户手动调用；仅产出 spec 文档，不得直接改代码；图优先、文辅佐；遵守项目级 `docs/architecture/` 约束 |
| ② 细化 | `ddev-detail` | spec 确认后细化结构体定义、数据流图和关键流程图 | 仅允许用户手动调用；spec 文档必须先获确认才能进入此阶段；图优先、文辅佐 |
| ③ 计划 | `ddev-plan` | 将已确认的 spec/detail 设计拆成可执行实现计划 | 仅允许用户手动调用；不得在计划阶段发明新设计；计划完成后不得自动进入执行 |
| ④ 执行 | `ddev-exec` | 按实现计划顺序落地代码、跟踪任务并在收尾阶段驱动验收 | 仅允许用户手动调用；执行完成后必须联动进入 `ddev-gate`，不得停在“代码已写完” |
| ⑤ 验收 | `ddev-gate` | 代码实现完成后逐项核对是否与 spec/detail 文档一致，通过后执行 slop 清理、编码规范审查和注释审查 | 禁止用户手动调用；仅允许由 `ddev-exec` 联动加载；一致性不通过就打回重改，循环直到 pass；规范审查和注释审查按语言路由（C 项目经 c-pro + comment-gen），均通过方可放行 |

> **联动技能**：`ddev-diagram`（画图规范）、`ddev-plan`（拆解执行计划）、`ddev-exec`（执行计划）、`ddev-clean`（被 ddev-gate 调用的代码清理）、`ddev-c-pro`（C 编码规范审查）、`ddev-comment-gen`（注释完整性审查）。

## 三、项目管理

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `ddev-exec` | 按已写好的实现计划顺序执行任务，先做批判性检查，再依次执行并收尾。 | 手动 — 用户明确调用 `ddev-exec` 时 |
| `using-git-worktrees` | 创建隔离的 git worktree，支持多分支并行开发，避免频繁切换分支。 | 自动 — 需要隔离的功能开发时 |
| `git-commit-template` | Conventional Commits 格式的提交消息模板与写作规范。由 `git-commit-standard` 强制加载。 | 自动（被 git-commit-standard 联动加载） |
| `using-superpowers` | 查找和使用执行类 skills 的入口指引。 | 自动 — 开始实际执行任务时 |

## 四、工具与基础设施

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `tool-routing` | 统一检索工具路由规则，调度 `codegraph_*`、`ctx_*`、`grep`/`Read` 三层职责。 | 自动 — 全局加载（由 AGENTS.md 强制执行） |
| `skill` | 管理本地 skills：列出、添加、删除、搜索、编辑、设置向导。 | 自动 — 需要管理 skills 时 |
| `skill-recorder` | 在 skill 使用过程中记录 corrected 和 friction 信号，写入目标 skill 的 `.skillopt/pending/` 目录。 | 自动 — 由 AGENTS.md 全局指令调用 |
| `find-skills` | 帮助用户发现和安装 agent skills。适用场景："how do I do X""find a skill for X""is there a skill that can..." | 自动 — 询问如何实现某功能时 |

## 五、编译与编码

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `compile-commands-init` | 为 C/C++ 项目初始化 compile_commands.json 和 .clangd 配置。Linux 用 bear 生成，Windows 用构建日志+CompilerGen.py 生成。触发词：compile_commands.json、clangd、编译数据库、代码跳转、LSP 配置。 | 自动 |

## 六、调试与测试

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `debug-locate-assistant` | C/C++ 回归定位，精确定位问题所在（文件:行/函数）。 | 自动 — 需要回归定位时 |
| `webapp-testing` | 用 Playwright 对本地 Web 应用进行功能验证、UI 调试、截图和浏览器日志查看。 | 自动 — 需要测试本地 Web 应用时 |

## 七、嵌入式开发

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `embedded-debug-workflow` | 编排"改代码→编译刷写→串口抓日志→可选 USB 触发→检查日志与回传"闭环联调流程。**强制**：配套 skill 各有独立工具，必须调用对应 skill 的工具，禁止自行实现替代品。 | 自动 — 需要嵌入式设备联调时 |
| `embedded-workflow-cache-init` | 初始化项目内 `.agents/cache` 的嵌入式工作流缓存：沉淀 VID/PID、固件产物路径、传输协议参数、KingstVIS 通道映射与测试方法等。 | 自动 — 需要初始化嵌入式调试缓存时 |
| `repo-firmware-flasher` | 基于仓库代码推导刷写参数，复用统一流程完成固件探测、分包或刷写。**强制**：必须调用本 skill 定义的工具。 | 自动 — 需要刷写固件时 |
| `repo-usb-communicator` | 基于仓库代码定位 USB 设备参数，打开设备、发送数据或读取响应。**强制**：必须调用本 skill 定义的工具。 | 自动 — 需要 USB 通信时 |
| `serial-log-debug` | Windows 本地串口调试：抓取 UART 日志、手动发送文本/十六进制命令、查看 TX/RX 轨迹。 | 自动 — 通过串口调试硬件时 |
| `kingstvis-socket` | 通过 SocketAPI 驱动 KingstVIS 逻辑分析仪进行抓取和导出，优先生成 CSV 供 AI 分析。 | 自动 — 需要使用 KingstVIS 时 |

## 八、媒体与数据

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `agent-browser` | 浏览器自动化 CLI：导航页面、填表、点击、截图、数据提取、Web 应用测试。触发词：open a website、fill out a form、click a button、take a screenshot、scrape data 等。 | 自动 |
| `bilibili-analyzer` | 自动分析 B 站视频内容：下载视频、拆解成帧图片、用 AI 分析并生成专题文档或实操教程。 | 自动 — 分析 B 站视频时 |
| `china-news-crawler` | 中国新闻站点内容提取。支持微信公众号、今日头条、网易新闻、搜狐新闻、腾讯新闻。输出 JSON 和 Markdown。 | 自动 — 需要提取中国新闻内容时 |
| `mediacrawler` | 多平台社交媒体数据爬取工具（小红书、抖音、快手、B站、微博）。支持搜索帖子、提取详情、爬取评论。 | 自动 — 需要爬取社交媒体数据时 |
| `hv-analysis` | 横纵分析法（Horizontal-Vertical Analysis）深度研究。纵轴追踪产品/公司/技术从诞生到当下的完整历程，横轴与竞品系统性对比，交叉产出独到洞察，输出排版精美的 PDF 研究报告。触发词：研究一下、帮我分析、深度研究、竞品分析、调研一下等。 | 自动 |
| `algorithmic-art` | 用 p5.js 创建算法艺术：流场、粒子系统、生成艺术等。使用种子随机性和交互式参数探索。 | 自动 — 请求用代码创建艺术/生成艺术时 |

## 九、系统服务（.system/）

以下技能位于 `.system/` 子目录，为各运行时底层提供系统级支持，用户通常无需直接操作。

| 技能 | 说明 |
|------|------|
| `imagegen` | 生成或编辑位图图像：照片、插图、纹理、精灵图、模拟图、透明背景抠图等。 |
| `openai-docs` | OpenAI 产品/API 最新官方文档查询、模型选择与升级指导。 |
| `plugin-creator` | Codex 插件创建与脚手架，生成 `.codex-plugin/plugin.json` 和可选目录结构。 |
| `skill-creator` | 创建有效 skills 的指南与最佳实践。 |
| `skill-installer` | 从精选列表或 GitHub 仓库安装 Codex skills。 |

## 十、其他

| 技能 | 说明 | 触发方式 |
|------|------|----------|
| `customize-opencode` | 编辑或创建 OpenCode 自身配置（opencode.json、.opencode/、插件、MCP 服务器、权限规则等）。 | 自动 — 编辑 OpenCode 配置时 |

---

## ⚠️ 手动调用技能（禁止自动加载）

以下技能**不会被**「技能强制评估」自动匹配。必须由用户明确说出指定触发词才会加载。

### `git-commit-standard` — 标准化提交流程

- **触发词**：「按标准流程提交」「按提交流程提交」（注意：不含"提交""提交一下""commit"等泛化词）
- **说明**：加载后自动联动 `git-commit-template`。向用户确认版本号递进方式后，检查并同步版本元数据、README/changelog、固件产物和发布记录，最后 commit。
- **使用示例**：
  ```
  帮我按标准流程提交
  ```

### `ddev-arch` — 初始化项目架构/硬件基线规范

- **触发词**：用户明确点名 `ddev-arch`，或明确要求初始化项目级架构规范/硬件基线文档
- **说明**：`ddev-arch` **禁止自动加载**。仅允许用户手动调用；进入后初始化项目级长期架构规范，并在嵌入式项目中一并沉淀机型、分区、外设和 GPIO 硬件基线文档，建立模块边界、依赖规则和变更门禁。
- **使用示例**：
  ```
  帮我初始化项目架构文档
  用 ddev-arch 初始化架构和硬件基线
  ```

### `ddev-spec` / `ddev-detail` / `ddev-plan` / `ddev-exec` — 流程类技能（仅手动）

- **触发词**：用户明确点名对应 skill 名，或明确说出“进入 ddev-spec / ddev-detail / ddev-plan / ddev-exec”
- **说明**：这四个流程类 skill 都**禁止自动加载**。只有用户明确要求进入对应阶段时才允许加载；agent 不得基于“看起来下一步该做什么”自行匹配。
- **使用示例**：
  ```
  进入 ddev-spec
  进入 ddev-plan
  用 ddev-exec 开始执行
  ```

### `ddev-gate` — 最终验收门禁（仅 exec 联动）

- **触发方式**：**不接受用户手动调用**；仅允许由 `ddev-exec` 在默认收尾阶段联动加载
- **说明**：`ddev-gate` 不参与自动匹配，也不能由用户直接点名触发。只有 `ddev-exec` 执行完任务、进入默认收尾时，才允许自动联动进入 gate 验收。
- **使用示例**：
  ```
  使用 ddev-exec 执行计划；任务完成后由 exec 自动进入 ddev-gate
  ```

### `grill-me` — 高强度追问式审查

- **触发词**：用户明确点名使用 `grill-me` 或说"grill me"
- **说明**：通过一次只问一个问题的高强度追问，逐步压实计划或设计的每个关键分支与决策。禁止自动触发，只有用户主动调用时才加载。
- **使用示例**：
  ```
  对这个方案 grill me
  grill-me 审查我的设计
  ```

### `skill-init` — 初始化 Skill Optimizer 系统

- **触发词**：「初始化 skill-optimizer」或「setup skill-optimizer」
- **说明**：一次性部署，将 optimizer-agent 和 gate-agent 部署到平台配置，追加每轮信号记录 checklist 到 AGENTS.md。
- **使用示例**：
  ```
  初始化 skill-optimizer
  setup skill-optimizer
  ```

### `skill-optimizer` — 基于信号优化 Skill

- **触发词**：「优化 <skill 名>」「/optimize <skill 名>」或「skill-optimizer」（展示信号面板）
- **说明**：8 步优化管线（Confirm→Load→Triage→Deep Read→Reflect→Dry-run→Gate→Update），基于 `skill-recorder` 记录的 corrected/friction 信号优化目标 skill。
- **使用示例**：
  ```
  优化 tool-routing
  /optimize code-review
  skill-optimizer
  ```

### `repository-encoding-normalizer` — 仓库编码规范化

- **触发词**：用户明确要求「规范化源码仓库文件编码」
- **说明**：将源码统一为 UTF-8 with BOM，编译时由 `gbk_encode.exe` 自动检测含 CJK 字面量的文件并生成 GBK 编码副本。附带专用脚本工具：`scan_encoding.py`、`normalize_encoding.py`、`check_mojibake.py`、`gbk_encode.exe`、`gbk_build.py`。
- **⚠️ 警告**：此操作会批量修改仓库文件编码，属破坏性操作。
- **使用示例**：
  ```
  帮我规范化这个仓库的源码编码
  ```

---

## 技能工具强制规则

部分技能（尤其是嵌入式、调试类）提供配套的可执行工具脚本。加载这些技能后，**必须使用其提供的工具**，禁止自行实现替代品。加载技能时会有 `Base directory for this skill:` 提示，结合 SKILL.md 中的工具路径即可定位工具脚本。

以下技能提供专用工具，使用时务必遵循强制规则：

- `embedded-debug-workflow`、`embedded-workflow-cache-init`、`repo-firmware-flasher`、`repo-usb-communicator`、`serial-log-debug`、`kingstvis-socket`、`repository-encoding-normalizer`
