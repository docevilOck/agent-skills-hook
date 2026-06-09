---
name: git-commit-standard
description: 【禁止自动加载 — 不可被 skill-forced-eval 匹配】仅限用户手动调用。加载后必须向用户确认版本号是否递进及递进方式、更新固件产物和 README。触发词仅限"按标准流程提交""按提交流程提交"，不含"提交""提交一下""commit"等泛化提交词。
---

# git-commit-standard

## 强制依赖

**加载本 skill 时必须同时加载 `git-commit-template` 并严格遵循其书写规范。** 本 skill 定义提交流程和门禁，`git-commit-template` 定义 commit message 的模板、字段和写作风格。

## Overview

用于执行仓库约定的提交、版本、固件产物归档和 changelog/release record 同步。核心原则：**提交前先确认仓库规则，再默认检查并同步版本元数据、README/changelog、固件产物和发布记录，最后 commit**。

**默认行为（最高优先级）：每次执行任何 commit 相关操作时，只要存在代码改动，就必须先重新编译并更新最新固件产物，再同步 README/changelog 总结。** 这条规则对 `commit` 和 `amend` 一视同仁，不受是否修改版本号影响；它是本 skill 的硬性门禁，不能当作额外功能、可选增强或 commit message 里的“变更点”。只有仓库规则、用户明确要求或历史证据明确证明本次没有对应固件/README/changelog 记录项时，才可跳过，并在执行记录中说明依据。禁止把“未递进版本”“只是 amend”“只是 fix/中间提交”作为跳过固件或履历同步的理由。

该 skill 设计为通用技能：不要写死某个仓库的版本头、固件目录、构建宏、产物命名或 README 路径；这些信息必须从当前仓库的配置、AGENTS.md、历史提交和实际文件结构中推导或维护。

## When to Use

必须使用：

- 用户明确要求遵循标准提交流程。
- 用户说"按标准流程提交""按提交流程提交"等精确触发词。注意：普通提交请求（如"提交""提交一下""commit"）不应匹配本 skill——这些请求仅应加载 `git-commit-template`，不得触发版本递进确认、固件重编译等本 skill 的重流程。

**禁止使用：**

- **agent 不得以任何理由自动加载本 skill**（包括但不限于：AGENTS.md 配置、skill-forced-eval、上下文推断、检测到 commit 操作）。
- 只做代码调研、diff 查看、问题分析，不准备提交。

## Repository Rule Discovery

每个仓库先按下面顺序找规则，不要凭经验写死路径：

1. 读取当前目录和上层 `AGENTS.md` / `README` / release 文档。
2. 查找仓库内 release 配置文件，优先级建议：
   - `.agents/release-config.md`
   - `.agents/git-commit-standard.md`
   - `.release-config.md`
   - 项目自定义说明文件。
3. 搜索版本来源：`FIRMWARE_VERSION`、`VERSION_BETA`、`VERSION`、`APP_VERSION`、`BUILD_VERSION`、`RELEASE_VERSION` 等。
4. 搜索产物归档目录：`firmware_record/`、`release/`、`releases/`、`dist/`、`out/`、`bin/` 等。
5. 搜索 changelog/release record（穷举搜索，不得遗漏）：
   - 根目录及一级子目录下的 `README.txt`、`ReadMe.txt`、`readme.txt`、`CHANGELOG.md`、`RELEASE.md`
   - `arch/*/change log/`、`arch/*/change_log/`、`arch/**/readme*` 等非标准路径（注意包含空格、大小写变体和多级嵌套）
   - `docs/release/`、`doc/`、`release-notes/` 等常见子目录
   - 必须使用递归 glob（如 `**/readme*`、`**/change*log*/**`），不能只在根目录搜索
   确认找到的每个 readme/changelog 文件的完整路径和格式，以便后续更新。
6. 查看历史提交：找最近一次版本递增、固件归档、README/changelog 更新的提交，确认真实格式。

如果规则不明确，先向用户确认；不要默认 fallback 到某个仓库的规则。

## Repository Config / State File

允许在仓库中维护一个小型配置/状态文件，用来记录跨 commit 的 release 信息。推荐路径：`.agents/release-config.md`。如果仓库已有等价文件，沿用已有文件。

该文件可记录：

