---
name: repository-encoding-normalizer
description: 仅当用户明确要求规范化源码仓库文件编码、保留历史非 UTF-8 运行期文本的原始字节语义、处理 armcc/armclang 嵌入式 C/C++ 项目中 UTF-8 与历史本地编码混合源码时使用；若用户没有明确要求，禁止使用。
---

# 仓库编码规范化

## 核心原则

先记录原始编码，再做转换；先确认运行期字节语义，再改源码文本形态。不要根据“转换后的编码”判断中文能否原地保留，必须根据文件**转换前的原始编码**判断。

对于原本不是 UTF-8 的源码，关键语义通常是 **原始编码下的运行期文本字节**，不是 Unicode 文本。迁移时不能把这类运行期字符串误变成 UTF-8 运行期字符串。

## 适用范围

用于含混合编码的源码仓库。常见目标包括 C/C++/H/ASM/Make/SCons/CMake/脚本/配置/文本资源，但必须按具体仓库确认文件类型。

不要写死设备、板卡、芯片、产品或绝对路径。用户给出的路径示例默认只表示“形态参考”，除非用户明确指定它就是目标路径。
仅在用户明确要求执行编码规范化时使用；如果用户没有明确要求，禁止调用本 skill。

## 必须遵守的规则

1. 普通目标文本文件统一转换为 **UTF-8 with BOM**；除非明确选择并验证了某个文本宏头文件必须保留原始本地编码。
2. 转换前必须识别每个文件的原始编码，并保留审计清单。
3. 原始编码已经是 UTF-8 的文件，其中中文可以原地保留。
4. 原始编码不是 UTF-8 的文件，其中被代码运行期使用的中文文本必须迁移到对应模块的宏定义头文件。
5. 宏值必须保持原始编码下的运行期字节序列。
6. 生成的宏定义头文件必须按模块/功能清晰分区，并带中文注释。
7. 除替换中文运行期字面量为宏以外，不改注释、格式、逻辑、API 或行为。
8. 不处理二进制、生成物、供应商目录、构建输出目录，除非用户明确要求。
9. 启动和汇编相关文件必须转换为 **UTF-8 无 BOM**，包括 `*.s`、`*.S`、启动汇编、链接/启动入口依赖的汇编 include；不要保存为 UTF-8 with BOM。
10. 每次完成一轮编码统一后，必须复查本次变更文件，确认没有因为本次编码转换引入新的乱码文件或乱码文本。

## 编译器策略

先根据工具链选择转换格式，再用最小构建验证。

| 工具链/场景 | 推荐宏头文件存储方式 | 原因 |
|---|---|---|
| `armcc` / ARM Compiler 5 | 转换为 UTF-8 with BOM | 保持 BOM 以适配旧工具链对文本头文件的稳定读取。 |
| `armclang` / ARM Compiler 6 | 转换为 UTF-8 | 避免不必要的 BOM 影响，按 UTF-8 统一保存。 |
| 非 ARM 或未知编译器 | 默认 UTF-8 with BOM | 跨文件编码最稳妥。 |

默认先识别工具链，再决定目标编码：`armclang` 输出 UTF-8，`armcc` 输出 UTF-8 with BOM，其他场景默认 UTF-8 with BOM。启动和汇编相关文件的无 BOM 要求优先于此默认策略。

## 工作流程

### 1. 建立仓库级策略

确认：

- 仓库根目录；
- 需要处理的文件扩展名和排除目录；
- 编译器/工具链对 BOM 与混合编码 include 的要求；
- 模块级文本宏头文件应放在哪里。

优先遵循仓库既有约定。没有约定时，把宏头文件放在拥有这些字符串的模块附近，例如：

```text
<module>/misc/<module>_text.h
<module>/inc/<module>_text.h
<module>/<feature>_text.h
```

用户示例 `.../misc/prt_gbk_text.h` 只表示“模块内集中维护历史本地编码运行期文本”的一种形态，不代表固定绝对路径。

### 2. 盘点原始编码

对每个目标文本文件记录：

