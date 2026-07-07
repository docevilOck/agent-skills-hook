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
| 调试日志 | 新增 `prt_printf`/`PRT_LOG`/`printf`/`__log`/`PRT_DBG` 等调试打印语句 |
| 临时注释标记 | 含 `TODO`、`DEBUG`、`test`、`temp`、`FIXME`、`HACK` 标记的新增代码 |
| 注释掉的旧实现 | 被 `//` 或 `#if 0` 注释掉的原有代码行 |
| 临时变量 | 仅为调试新增的计数器、状态 dump 变量 |
| 调试配置值 | 为调试临时改小的超时、延迟、重试次数等魔数 |
| 个人 gitignore | `.gitignore` 中新增的个人工具/脚本路径 |
| 日志宏开关 | 临时开启的 debug 宏（`#define PRT_DEBUG 1`） |
| 死代码 | 被注释掉但未删除的函数/逻辑块 |

以下改动视为**有效修复，应提交**：

| 类别 | 识别特征 |
|------|---------|
| 逻辑修正 | 条件判断、边界处理、状态机转换、循环逻辑的修正 |
| 功能代码 | 新特性、新接口、新函数、新配置项 |
| 错误处理 | 新增 return 值检查、null 判断、资源释放、cleanup 路径 |
| 协议/结构体 | 通信协议字段、共享内存结构、RPMSG 接口的增删改 |
| 配置项 | 产品功能配置、硬件参数、版本号（非临调目的） |
| 文档 | `docs/` 下架构文档、接口说明、README |
| 代码清理 | 删除死代码、修复 warning、字段重命名 |

## 执行流程

### 第一步：扫描全部改动

```bash
git status --porcelain          # 所有未提交文件列表
git diff --cached               # 已暂存区改动
git diff                        # 工作区未暂存改动
```

### 第二步：逐文件分类

对每个有改动的文件：
1. `git diff <file>` 查看完整改动
2. 逐 hunk 按判定标准分类为「有效修复」或「调试改动」
3. 汇总为分类表

### 第三步：向用户展示分类结果并确认

以表格展示：

```
| 文件 | 有效修复 | 调试改动 | 操作 |
|------|---------|----------|------|
| src/module/prt_usb_printer.c | 错误处理 2 处、逻辑修正 1 处 | debug printf 3 处 | 部分提交 |
| prt_z5_cfg.h | 新增配置项 1 处 | — | 全部提交 |
| .gitignore | — | 个人工具路径 | 跳过 |
```

**必须等待用户确认后才执行暂存操作。**

### 第四步：选择性暂存

- **全部有效修复** → `git add <file>`
- **全部调试改动** → 跳过此文件，不暂存
- **混合改动** → 使用 `git apply --cached` 方式，仅将有效 hunk 写入暂存区：

```bash
# 1. 生成完整 diff
git diff <file> > /tmp/selective_<file>.patch

# 2. 编辑 patch 文件，删除调试改动的 hunk（保留有效修复的 hunk）
#    patch 文件中每个 hunk 以 @@ ... @@ 开头，删除整个调试 hunk 块

# 3. 将编辑后的 patch 应用到暂存区
git apply --cached /tmp/selective_<file>.patch

# 4. 验证暂存区内容
git diff --cached <file>
```

**编辑 patch 文件注意事项**：
- 每个 hunk 以 `@@ -old_start,old_count +new_start,new_count @@` 开头
- 删除整个调试 hunk（从 `@@` 行到下一个 `@@` 行之前，或到文件末尾）
- 不要修改 hunk 内部的上下文行号，`git apply` 会自动调整

### 第五步：生成 commit message 并提交

按 `git-commit-v85x` 规范生成标题。TYPE 根据内容选 `FIX`/`CHG`/`ADD`，SCOPE 和 PRODUCT 按改动路径确定。

```bash
git commit -m "[FIX][MKMPP][P1] 修复 USB 打印机断连后资源泄漏问题"
```

正文（可选）仅描述有效修复内容，不提及跳过的调试改动。

### 第六步：验证

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
+ prt_printf("[DEBUG] usb_state=%d, ret=%d\n", state, ret);

  // 有效修复（提交）：
- if (ret < 0) return;
+ if (ret < 0) { usb_cleanup(); return -1; }
```

### 场景 2：临时配置值 + 正式配置项

```diff
  // 调试改动（不提交）：
- #define USB_TIMEOUT_MS  5000
+ #define USB_TIMEOUT_MS  100

  // 有效修复（提交）：
+ #define USB_RETRY_MAX   3
```

### 场景 3：注释旧实现 + 新实现

```diff
  // 调试改动（不提交）：
+ // old_dispatcher();  // TODO: remove after verify

  // 有效修复（提交）：
+ new_dispatcher_v2();
```

### 场景 4：纯调试文件

如果某个文件的所有改动都是调试目的（如只在文件头加了 `#define DEBUG 1`），整文件跳过不提交。

## 与 git-commit-v85x 的关系

- `git-commit-v85x`：正常提交流程，提交所有暂存改动
- `git-commit-select`：先筛选，仅暂存有效修复，再走 `git-commit-v85x` 格式提交

两者不互斥。当用户说"筛选提交"时，先走本 skill 的筛选→暂存流程，再按 v85x 格式生成 message 并提交。