```markdown
# Release Config

## Version Sources
- default: `path/to/version.h`, macros: `FIRMWARE_VERSION`, `VERSION_BETA`
- variant-a: `path/to/version.h`, compile macro/env: `<VARIANT_MACRO>`, artifact prefix: `<product-variant>`

## Build Variants
| variant | build command | compile macro/env | output artifact | archive dir | archive name pattern |
|---|---|---|---|---|---|
| default | `<repo build command>` | none | `<out artifact path>` | `<archive dir>` | `<artifact-prefix>_v<version>_<beta>.bin` |

## Changelog
- file: `path/to/ReadMe.txt`
- insert: top
- block separator: `================================================================`
- fields: version, date, author, change points

## Release State
- last_version_bump_commit: `<commit>`
- last_released_version: `<version>`
- last_archived_artifacts:
  - `<path>`
```

用途：当“多个 commit 才递进一次版本”时，用 `last_version_bump_commit` 或上一个版本记录位置作为汇总边界，不要只拿当前 commit 写 changelog。

## Version Bump Rules

**硬性门禁：每次加载本 skill 执行提交，必须向用户确认版本号是否递进及递进方式，必须更新固件产物，必须更新 README。不存在例外。**

### 修改版本宏前的预定位

向用户确认版本号递进方式之前，必须先完成以下两层定位，避免改错宏或改错分支：

**第一层：定位活跃机型宏块。** 在版本配置文件中搜索机型宏定义（如 `#define TP806L`），确认当前活跃的 `#ifdef`/`#if` 分支区域；只在活跃分支内修改版本号。常见错误：改了非活跃分支的版本宏，版本号未实际生效。

**第二层：区分显示控制宏与真实版本标识宏。** 注意某些宏仅控制 UI 显示（如 `VERSION_BETA 0` 表示自检页不显示 beta 编号），并非真实版本号；真实版本标识宏通常是字符串常量（如 `VERSION_BETA_TEST "v1.0.1"`）。参考 `git log` 确认历史开发者实际修改的是哪个宏。常见错误：把显示控制宏从 0 改成 1，而非修改真实版本字符串。

1. 向用户确认：本次是否递进版本号、递进哪个字段（通常 beta 递增 1）。
2. 递进后重新编译目标变体，生成新版本固件。
3. 将构建产物按历史命名规则复制到归档目录。
4. 汇总变更内容，按仓库模板更新 README/changelog（插入顶部）。
5. 多个变体有不同宏/版本时，分别确认目标变体，不要只改默认分支。
6. 同一版本有多条提交时，changelog 要汇总所有变更，拆为多个 1、2、3 条，不要拆成多条版本记录。

## Changelog / README Rules

写 changelog 前必须确认：

- 文件路径和格式来自仓库历史，不要新造格式。
- 插入位置是顶部、底部还是按版本排序。
- 版本字段是否带产物后缀，如 `.bin`。
- 作者字段来自 `git config user.name`，除非仓库规则另有要求。
- 日期格式沿用仓库历史；若仓库没有固定格式，使用 `YYYY.MM.DD`。

生成 changelog 内容时：

1. 找到汇总边界：
   - 优先使用 `.agents/release-config.md` 中的 `last_version_bump_commit`。
   - 否则用上一个 README/changelog 版本记录对应的 commit。
   - 再否则询问用户。
2. 汇总边界之后的所有相关 commit。
3. 合并成发布视角的“修改原因 / 修改依据 / 修改方法 / 修改影响”或仓库既有字段。
4. `ReadMe.txt` / changelog 默认写精简版版本摘要，不写详细实现过程；除非用户明确要求详细版，否则一律按发布说明风格输出，而不是设计文档风格。
5. 描述保持短句，优先写关键改动目的、关键方法、关键影响，不展开内部处理逻辑。
6. 每个一级字段下的子项默认不超过 3 点；先压缩语言，再检查是否还能继续合并同类项，避免出现 4 条以上细碎分点。
7. 在不丢失关键信息的前提下，优先合并为更高层级概括表达；能写成一条摘要时，不拆成多条函数级、协议级、状态级细节。
8. “修改方法”只保留必要方法摘要，不写过细实现细节，默认不要写：
   - 具体函数级处理步骤
   - 内部状态机细节
   - 输入输出字节级变化
   - 调试日志点布置
   - 具体兼容分支和兜底路径
9. “修改影响”只保留必要的用户侧/业务侧结果，不写过细技术影响，默认不要写：
   - 某种旧报文/旧字段/旧格式会被拒绝
   - 某个中间态如何切换
   - 某个内部 session / payload 如何分段推进
   - 过细的协议兼容边界
10. 如果某些细节更适合放设计文档、计划文档、回归文档或代码注释，就不要塞进 `ReadMe.txt`。
11. 推荐摘要表达示例：
    - 好示例：`收口鉴权入口`、`补充打印阻断`、`完善回归日志点`
    - 坏示例：逐条罗列函数调用链、协议字段兼容分支、状态切换条件、session/payload 分段推进细节
