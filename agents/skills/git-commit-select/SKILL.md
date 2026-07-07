---
name: git-commit-select
description: 筛选未提交改动，仅提交有效代码修复，保留调试/临时改动在工作区不提交也不删除。触发词：筛选提交、选择性提交、只提交有效改动、commit real changes、跳过调试提交、debug changes。
---

# git-commit-select — 选择性提交（去调试，留改动）

## 概述

从当前未提交改动中自动筛选"有效代码修复"，仅提交这些改动；调试/临时代码保留在工作区，既不提交也不删除。

## 触发条件

**仅限手动调用**，不自动匹配。触发词示例：
- "筛选提交" / "选择性提交"
- "只提交有效改动" / "跳过调试代码提交"
- "commit only real changes, skip debug"

## 调试改动判定标准

以下改动视为**调试/临时改动，不提交**：

| 类别 | 识别特征 |
|------|---------|
| 调试日志 | 新增调试打印语句（`printf`、`fprintf(stderr,`、`console.log`、`NSLog`、`log::`、`print(`、`LOG_DEBUG`、`pr_dbg` 等），或明显仅用于开发期观察的输出 |
| 临时注释标记 | 含 `TODO`、`DEBUG`、`test`、`temp`、`FIXME`、`HACK` 标记的新增代码 |
| 注释掉的旧实现 | 被 `//` 或 `/* */` 或 `#if 0` 注释掉的原有代码行 |
| 临时变量 | 仅为调试新增的计数器、状态 dump 变量 |
| 调试配置值 | 为调试临时改小的超时、延迟、重试次数等魔数 |
| 个人 gitignore | `.gitignore` 中新增的个人工具/IDE/脚本路径 |
| 日志宏开关 | 临时开启的 debug 宏（`#define DEBUG 1`、调试级别调高） |
| 死代码 | 被注释掉但未删除的函数/逻辑块 |

以下改动视为**有效修复，应提交**：

| 类别 | 识别特征 |
|------|---------|
| 逻辑修正 | 条件判断、边界处理、状态机转换、循环逻辑的修正 |
| 功能代码 | 新特性、新接口、新函数、新配置项 |
| 错误处理 | 新增 return 值检查、null 判断、资源释放、cleanup 路径 |
| 协议/结构体 | 通信协议字段、数据结构、接口定义的增删改 |
| 配置项 | 产品功能配置、硬件参数、版本号（非临调目的） |
| 文档 | `docs/` 下架构文档、接口说明、README、CHANGELOG |
| 代码清理 | 删除死代码、修复 warning、字段重命名、重构 |

## 执行流程

### 第一步：确认当前仓库的 commit 规范

- 检查工作区是否有 `CLAUDE.md`、`CONTRIBUTING.md` 或 `.github/` 下的提交规范说明
- 如果有仓库专属的 commit skill（如 `git-commit-<repo>`），优先使用其格式生成 commit message
- 如果没有，使用标准的 Conventional Commits 或用户指定的格式

### 第二步：扫描全部改动

```bash
git status --porcelain          # 所有未提交文件列表
git diff --cached               # 已暂存区改动
git diff                        # 工作区未暂存改动
```

### 第三步：逐文件分类

对每个有改动的文件：
1. `git diff <file>` 查看完整改动
2. 逐 hunk 按判定标准分类为「有效修复」或「调试改动」
3. 汇总为分类表

### 第四步：向用户展示分类结果并确认

以表格展示：

```
| 文件 | 有效修复 | 调试改动 | 操作 |
|------|---------|----------|------|
| src/main.c | 错误处理 2 处、逻辑修正 1 处 | debug printf 3 处 | 部分提交 |
| config.h | 新增配置项 1 处 | — | 全部提交 |
| .gitignore | — | 个人工具路径 | 跳过 |
```

**必须等待用户确认后才执行暂存操作。**

### 第五步：选择性暂存

- **全部有效修复** → `git add <file>`
- **全部调试改动** → 跳过此文件，不暂存
- **混合改动** → 使用 `git add -p <file>` 交互式选择 hunk，或手动编辑 patch：

```bash
# 方案 A：交互式（推荐，hunk 少时）
git add -p <file>
# 按 y/n/s 逐 hunk 选择

# 方案 B：手动编辑 patch（hunk 多、需要细粒度控制时）
git diff <file> > /tmp/selective_<file>.patch
# 编辑 /tmp/selective_<file>.patch，删除调试改动的 hunk
# patch 文件中每个 hunk 以 @@ ... @@ 开头，删除整个调试 hunk 块
git apply --cached /tmp/selective_<file>.patch
```

**编辑 patch 文件注意事项**：
- 每个 hunk 以 `@@ -old_start,old_count +new_start,new_count @@` 开头
- 删除整个调试 hunk（从 `@@` 行到下一个 `@@` 行之前，或到文件末尾）
- 不要修改 hunk 内部的上下文行号，`git apply` 会自动调整

### 第六步：生成 commit message 并提交

根据第一步确认的仓库规范生成 commit message。如有仓库专属 commit skill 则调用它；否则按通用 Conventional Commits 格式。

```bash
git commit -m "<生成的 commit message>"
```

正文（可选）仅描述有效修复内容，不提及跳过的调试改动。

### 第七步：验证

```bash
git diff                        # 确认调试改动仍在工作区，未被提交
git diff --cached               # 确认暂存区已清空（提交后）
git log -1 --stat               # 确认提交内容正确
```

## 安全检查

- **绝不删除工作区改动**：不使用 `git checkout -- <file>` / `git restore`
- **不强制 reset**：不使用 `git reset --hard`
- **可回滚**：提交后若发现问题，`git reset HEAD~1` 即可撤销
- **操作前展示**：暂存操作前必须展示分类结果并获用户确认

## 常见场景示例

### 场景 1：调试日志 + 错误处理混合

```diff
  // 调试改动（不提交）：
+ printf("[DEBUG] state=%d, ret=%d\n", state, ret);

  // 有效修复（提交）：
- if (ret < 0) return;
+ if (ret < 0) { cleanup(); return -1; }
```

### 场景 2：临时配置值 + 正式配置项

```diff
  // 调试改动（不提交）：
- #define TIMEOUT_MS  5000
+ #define TIMEOUT_MS  100

  // 有效修复（提交）：
+ #define RETRY_MAX   3
```

### 场景 3：注释旧实现 + 新实现

```diff
  // 调试改动（不提交）：
+ // old_handler();  // TODO: remove after verify

  // 有效修复（提交）：
+ new_handler_v2();
```

### 场景 4：纯调试文件

如果某个文件的所有改动都是调试目的（如只在文件头加了 `#define DEBUG 1`），整文件跳过不提交。
