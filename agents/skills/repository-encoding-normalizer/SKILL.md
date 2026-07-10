---
name: repository-encoding-normalizer
description: 源码仓库编码规范化（UTF-8 统一 + 编译时 GBK 自动转换）。仅当用户明确要求规范化源码仓库文件编码时使用；若用户没有明确要求，禁止使用。
---

# 仓库编码规范化

源码统一为 **UTF-8**。BOM 策略取决于编译器环境：**ARM/Keil（armcc）→ UTF-8 with BOM**；**ARMCLang / Linux/GCC → UTF-8 without BOM**。中文运行期字面量保留在源码中，编译时由 `gbk_encode.exe`（Windows/ARM/Makefile）或 `gbk_build.py`（Linux/GCC/CMake，Python 源码，跨平台）自动检测含 CJK 字面量的文件并生成 GBK 编码副本供编译器使用。

> `<skill_dir>` = `C:/Users/DELL/.config/opencode/skills/repository-encoding-normalizer`

## 脚本工具

**本 skill 附带的脚本为唯一合法实现，禁止自写替代：** `scan_encoding.py`（编码审计）、`normalize_encoding.py`（批量转换）、`check_mojibake.py`（乱码巡检）、`gbk_encode.exe`（GBK 编译时转换，Windows PE）、`gbk_build.py`（GBK 编译时转换，Python 源码，跨平台）。ARM/Makefile 项目将 `gbk_encode.exe` 复制到仓库 `tool/` 目录；Linux/CMake 项目直接使用 `gbk_build.py`。

## 首次规范化流程

```bash
# 1. 确定扫描范围（--root 指向实际需要规范化的目录，不要全仓扫描）
#    多机型仓库只扫描目标机型子目录（如 tp586w_gen/），不是仓库根

# 2. 编码审计（含 Makefile、*.mk、*.bat、CMakeLists.txt）
python <skill_dir>/scan_encoding.py --root <target_dir> --out encoding_audit.md --json-out encoding_audit.json

# 3. 编译器环境检测（确定 armcc / armclang / gcc 及正确编译命令）
#    检查 Makefile 中 ifeq/ifneq ($(armclang),1) 等分支 + 搜索 build*.bat/build*.sh
#    本仓库若 armclang=1 可用则优先；否则用默认 armcc。记录真实 make 命令。
#    Linux/GCC 项目：检查 CMakeLists.txt 中的 CMAKE_C_COMPILER，确认是否为 GCC。

# 4. 批量转换（compiler 参数需与实际编译器匹配）
#    armcc → --compiler armcc（UTF-8 with BOM）; armclang → --compiler armclang（UTF-8）; GCC → --compiler armclang（UTF-8 without BOM）
python <skill_dir>/normalize_encoding.py --root <target_dir> --compiler armcc --audit-json encoding_audit.json
# ⚠️ 转换后易出两类编译问题：(a) Makefile 若含 BOM → GNU Make exit 2；(b) GBK 注释含中文 → 字节膨胀导致跨行断裂。
# 建议转换后立即用 grep 抽查 `//` 行是否完整，并对 Makefile 强制 strip BOM（PowerShell: Set-Content -Encoding UTF8）
# 若误用 armcc 模式给 GCC 项目的文件加了 BOM：find <dir> '(' -name '*.c' -o -name '*.h' ')' -exec sh -c 'tail -c+4 "$1" > /tmp/stripbom && mv /tmp/stripbom "$1"' _ {} \;

# 5. 复制 GBK 转换工具
#    ARM/Makefile 项目 → copy gbk_encode.exe 到 tool/; Linux/CMake 项目 → 直接用 gbk_build.py（无需复制）

# 6. 改造构建系统（按项目类型选择）
#    Makefile ARM 项目 → 下方「Makefile 集成模板」; CMake 项目 → 下方「CMake 集成」章节
#    ⚠️ 仅修改与编码/GBK 转换相关的部分，禁止改动其他编译逻辑。
#    注意检查 Makefile 自身编码：若为 UTF-16 LE 等非 UTF-8，先转换为 UTF-8 BOM。