- 路径；
- 检测到的原始编码；
- 是否已有 BOM；
- 是否包含中文字符；
- 中文出现在注释中，还是出现在可执行/运行期字符串数据中。

优先使用确定性工具。对 GBK/GB2312/Big5/Shift-JIS 等历史编码要使用多种信号交叉确认。编码识别不确定时，停止并询问用户，不要猜测转换。

**工具脚本：** 本 skill 附带 `scan_encoding.py`，可自动扫描仓库并生成编码审计报告：

```bash
python scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json
```

该脚本会输出每个含中文文件的路径、原始编码、中文出现在注释/字符串/代码区的统计、文件级分类，以及详细行级清单。将审计报告作为后续决策依据。

### 3. 区分中文注释和中文运行期文本

只迁移代码会使用的中文，例如：

- C/C++ 字符串字面量；
- 宏字符串值；
- 协议/UI/状态文本数组；
- 运行期会读取的命令表、菜单表、提示文本。

以下纯文本文档/配置文件通常可直接做编码转换，不必按“运行期字符串迁移”处理：

- `*.txt`
- `*.md`
- `*.rst`
- `*.csv`
- `*.json`
- `*.yaml`
- `*.yml`
- `*.ini`
- `*.cfg`

前提是这些文件确实只是文档、说明、静态配置或数据交换文本，而不是会被目标固件按特定历史编码逐字节消费的协议资源。

不要因为文件原始编码不是 UTF-8 就迁移中文注释。中文注释可以随文件一起转换为 UTF-8 with BOM 后原地保留，除非仓库策略另有要求。

### 4. 按模块创建宏定义头文件

根据字符串归属创建一个或多个头文件。除非仓库已有统一大文本表风格，否则不要创建全仓库级“垃圾桶”式头文件。

最大兼容方案：宏头文件使用 UTF-8 with BOM 保存，迁移出来的原始非 UTF-8 运行期字符串用原始编码字节转义表达，并在宏后保留中文注释方便维护。

头文件模板：

```c
#ifndef MODULE_TEXT_H
#define MODULE_TEXT_H

/*
 * 中文文本集中定义
 * 来源：由历史非 UTF-8 编码源码中的运行期文本迁移而来。
 * 说明：本文件使用 UTF-8 with BOM 保存；宏值使用原始编码字节转义，保持运行期字节不变。
 */

/* ===== 打印状态文本 ===== */
#define MODULE_TEXT_PRINT_READY      "\xB4\xF2\xD3\xA1\xBB\xFA\xBE\xCD\xD0\xF7"  /* 打印机就绪 */
#define MODULE_TEXT_PRINT_ERROR      "\xB4\xF2\xD3\xA1\xBB\xFA\xB4\xED\xCE\xF3"      /* 打印机错误 */

/* ===== 菜单显示文本 ===== */
#define MODULE_TEXT_MENU_SETTING     "\xC9\xE8\xD6\xC3"                          /* 设置 */

#endif /* MODULE_TEXT_H */
```

默认不要使用原始本地编码、明文非 ASCII 宏值的头文件。只有在仓库明确要求，并且编译器专项验证能证明无 warning/error 时，才允许这种例外。

命名规则：

- 使用大写模块前缀；
- 按功能/模块分组，并使用中文分区注释；
- 宏名要表达语义，不要随意编号；只有无法判断语义时才使用编号；
- 文本相同但运行期语义不同的字符串不要强行合并；
- 使用字节转义宏时，宏后必须保留中文注释方便维护。

### 5. 外科式替换字面量

对每个被迁移的中文运行期文本：

- 在原源码文件中 include 对应模块文本头文件；
- 只替换字符串字面量本身；
- 保留原有字符串拼接、格式化占位符、转义序列和数组布局；
- 确认格式字符串与参数仍匹配。

示例：

```c
/* before：原始文件不是 UTF-8，运行期需要原始编码字节 */
show_msg("打印机错误");

/* after */
#include "module_text.h"
show_msg(MODULE_TEXT_PRINT_ERROR);
```

### 6. 转换文件编码

完成字面量迁移决策后：

