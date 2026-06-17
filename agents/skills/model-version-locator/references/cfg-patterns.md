# 固件配置模式

## 目录布局

### Arch-based（第三代，最常见的新仓库）

```
repo/
  arch/<mcu系列>/<机型>/
    <机型>_cfg.h          ← 配置头文件
    <机型>_readme.txt     ← 版本履历（有时在此）
```

示例：TP80X_MCU_EPRT、TP805L_MCU_EPRT、TP80K、PT56X、PM251、N31、IT4B、HM-A300E、HM_T300_PRO、HM_A300S、A200U

### Project-based（TP80X_PRT_FRAME）

```
repo/
  project/<子项目>/<机型>/
    <机型>_cfg.h          ← 配置头文件
    1_log/<机型>_readme.txt ← 版本履历
```

### Flat src/（遗留布局）

```
repo/
  src/misc/includes.h      ← 版本宏在单体头文件中
  readme/<机型>_readme.txt ← 版本履历
```

## 机型选择机制

### 模式 A：命名宏开关

```c
// 一个活跃，其余注释掉
#define TP80R
//#define TP80G
//#define TP80U

// 基于活跃宏的条件编译块
#if defined(TP80R)
    #define VERSION_MAJOR   2
    #define VERSION_MINOR   1
    // ...
#elif defined(TP80G)
    #define VERSION_MAJOR   1
    // ...
#endif
```

**识别方法**：grep 连续的 `#define 机型名` / `//#define 机型名` 对。未注释的是活跃项。

**适用仓库**：TP80X_PRT_FRAME、TP80K、TP805L_MCU_EPRT、HM-A300E、HM_A300S、A200U

### 模式 B：整数枚举选择器

```c
#define PRINTER_MODEL (31)

#if (PRINTER_MODEL == 31)
    #define VERSION_MAJOR   1
    // ...
#elif (PRINTER_MODEL == 61)
    #define VERSION_MAJOR   2
    // ...
#endif
```

**识别方法**：找到 `#define PRINTER_MODEL` 或类似整数宏；将值映射到对应的 `#if`/`#elif` 分支。

**适用仓库**：TP80X_MCU_EPRT、PM251、tp80x

### 模式 C：构建时注入

```c
#ifdef MODEL_FROM_CMDLINE
// 机型通过 Makefile 的 -D 标志设置
#endif
```

**识别方法**：在 Makefile/SConscript/.bat 中搜索 `-DMODEL=` 或 `project=` 变量。活跃机型来自构建命令行，而非头文件。

**适用仓库**：许多仓库中作为覆盖机制存在

### 模式 D：固件类型枚举（N31）

```c
#define PRT_N31
#if defined(PRT_N31)
    // ...
#endif
```

版本宏可能在独立的 `version.h` 中，而非主 cfg.h。

## 版本宏格式

### 格式 1：四字段数值型（10+ 仓库）

```c
#define VERSION_MAJOR   1
#define VERSION_MINOR   0
#define VERSION_TEST    17
#define VERSION_BETA    2
// 可选的：
#define VERSION_USER    1   // 客户定制变体
```

版本字符串：`"V" MAJOR "." pad2(MINOR) "." pad2(TEST)`  
完整格式：`V1.0.17_Beta2` 或 `V1.0.17.01_Beta2`（含 USER）

### 格式 2：字符串字面量（HM 系列）

```c
// 在 prt_firmware_download_*.h 中：
#define FIRMWARE_VERSION "V1.2.61"
#define FIRMWARE_VERSION_BETA "BETA1"   // 可选
```

**识别方法**：在机型目录中 grep `FIRMWARE_VERSION\s*"`。不在 `*_cfg.h` 中。

### 格式 3：独立版本文件（N31）

```c
// version.h（与 cfg.h 分离）：
#define VERSION_MAJOR 1
#define VERSION_MINOR 0
```

### 始终伴随版本号存在的宏

```
HARDWARE_MAJOR / HARDWARE_MINOR / HARDWARE_TEST
```

## 版本履历位置模式

| 模式 | 路径 |
|------|------|
| project 子目录 | `project/**/<机型>/1_log/<机型>_readme.txt` |
| arch change 目录 | `arch/**/<机型>/change*/<机型>_readme.txt` |
| arch 平级 | `arch/**/<机型>/<机型>_readme.txt` |
| 顶层 readme | `readme/<机型>_readme.txt` |
| 根目录 ReadMe | `ReadMe.txt`、`CHANGELOG.md` |
| 无（仅 git） | 许多仓库不维护 changelog 文件 |

## 未知机型名解析

如果机型名未知：
1. `git branch --show-current` → 可能包含机型后缀
2. `git log --oneline -20 --grep="机型\|model"` → 扫描机型宏名称
3. `grep -rl "VERSION_MAJOR" --include="*_cfg.h"` → 列出配置头文件，从目录名推断
4. `grep -r "PRINTER_NAME\|MACHINE_CODE" --include="*.h"` → 找到机型标识字符串