# 7. 确定 gbk_encode 扫描范围
#    从 Makefile 的 SRCS/OBJS/vpath 等变量推导实际参与编译的源文件目录集合，
#    gbk_encode -s 参数必须恰好覆盖这些目录（不多扫也不少漏）。
#    GBK 命中预览：
tool/gbk_encode.exe -s <从Makefile推导的扫描根目录> -o <out_dir> --list

# 8. 乱码巡检（从审计 JSON 自动读取文件列表）
python <skill_dir>/check_mojibake.py --root <target_dir> --from-json encoding_audit.json

# 9. 编译验证（使用步骤 3 检测到的真实编译命令）
make clean; if ($?) { make armclang=1 project=<name> -j }
# 验证产物：
#   Get-ChildItem out\<project>\objs\*.o | Measure-Object | Select-Object Count
#   Get-ChildItem out\<project>\*.axf,*.bin,*.hex
```

## gbk_encode.exe 参数

`-s DIR`（源根）/ `-o DIR`（输出目录）/ `-x DIR`（排除目录，至少排除构建输出）/ `--list`（仅列出）/ `--force`（忽略 mtime）/ `-q`（静默）。检测跳过 `#` `//` `/* */` 行，自动清理陈旧副本。

**`-s` 参数必须从 Makefile 中推导**：读取 SRCS/OBJS/vpath 等变量，确定实际参与编译的源文件所在目录集合，`-s` 参数只覆盖这些目录。禁止用 `.` 全仓扫描——会引入不参与编译的文件或遗漏 vpath 引用的源文件。

## 编译器检测

改造 Makefile 前需确认项目实际使用的编译器，避免 `make` 无参数时走错分支：

1. 检查 `Makefile` 中 `ifeq ($(armclang),1)` / `ifeq ($(gcc),1)` 等分支条件
2. 搜索项目中的 `build*.bat` / `build*.sh`，获取实际编译命令（如 `make armclang=1 project=tp80k`）
3. 检查 `CFLAGS` 中的编译选项语法：`-mcpu` → armclang，`--cpu` → armcc
4. 记录正确的 make 命令（含所有必需变量），用于最终编译验证

## Makefile 集成模板

> **占位符模板**：必须替换 `<>` 为仓库实际值后才可使用。

```makefile
.DEFAULT_GOAL := all                    # 1. 顶部（避免默认目标落在首个目标）
GBK_SRC_DIR := <OBJDIR>gbk_src/         # 2. 路径变量

# 3. vpath — ⚠️ ifneq 保护：空 wildcard 会清除所有 .c vpath
ifneq ($(wildcard $(GBK_SRC_DIR)),)
vpath %.c $(wildcard $(GBK_SRC_DIR)*/)
vpath %.c $(GBK_SRC_DIR)
endif

# 4. resolve_gbk（路径剥离按仓库 src_root 调整）
resolve_gbk = $(if $(wildcard $(GBK_SRC_DIR)$(subst <src_root>,,$1)),$(GBK_SRC_DIR)$(subst <src_root>,,$1),$1)

# 5. OBJDIR 有效目标（编译规则 | <OBJDIR> 需要对应的目录创建规则）
<OBJDIR>:
	if not exist "$(<OBJDIR>)" mkdir "$(subst /,\,$(<OBJDIR>))"

# 6. gbk_prepare — cmd.exe 下 exe 用反斜杠！-x 排除构建输出防陈旧副本
#    <scan_root> 必须从 Makefile 的 SRCS/OBJS/vpath 推导（见上方步骤 6），禁止全仓扫描
.PHONY: gbk_prepare
gbk_prepare: | $(OBJDIR)
	.\tool\gbk_encode.exe -s <scan_root> -x <exclude_dir> -o "$(GBK_SRC_DIR)" -q

# 7. 顺序依赖
$(obja) $(objc): | gbk_prepare

# 8. 编译规则：C 注入 resolve_gbk + | <OBJDIR>；ASM 加 | <OBJDIR>
# 9. clean 必须递归删除
clean:
	-if exist $(subst /,\,$(OBJDIR)) rmdir /s /q $(subst /,\,$(OBJDIR))
```