- 先识别编译器类型，再决定编码格式：`armclang` 转换为 UTF-8，`armcc` 转换为 UTF-8 with BOM；
- 启动和汇编相关文件（如 `*.s`、`*.S`、startup 汇编文件、汇编 include）必须转换为 UTF-8 无 BOM，并加入 `--no-bom-files`；
- 新建或修改的宏头文件按选定编译器策略保存；
- 行尾保持原样，除非仓库已有明确行尾规则。

**工具脚本：** 本 skill 附带 `normalize_encoding.py`，可根据审计结果批量执行编码转换和宏迁移：

```bash
# 示例：armcc 项目，转换指定文件为 UTF-8 with BOM，同时创建宏头文件并替换字面量
python normalize_encoding.py \
    --root . \
    --compiler armcc \
    --files "src/tp.c,src/esc_p.c,src/includes.h" \
    --no-bom-files "src/inc_config.mk" \
    --macro-header "src/tp_text.h" \
    --macro-name "TP_TEXT_TEST_SAMPLE" \
    --macro-value "PT562\\xB2\\xE2\\xCA\\xD4\\xD1\\xF9\\xD5\\xC5\\n" \
    --macro-comment "PT562测试样张" \
    --source-file "src/tp.c" \
    --old-string '"PT562测试样张\\n"' \
    --include-marker '#include "includes.h"'
```

**注意：** `normalize_encoding.py` 为模板脚本，执行前必须根据 `scan_encoding.py` 的审计结果调整 `--files`、`--macro-*` 和 `--source-file` 参数。Makefile 类文件、启动汇编和 `*.s`/`*.S` 等汇编文件务必放入 `--no-bom-files`，避免 Make 或汇编工具解析失败。

### 7. 验证

必须验证：

- 转换前/转换后的文件编码审计；
- 搜索确认：原始非 UTF-8 文件中的运行期非英文/非 ASCII 字面量已迁移；允许中文注释按策略保留；
- 检查本次编码转换涉及的文件，确认没有新增乱码、问号替代、异常替换字符或明显错误解码片段；
- 通过字节对比或确定性转换证明：迁移后的宏值保持原始编码运行期字节；
- 宏头文件 include 路径可解析；
- 项目构建或最接近的编译检查通过；
- 变更文件中没有误改二进制、生成物或供应商文件。

建议按下面步骤执行乱码复查：

1. 先整理本次编码转换实际修改的文件列表，不要扫描整个仓库替代本次变更复查。
2. 对每个变更文件优先检查是否出现 `�`、连续 `?`、`??`、`???`、`锟斤拷`、`烫烫烫`、`屯屯屯` 等典型乱码片段。
3. 对原本应保留中文注释或中文文档的文件，抽样打开关键行，确认中文语义仍可读，不是“能解码但内容已错”。
4. 对迁移过运行期字符串的源码和宏头文件，同时检查替换前后的显示文本与字节转义注释，确认没有把原始本地编码语义误转成 UTF-8 运行期文本。
5. 对 `*.s`、`*.S`、startup 汇编、Makefile 类文件，额外确认输出编码是 `UTF-8 无 BOM`，且文件头没有被插入 BOM。
6. 若本次改动文件较多，先运行 `check_mojibake.py` 做批量巡检，再对命中的文件人工复核；脚本未命中不等于可跳过人工抽查。

可直接使用：

```bash
python check_mojibake.py --root . --files "src/a.c,src/b.h,docs/readme.md"
```

建议报告格式：

```text
编码规范化报告
- 处理范围：
- 转换为 UTF-8 with BOM 的文件：
- 原始 UTF-8 且保留原地中文的文件：
- 已迁移原始编码运行期文本的原始非 UTF-8 文件：
- 新建/更新的宏头文件：
- 宏头文件存储策略：UTF-8 with BOM + 原始编码字节转义 / 已验证的原始本地编码明文头文件例外
- 跳过文件与原因：
- 验证命令与结果：
- 风险/未覆盖项：
```

## 安全门槛

遇到以下情况必须暂停并询问用户：