12. 不要把每个 commit 原文机械粘贴；要按功能归并。
13. 若仓库历史或用户要求“一版本一条”，README/changelog 必须以版本为主键；同一版本内多次修正、回归、补充说明都合并到同一个版本块内，不要拆成多条相同版本记录。
14. README/changelog 总结允许在既有模板条目下继续分点或缩进分层；当同一字段内包含多个独立事项、影响面或风险点时，使用二级分点，不要用长句和分号串联多个主题。
15. 版本履历只写业务结果、行为变化、兼容性、风险和测试维护有意义的信息；不要写流程性负面或后续安排，例如“本次不递进版本号”“不修改版本宏”“不归档固件产物”“后续需要覆盖固件”“已按流程检查”。这些内容只能放在任务汇报或内部执行记录中。
16. 如果本次是非递进版本但有代码改动，也要先检查 README/changelog 是否需要补记录，再判断是否能跳过；不要默认“不升版本=不用同步”。

## Firmware Artifact Rules

当仓库要求归档固件产物时：

1. 先确认目标变体和构建宏：default / factory / esc / 300dpi / bootloader / product tool 等。
2. 运行仓库真实构建命令生成新产物。
3. 根据版本宏、构建宏和历史命名规则计算归档文件名。
4. 将构建产物复制到对应历史目录。
5. 若同一版本需要多个变体，逐个构建、逐个命名、逐个归档。
6. 归档前确认目标文件是否已存在。若目标文件是当前版本既有归档，且用户或仓库流程要求“更新当前版本产物”，可用最新构建产物覆盖并记录验证证据；若版本/变体/目标文件不明确，或覆盖跨版本、跨变体、历史冻结产物，必须先询问用户。
7. 归档产物应进入 commit，除非仓库规则明确忽略产物。
8. 即使本次不递增版本，只要存在会进入固件镜像的代码或构建输入改动，默认也要构建并更新当前版本对应的固件产物。只有仓库规则、用户明确要求或历史证据明确证明本次没有固件记录要求时，才可不归档；跳过时必须说明证据。禁止用“未递进版本”“只是 amend”“只是 fix”作为跳过理由。
9. amend 场景下若版本号、版本命名字段、构建宏、产物命名规则、README/changelog 汇总范围或任何构建输入发生变化，必须把当前版本对应的归档产物视为失效，重新构建、重新复制/覆盖归档文件，并把更新后的产物与文档一起纳入 amend。

不要假设所有仓库都把产物放在同一个目录；必须从历史文件和 git log 中确认。

## Commit Message Rules

提交正文的模板、字段定义、写作风格和正反示例由 `git-commit-template` 定义。使用本 skill 时必须同时遵循 `git-commit-template` 的所有书写规范。关键约束摘要：

- 标题聚焦本次提交目的，不把长版本信息塞进标题。
- 正文必须和版本头、README/changelog、归档产物一致。
- 正文只描述本次真实业务、代码、文档、兼容性和影响变化；不要写提交流程、是否递进版本、是否归档固件、后续应该做什么等流程话术。
- 不要把"已按默认流程检查/同步固件和 README/changelog"写成 commit message 的变更点或原因。

## Operating Pattern

执行 commit 前按顺序处理：

1. 确认用户确实要求提交。
2. 读取仓库规则：AGENTS、release 配置、历史提交、版本文件、changelog 文件、产物目录。
3. 硬性门禁：若存在任何代码改动（即使未递增版本），按序执行：
   a. 重新编译目标变体（执行仓库真实构建命令）
   b. 将构建产物按历史命名规则复制到归档目录
   c. 验证产物已存在于归档目录中
   此门禁对 commit 和 amend 一视同仁，不可跳过、不可推迟到后续步骤。
4. 分别确认本次是否触发版本递增、README/changelog 汇总和固件归档；版本递增不是固件归档的前置条件。
5. 若触发版本递增：
    - 更新版本源文件。
    - 构建目标变体。
    - 按历史命名复制/归档产物。
    - 汇总当前版本范围内多个 commit 的 changelog 并更新 README/changelog。
    - 更新 `.agents/release-config.md` 的 release state（如果仓库采用该文件）。
6. 若未触发版本递增但存在代码改动：
    - 仍要检查 README/changelog 和固件产物是否需要同步。
    - 若代码会进入固件运行镜像，必须先重新构建并更新当前版本对应固件产物。
    - 若仓库规则或用户明确不需要记录，才可跳过，并记录证据。