**CheckList：** `GBK_SRC_DIR` 指向 `$(OBJDIR)gbk_src/` · `<OBJDIR>:` 目录规则存在 · `gbk_prepare: | <OBJDIR>` · `$(obja) $(objc): | gbk_prepare` · vpath 用 `ifneq` 保护 · exe 用反斜杠 · `.DEFAULT_GOAL := all` · `-x` 排除构建输出 · `rmdir /s /q` 递归 clean · 使用检测到的正确编译命令实际通过 · 若用 `foreach` + `eval` + `call` 生成单文件规则，recipe 内自动变量需写为 `$$@` / `$$<` / `$$(@D)`（双 `$` 转义，防 `eval` 阶段提前展开）

## CMake 集成

> 适用于 ESP-IDF / CMake 项目的 GBK 编码编译时转换。使用 `gbk_build.py`（Python 源码，无需 Windows PE）。

**顶层 CMakeLists.txt（在 `project()` 之前）：**

```cmake
# GBK 编码副本生成 — 必须在 project() 之前！
# ESP-IDF 的 project() 内部会递归注册组件，此时 GBK 副本必须已就绪
execute_process(
    COMMAND python ${CMAKE_CURRENT_SOURCE_DIR}/tool/gbk_build.py
        -s ${CMAKE_CURRENT_SOURCE_DIR}/<component_dir>
        -o ${CMAKE_CURRENT_BINARY_DIR}/gbk_src
        -x ${CMAKE_CURRENT_BINARY_DIR}
    RESULT_VARIABLE GBK_RESULT
)
if(NOT GBK_RESULT EQUAL 0)
    message(WARNING "gbk_build.py failed, continuing without GBK copies")
endif()
```

**组件 CMakeLists.txt（GBK 副本优先包含）：**

```cmake
# GBK 副本存在时，优先使用 GBK 编码的源文件
set(GBK_SRC_DIR ${CMAKE_CURRENT_BINARY_DIR}/gbk_src)

# 源文件替换：GBK 副本存在则用它，否则用原始 UTF-8 文件
foreach(src ${srcs})
    file(RELATIVE_PATH rel_src ${CMAKE_CURRENT_SOURCE_DIR} ${src})
    if(EXISTS ${GBK_SRC_DIR}/${rel_src})
        list(APPEND gbk_srcs ${GBK_SRC_DIR}/${rel_src})
    else()
        list(APPEND gbk_srcs ${src})
    endif()
endforeach()

# GBK include 目录 — 必须 EXISTS 检查！gbk_build.py 只给含 CJK 字面量的文件创建目录
if(EXISTS ${GBK_SRC_DIR})
    target_include_directories(${COMPONENT_LIB} PRIVATE ${GBK_SRC_DIR})
endif()
```

**trigraph 警告抑制（GCC/ESP-IDF，组件级别）：**

```cmake
# GBK 编码中 ??! 等字节序列匹配 C trigraph 模式（??! → |）
# GCC/ESP-IDF 默认 -Werror=trigraphs 将其当错误，需在组件 target 级别抑制
# 不要用 add_compile_options() — 可能被 ESP-IDF 默认参数覆盖
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-trigraphs)
```

**要点：**
- `execute_process` 放 `project()` **之前**，确保 GBK 副本在组件注册时已存在
- `foreach` 中对每个 include 目录加 `if(EXISTS)` 检查，防止 gbk_build.py 未创建的空目录被加入
- trigraph 抑制必须在组件 `target_compile_options` 级别，不能用全局 `add_compile_options`
- 源文件替换用 `file(RELATIVE_PATH …)` 计算相对路径，匹配 gbk_build.py 的输出结构



## 预置乱码修复

`normalize_encoding.py` 无法修复的预置乱码文件（GBK 字节已腐坏，被工具跳过），需手动修复：

**修复流程（严格遵守，防止二次编码腐坏）：**