- 编码识别不确定；
- 文件无法无损解码/重新编码；
- 中文文本处于协议字节、校验敏感数据、固件资源或外部指定二进制格式中；
- 编译器/工具链拒绝某类文件使用 BOM；
- 仓库想使用原始本地编码明文头文件，但尚无该编译器行为的验证证据；
- 移动字符串可能改变内存段、链接属性、constness 或 ABI 可见数据布局。

## 常见错误

| 错误 | 正确做法 |
|---|---|
| 根据转换后的编码判断中文能否保留 | 根据原始编码审计判断 |
| 迁移所有中文 | 只迁移原始非 UTF-8 文件中的运行期中文文本；注释可保留 |
| 创建全仓库一个巨大文本头文件 | 优先创建模块归属明确的头文件 |
| 在 armcc/armclang 项目中不区分工具链就统一套用同一种输出编码 | 先判断工具链，armclang 输出 UTF-8，armcc 输出 UTF-8 with BOM |
| 把原始本地编码运行期字符串转成 UTF-8 运行期字符串 | 宏值必须保持原始编码字节 |
| 不先识别编译器就开始转换 | 先确认编译器类型，再选择对应编码格式 |
| 修改生成物/供应商/构建输出 | 默认排除，除非用户明确要求 |
| 使用 Windows 绝对路径写死规则 | 文档和配置使用仓库相对路径与 `/` 分隔符 |

## 交付标准

完成一次编码规范化时，必须提供：

- 仓库相对路径的变更文件清单；
- 宏头文件路径和模块归属理由；
- 选定的宏头文件存储策略与编译器验证证据；
- 原始编码审计证据；
- 原始编码运行期字节保持证据；
- 本次编码转换后乱码检查证据；
- 构建/编译验证证据；
- 跳过文件和风险项说明。

---

## 工具脚本

本 skill 目录下附带两个 Python 辅助脚本，用于自动化扫描和执行编码规范化。

### scan_encoding.py

**作用：** 扫描仓库所有目标文本文件，检测原始编码，识别中文字符位置（注释 vs 字符串字面量 vs 代码区），生成 `encoding_audit.md` 审计报告。

**位置：** `agents/skills/repository-encoding-normalizer/scan_encoding.py`

**参数：**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--root` | `.` | 仓库根目录 |
| `--out` | `encoding_audit.md` | 审计报告输出路径 |
| `--json-out` | `""` | 机器可读 JSON 审计输出路径，供 `normalize_encoding.py` 直接消费 |
| `--exts` | `.c,.h,.s,.S,.mk,.txt,.bat,.cmd` | 扫描的文件扩展名（逗号分隔） |
| `--exclude` | `stm32lib,stm32usb,ucos2,Libraries,...` | 排除的目录名（逗号分隔） |

**用法示例：**

```bash
python scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json
```

**输出示例：**

审计报告包含三部分：
1. **汇总表**：文件路径、原始编码、文件分类、含中文行数、字符串字面量/注释/代码区的中文字符数
2. **文件分类说明**：区分 `comment_only`、`string_or_runtime`、`mixed_comment_and_runtime`、`mixed_comment_and_code`、`code_only_needs_review`
3. **详细清单**：每个含中文文件的逐行分析，标注中文字符所在位置类型

### normalize_encoding.py

**作用：** 根据审计结果批量执行编码转换（原始非 UTF-8 -> UTF-8 with/without BOM），创建宏定义头文件，并替换源文件中的运行期字符串字面量为宏。

**位置：** `agents/skills/repository-encoding-normalizer/normalize_encoding.py`

**参数：**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--root` | `.` | 仓库根目录 |
| `--compiler` | `armcc` | 编译器类型（`armcc` 或 `armclang`），决定目标编码是否带 BOM |
| `--files` | `""` | 需要转换的文件列表（逗号分隔，相对 root） |
| `--no-bom-files` | `""` | 转为 UTF-8 **无 BOM** 的文件列表（如 Makefile） |
| `--macro-header` | `""` | 新建的宏头文件路径（相对 root） |
| `--macro-name` | `""` | 宏名称 |
| `--macro-value` | `""` | 宏值（原始编码字节转义，如 `PT562\xB2\xE2...`） |
| `--macro-comment` | `""` | 宏后中文注释 |
| `--source-file` | `""` | 包含旧字符串的源文件路径（相对 root） |
| `--old-string` | `""` | 需要替换的旧字符串字面量 |
| `--include-marker` | `#include "includes.h"` | 插入 include 的标记行 |
| `--audit-json` | `""` | `scan_encoding.py` 生成的 JSON 审计文件 |
| `--plan-out` | `""` | 输出 dry-run 或执行计划的 JSON 文件 |
| `--dry-run` | `false` | 只生成计划，不改文件 |

