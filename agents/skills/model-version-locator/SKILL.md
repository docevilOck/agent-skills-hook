---
name: model-version-locator
description: 定位固件仓库中的机型宏和版本号。当需要确认当前活跃机型、从 `*_cfg.h` 中提取版本宏（VERSION_MAJOR/MINOR/TEST/BETA）、解析机型选择机制（`#ifdef` 链或整数枚举）、或发现配置头文件位置时使用。适用于多种固件仓库布局（arch-based、project-based、flat src/）。应由 git-commit-standard 和 git-commit-template 在生成提交信息前加载。
---

# 机型版本定位器

给定机型名，定位配置头文件，识别活跃的机型选择分支，提取版本宏。通过多策略决策树适配多样化的固件仓库结构。

## 发现决策树

按顺序执行策略，命中即停。

### 1. 定位配置头文件

搜索定义版本宏或机型标识的文件。按顺序尝试：

| 优先级 | 模式 | 示例 |
|--------|------|------|
| 1 | `**/<机型名>_cfg.h`（任意深度） | `arch/stm32/pm251/pm251_cfg.h` |
| 2 | `arch/**/<机型名>_cfg.h` | `arch/gd32e50x/tp805l/tp805l_cfg.h` |
| 3 | `project/**/<机型名>_cfg.h` | `project/pos/i9/i9_cfg.h` |
| 4 | `<机型目录>/src/prt_firmware_download*.h` | HM 系列版本文件 |
| 5 | 同时包含机型名和 `VERSION_MAJOR` / `FIRMWARE_VERSION` 的文件 | 任意遗留布局 |

校验：打开的文件必须包含 `VERSION_MAJOR`、`FIRMWARE_VERSION`、`PRINTER_NAME` 或 `MACHINE_CODE` 中至少一项。

如果机型名未知，从以下来源推断：
- `git branch --show-current` → 提取机型后缀
- 近期的 `git log --oneline --grep="机型\|model"` → 扫描机型宏名称
- `grep -l "<关键词>" **/*_cfg.h` → 模糊匹配

### 2. 识别活跃机型变体

配置头文件通常采用以下选择机制之一：

**命名宏开关**（最常见）：
```c
#define TP80R            // ← 活跃
//#define TP80G          // ← 注释掉 = 非活跃
```

**整数枚举选择器**：
```c
#define PRINTER_MODEL (31)
```

**Makefile / 命令行注入**：寻找 `MODEL_FROM_CMDLINE`、`MODEL_DEFINE_BY_MAKEFILE`、`UMS_DEF_BY_MAKEFILE` 等守卫宏——活跃机型可能由构建时注入。检查构建系统（Makefile、SConscript、.bat）中的 `-D` 标志或 project/model 变量。

如果配置使用 `#if`/`#elif` 链，通过匹配活跃机型标识与 `#if defined(MODEL)` 条件来追踪哪个分支生效。

### 3. 提取版本宏

存在两种主要版本格式：

**A. 四字段数值型**（最常见）：
```
VERSION_MAJOR + VERSION_MINOR + VERSION_TEST + [VERSION_USER] + VERSION_BETA
```

**B. 字符串字面量**（HM 系列等）：
```
FIRMWARE_VERSION = "V1.2.61"
FIRMWARE_VERSION_BETA = "BETA1"  (可选)
```

同时收集 `HARDWARE_MAJOR` / `HARDWARE_MINOR` / `HARDWARE_TEST`（若存在）。

### 4. 在正确的作用域内读取

如果配置使用 `#if`/`#elif`/`#else`/`#endif` 链：
- 找到激活当前机型的 `#define` 或 `#if defined()` 行
- 向下追踪到匹配的 `#elif`/`#else`/`#endif`——版本宏位于此块内
- 只读取活跃分支的宏；忽略非活跃分支中的值

如果配置没有条件分支（单机型文件）：直接读取。

## 输出格式

```
机型: <活跃机型标识>
来源: <配置头文件路径>:<机型宏所在行号>
变体机制: <命名宏开关 | 整数枚举 | 构建注入>
版本:
  MAJOR=<n> MINOR=<n> TEST=<n> [USER=<n>] BETA=<n>
  → <版本字符串>
```

如果 `VERSION_USER` 不存在，省略不写。如果 `FIRMWARE_VERSION` 是字符串字面量，直接使用。

## 版本履历发现

如果需要查找 changelog/发布记录：

| 优先级 | 模式 |
|--------|------|
| 1 | `project/**/<机型>/1_log/*_readme.*` |
| 2 | `arch/**/<机型>/change*/**/*readme*.*` |
| 3 | `arch/**/<机型>/*_readme.*` |
| 4 | `readme/*_readme.*`（遗留） |
| 5 | 机型目录附近的 `**/ReadMe.txt`、`**/CHANGELOG*` |

## 参考

- [固件配置模式](references/cfg-patterns.md) — 各仓库布局的具体示例