1. **git log 找历史版本**：`git log --oneline -- <file>` 列出文件历史
2. **逐个 GBK decode 测试**找到最后干净版本：`git show <commit>:<file> | iconv -f gbk -t utf-8 > /dev/null 2>&1`，退出码 0 表示该版本编码干净
3. **从干净版本提取正确注释**：`git show <clean_commit>:<file>` 导出原始内容
4. **⚠️ 必须先 cp 从原始路径恢复**：不能对已转 UTF-8 的文件做 GBK decode 操作！已转 UTF-8 的文件再用 GBK decode → 二次腐坏（锟斤拷变閿熸枻鎷）。正确做法：
   ```bash
   git show <clean_commit>:<file> > /tmp/original_gbk.c   # 从 git 提取原始 GBK
   python <skill_dir>/normalize_encoding.py --root /tmp --compiler armclang  # 转换原始 GBK
   # 再从转换后的版本提取正确注释
   ```
5. **字符串匹配替换**腐坏注释为正确文本（在当前已转 UTF-8 的目标文件中操作）

**高发陷阱：** 在已转 UTF-8 的文件上做 GBK decode → 字节被误读产生二次腐坏。每次修复前自问：当前文件是原始 GBK 还是已转 UTF-8？只有原始 GBK 才能用 GBK decode。

## 常见故障速查

| 现象 | 根因 | 修复 |
|------|------|------|
| `'tool' is not recognized` | cmd.exe 把 `/` 当开关前缀 | exe 路径用反斜杠 |
| make 只跑第一个目标 | 默认目标是 gbk_prepare | 顶部 `.DEFAULT_GOAL := all` |
| clean build 只编译 asm | 空 wildcard 清空 `.c` vpath | `ifneq` 保护 GBK vpath |
| UTF-8 解码失败 | 扫描到 `out/` 陈旧 GBK 副本 | `-x <build_dir>` 排除 |
| 编译仍用原始 UTF-8 | vpath 仅一级扁平搜索 | `$(wildcard $(GBK_SRC_DIR)*/)` |
| 改中文后未更新 | mtime 缓存/陈旧副本 | `--force` 或递归 clean |
| ASM `.d` 写失败 | OBJDIR 不存在 | gbk_prepare 中 `mkdir` |
| `-j` 并行编译抢先 | 并列前置依赖不保序 | `$(obja) $(objc): \| gbk_prepare` |
| `target 'out/.../objs/' failed to remake` | C/ASM 规则依赖 `\| $(OBJDIR)` 但没有目录创建规则，或规则目标名含尾斜杠与依赖项不匹配 | 添加 `<OBJDIR>:` 无尾斜杠的目录创建目标，recipe 内用 `$@`（非 `$<`）并在 `mkdir` 前 strip 尾斜杠 |
| `C3900U: Unrecognized option` / `A3903U: Cortex-M33 not permitted` | armcc 与 armclang 选项语法不匹配 | 检查 `build*.bat`，用 `make armclang=1` |
| 改造后链接超限 / 编译反馈未触发 | 擅自修改了 Makefile 中的 `--feedback` 等编译反馈条件分支 | 回滚所有非编码/GBK 相关改动，仅保留 GBK_SRC_DIR、vpath、resolve_gbk、gbk_prepare、编译规则注入等编码相关修改 |
| gbk_encode 生成副本缺失或包含无关文件 | `-s` 扫描范围与 Makefile 实际编译范围不一致 | 从 Makefile 的 SRCS/OBJS/vpath 推导实际参与编译的源文件目录集合，重新指定 `-s` |
| Makefile 转 UTF-8 BOM 后 `make` exit 2 | GNU Make 无法解析 BOM 前缀 | 用 PowerShell `Set-Content -Encoding UTF8`（无 BOM）重写 Makefile；`normalize_encoding.py` 对 Makefile 应跳过 BOM 或转换后自动 strip BOM |
| GBK→UTF-8 后 `//` 注释断裂导致语法错误（如 `//#include \"hw_led.h` 与下一行 `led.h\"` 分裂） | GBK 多字节字符（如中文）转 UTF-8 后字节数膨胀，原 `//` 注释行内不再容纳全部内容而跨行 | 手动重排断裂注释：将跨行注释重组为完整行，或改用 `/* */` 块注释；高发文件为 `includes.h` 等集中包含头文件 |
| Makefile 编辑后 `\r\r\n` / 编译语法错乱 | Makefile 自身是 UTF-16 LE 等非 UTF-8，编辑破坏行尾 | 先对 Makefile 做 UTF-16 LE → UTF-8 BOM 转换 |
| Linux/GCC 编译报 `error: trigraph ??` ignored 导致 -Werror 失败 | GBK 编码中 `??!` 等字节序列匹配 C trigraph 模式 | 组件 CMakeLists.txt 中 `target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-trigraphs)`；Makefile 项目在 CFLAGS 中加 `-Wno-trigraphs` |
| CMake configure 报 `Include directory not a directory` | gbk_build.py 只给含 CJK 字面量的文件创建目录，未创建的目录被无条件加入 INCLUDE_DIRS | foreach 遍历 include 目录时加 `if(EXISTS ${dir})` 判断 |
| CMake 构建时找不到 GBK 副本 include 目录 | execute_process 放在了 project() 之后，ESP-IDF project() 内部注册组件时 GBK 副本尚未生成 | execute_process 移到 project() 之前 |
| GCC 环境文件被误加了 BOM | normalize_encoding.py 无 GCC 模式，误用 armcc 加了 BOM | 用 `--compiler armclang` 重新转换；或批量 strip BOM：`find <dir> -name '*.c' -o -name '*.h' | while read f; do tail -c+4 "$f" > /tmp/t && mv /tmp/t "$f"; done` |
| 修复乱码后注释仍腐坏（反复修复不成功） | 在已转 UTF-8 的文件上做 GBK decode 导致二次腐坏 | 从 git 历史提取原始 GBK 版本，在原始版本上修复，再转换到 UTF-8。见「预置乱码修复」章节 |
| `eval` 生成规则中 `$@` / `$(@D)` 展开为空，增量编译 `mkdir` 报路径语法错误 | `foreach` + `eval` + `call` 批量生成单文件 GBK copy 规则时，recipe 内自动变量 `$@`、`$<`、`$(@D)` 在 `eval` 阶段被 Make 提前展开（首次全量编译不触发，仅增量暴露） | recipe 中所有自动变量改为 `$$@` / `$$<` / `$$(@D)`（双美元转义，阻止 `eval` 阶段展开）。同时确保 `mkdir` / `if not exist` 路径参数非空 |