**用法示例：**

```bash
# 1. 仅批量转换文件编码
python normalize_encoding.py \
    --root . \
    --compiler armcc \
    --files "src/tp.c,src/esc_p.c,src/includes.h" \
    --no-bom-files "src/inc_config.mk"

# 2. 先基于扫描结果生成自动计划，不落盘改动
python scan_encoding.py \
    --root . \
    --out encoding_audit.md \
    --json-out encoding_audit.json

python normalize_encoding.py \
    --root . \
    --compiler armcc \
    --audit-json encoding_audit.json \
    --dry-run \
    --plan-out normalize_plan.json

# 3. 同时创建宏头文件并替换字面量
python normalize_encoding.py \
    --root . \
    --compiler armcc \
    --files "src/tp.c,src/esc_p.c" \
    --no-bom-files "src/inc_config.mk" \
    --macro-header "src/tp_text.h" \
    --macro-name "TP_TEXT_TEST_SAMPLE" \
    --macro-value "PT562\\xB2\\xE2\\xCA\\xD4\\xD1\\xF9\\xD5\\xC5\\n" \
    --macro-comment "PT562测试样张" \
    --source-file "src/tp.c" \
    --old-string '"PT562测试样张\\n"' \
    --include-marker '#include "includes.h"'
```

**注意事项：**

1. **Makefile 类文件、启动汇编和 `*.s`/`*.S` 等汇编文件**必须放入 `--no-bom-files`，否则 Make 或汇编工具可能因 BOM 解析失败。
2. `--macro-value` 中的字节必须按原始文件编码确认，而不是默认按 GBK 假设。
3. `--old-string` 必须与实际源码中的字符串字面量完全匹配（包括引号和转义）。
4. `--audit-json + --dry-run` 适合先自动区分“只转编码”和“需要迁移运行期中文”的文件，再人工确认。
5. `txt/md/rst/csv/json/yaml/yml/ini/cfg` 这类纯文本文件默认直接进入编码转换计划，不进入运行期迁移候选。
6. 对源码类 `string_or_runtime` / `mixed_comment_and_runtime` 文件，脚本当前只会列为迁移候选，不会擅自生成宏替换方案。
7. 当前自动替换器支持显式传入源文件原始编码；若源文件是其他历史编码，仍建议先用 dry-run 计划，再按原始编码人工确认迁移参数。
8. 仍建议先处理少量文件并编译验证，再扩大范围。

### check_mojibake.py

**作用：** 对本次编码转换涉及的文件做批量乱码巡检，快速发现替换字符、连续问号、典型乱码词和 UTF-8 BOM 误写入到无 BOM 文件等问题。

**位置：** `agents/skills/repository-encoding-normalizer/check_mojibake.py`

**参数：**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--root` | `.` | 仓库根目录 |
| `--files` | `""` | 需要巡检的文件列表，逗号分隔，相对 `root` |
| `--allow-question-files` | `""` | 允许出现连续问号的文件列表，逗号分隔，相对 `root` |

**用法示例：**

```bash
python check_mojibake.py --root . --files "src/tp.c,src/tp_text.h,docs/readme.md"
```

**输出说明：**

- 无命中时输出 `No suspicious mojibake patterns found.`
- 命中时按文件列出问题类型、行号和片段，并以非零状态码退出，方便作为人工复查前的快速筛查。