7. 若本次是 amend：存在任何代码改动，或涉及版本号/构建输入/产物命名等变化的，必须重新构建目标变体→复制产物到归档目录→验证归档→重新暂存。不可假设前次 commit 的产物仍然有效。
8. 运行验证：diff check、必要的 LSP/构建/测试、产物存在性和文件名检查。
9. 暂存源码、版本文件、changelog、归档产物、release 配置文件；如果是 amend，必须确认重编译生成的新产物已重新进入暂存区。
10. 使用仓库模板创建 commit；commit message 只写实际变更，不写“执行了默认固件/README 同步检查”“不递进版本”“不归档固件”等流程话术。
11. 提交后验证工作区状态、最新 commit message、Change-Id（若 Gerrit hook 存在）。

## Common Mistakes

- 把“每个 commit”都当成“每次版本递增”。
- 代码有改动却因为没递增版本，就漏掉固件和 README/changelog 同步检查。
- 把“未递进版本”“只是 amend”“只是 fix/中间提交”当作跳过固件产物的理由。
- amend 前改了版本号、版本宏或构建输入，却没有重新编译固件、刷新归档产物并重新暂存。
- 把固件和 README/changelog 同步检查当成“可选项”，等用户提醒才做；正确做法是每次 commit 默认执行。
- 在 commit message 里写“按默认流程检查/同步固件和 README”，造成提交说明噪音；默认流程不要写入提交说明。
- 在 commit message 或版本履历里写“不修改版本宏”“不归档固件产物”“后续需要更新固件”等流程说明。
- changelog 只写当前 commit，漏掉同一版本从上次 release 后累计的多个 commit。
- 同一个版本拆成多条 README/changelog 记录，而用户或仓库规则要求一版本一条。
- 多个独立影响面挤在一条长句里，导致兼容性、密钥策略、payload/session 行为和诊断能力混在一起。
- README/ReadMe.txt 写成设计文档，把函数步骤、协议兼容细节、状态切换或字节级变化塞进版本履历。
- 一级字段下分出 5-8 条碎点，没有先压缩语言、合并同类项。
- README 只写当前提交摘要，没有覆盖整个版本范围内的提交内容。
- 只改版本头，不更新 README/changelog。
- 只构建不归档，或归档文件名仍是临时 `out/` 名称。
- 不看历史目录，把 ESC/300DPI/工厂/boot 产物放到默认固件目录。
- 覆盖已有固件产物而不确认。
- 把某个仓库的路径写死到通用 skill。
- 忘记把 release 配置/状态文件纳入 commit，导致下次无法知道汇总边界。
- 修改版本号时未先定位活跃机型宏块，改到了非活跃分支的宏。
- 混淆显示控制宏与真实版本标识宏，修改了 UI 显示控制宏而非真实版本字符串。
- 搜索 readme/changelog 时只在根目录查找，遗漏 `arch/*/change log/` 等深层嵌套路径。

## Minimal Checklist

提交前至少确认：

- [ ] 已确认用户要求提交。
- [ ] 已加载本 skill 和 `git-commit-template`（强制依赖）。
- [ ] 已读取仓库 release/commit 规则，而不是套用其它仓库路径。
- [ ] 已分别判断本次是否递增版本、是否更新 README/changelog、是否更新固件产物；未把“不递进版本”作为跳过依据。
- [ ] 若有代码改动，已先重新构建并更新最新固件产物；若跳过，已有用户/规则/历史证据。
- [ ] 若递增版本，已更新版本源、README/changelog、固件归档产物和 release state。
- [ ] 若本次为 amend，凡是涉及版本号、版本宏、构建输入、release 配置或产物命名变化，或存在任何代码改动，均已重新构建、重新归档并重新暂存更新后的固件产物与相关文件。
- [ ] README/changelog 汇总范围正确，覆盖同一版本内多个 commit；若要求一版本一条，已合并到同一版本块，并用二级分点表达独立事项。
- [ ] `ReadMe.txt` / changelog 已按精简版版本摘要写法输出：默认发布说明风格、短句概括、每个一级字段子项默认不超过 3 点，且已合并同类项。
- [ ] `修改方法`、`修改影响` 未写入函数级、协议级、状态级、字节级、session/payload 分段或调试日志布置等过细细节；相关内容已留在更合适的设计/计划/回归/注释位置。
- [ ] README/changelog 和 commit message 未包含“不递进版本”“不修改版本宏”“不归档固件产物”“后续应该”等流程话术。
- [ ] 固件产物文件名、目录和构建宏与历史规则一致。
- [ ] 已运行必要验证并记录结果。
- [ ] commit message 与版本/README/产物一致，且符合 `git-commit-template` 规范。
- [ ] 提交后工作区状态和 Change-Id（如适用）已验证。