## 规则

1. 扫描范围：`*.c`, `*.h`, `*.s`, `*.S`, `*.mk`, `Makefile`, `*.bat`, `CMakeLists.txt`（含无扩展名的 Makefile）
2. 普通文件 BOM 策略：armcc → UTF-8 with BOM；armclang/GCC → UTF-8 without BOM；`*.s`/`*.S` → UTF-8 无 BOM；`Makefile` → UTF-8 无 BOM（GNU Make 不兼容 BOM）
3. 扫描/转换必须指定 `--root <target_dir>` 而非 `.`，仅处理需要规范化的子目录
4. 转换前识别原始编码；不改注释/格式/逻辑/API
5. 不处理二进制、生成物、供应商目录、构建输出
6. Makefile 自身若是 UTF-16 LE 等异常编码，需先转换为 UTF-8 without BOM 后再进行内容编辑（GNU Make 不兼容 BOM）
7. 改造构建系统后必须用实际编译器正确命令编译到 0 error，且确认全部 .o 和最终产物均已生成
8. 完成后 `check_mojibake.py` 复查

## 安全门槛

编码不确定、无法无损转换、中文处于协议字节/校验数据/固件资源、字符串移动影响链接/ABI → 暂停询问用户。Linux/GCC 环境默认不加 BOM；armcc 环境加 BOM。

## 交付

变更清单 + 编码审计 + GBK 命中列表 + **编译通过证据**（exit 0 + .o 文件数 + 最终产物 hex/bin/dfu 已生成，注意 exit 0 不代表实际编译了 C 文件）+ 跳过/风险说明。
