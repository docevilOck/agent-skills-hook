---
name: repository-encoding-normalizer
description: 源码仓库编码规范化（UTF-8 统一 + 编译时 GBK 自动转换）。仅当用户明确要求规范化源码仓库文件编码时使用；若用户没有明确要求，禁止使用。
---

# 仓库编码规范化

源码统一为 **UTF-8 with BOM**，中文运行期字面量保留在源码中，编译时由 `gbk_encode.exe` 自动检测含 CJK 字面量的文件并生成 GBK 编码副本供编译器使用。

> `<skill_dir>` = `C:/Users/DELL/.config/opencode/skills/repository-encoding-normalizer`

## 脚本工具

**本 skill 附带的脚本为唯一合法实现，禁止自写替代：** `scan_encoding.py`（编码审计）、`normalize_encoding.py`（批量转换）、`check_mojibake.py`（乱码巡检）、`gbk_encode.exe`（GBK 编译时转换）、`gbk_build.py`（转换源码备查）。仓库改造时将 `gbk_encode.exe` 复制到仓库 `tool/` 目录。

## 首次规范化流程

```bash
# 1. 编码审计（含 Makefile、*.mk、*.bat）
python <skill_dir>/scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json

# 2. 编译器环境检测（确定 armcc / armclang / gcc 及正确编译命令）
#    检查 Makefile 中 ifeq/ifneq ($(armclang),1) 等分支 + 搜索 build*.bat/build*.sh
#    本仓库若 armclang=1 可用则优先；否则用默认 armcc。记录真实 make 命令。

# 3. 批量转换（compiler 参数需与实际编译器匹配）
python <skill_dir>/normalize_encoding.py --root . --compiler armcc --audit-json encoding_audit.json
# ⚠️ 转换后易出两类编译问题：(a) Makefile 若含 BOM → GNU Make exit 2；(b) GBK 注释含中文 → 字节膨胀导致跨行断裂。
# 建议转换后立即用 grep 抽查 `//` 行是否完整，并对 Makefile 强制 strip BOM（PowerShell: Set-Content -Encoding UTF8）

# 4. 复制 gbk_encode 到仓库
copy <skill_dir>/gbk_encode.exe tool/gbk_encode.exe

# 5. 改造 Makefile（见下方模板，替换占位符为仓库实际值）
#    ⚠️ 仅修改与编码/GBK 转换相关的部分：GBK_SRC_DIR、vpath、resolve_gbk、gbk_prepare、
#    编译规则中的 resolve_gbk 注入和 | <OBJDIR> 依赖、clean 中的 GBK_SRC_DIR 清理。
#    禁止改动其他编译逻辑（--feedback、优化选项、条件分支、链接脚本、编译参数等）。
#    注意检查 Makefile 自身编码：若为 UTF-16 LE 等非 UTF-8，先转换为 UTF-8 BOM。

# 6. 确定 gbk_encode 扫描范围
#    从 Makefile 的 SRCS/OBJS/vpath 等变量推导实际参与编译的源文件目录集合，
#    gbk_encode -s 参数必须恰好覆盖这些目录（不多扫也不少漏）。
#    GBK 命中预览：
tool/gbk_encode.exe -s <从Makefile推导的扫描根目录> -o <out_dir> --list

# 7. 乱码巡检（从审计 JSON 自动读取文件列表）
python <skill_dir>/check_mojibake.py --root . --from-json encoding_audit.json

# 8. 编译验证（使用步骤 2 检测到的真实编译命令）
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

**CheckList：** `GBK_SRC_DIR` 指向 `$(OBJDIR)gbk_src/` · `<OBJDIR>:` 目录规则存在 · `gbk_prepare: | <OBJDIR>` · `$(obja) $(objc): | gbk_prepare` · vpath 用 `ifneq` 保护 · exe 用反斜杠 · `.DEFAULT_GOAL := all` · `-x` 排除构建输出 · `rmdir /s /q` 递归 clean · 使用检测到的正确编译命令实际通过

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

## 规则

1. 扫描范围：`*.c`, `*.h`, `*.s`, `*.S`, `*.mk`, `Makefile`, `*.bat`（含无扩展名的 Makefile）
2. 普通文件 → UTF-8 with BOM；`*.s`/`*.S` → UTF-8 无 BOM；`Makefile` → UTF-8 无 BOM（GNU Make 不兼容 BOM）
3. 转换前识别原始编码；不改注释/格式/逻辑/API
4. 不处理二进制、生成物、供应商目录、构建输出
5. Makefile 自身若是 UTF-16 LE 等异常编码，需先转换为 UTF-8 without BOM 后再进行内容编辑（GNU Make 不兼容 BOM）
6. 改造 Makefile 后必须用实际编译器正确命令编译到 0 error，且确认全部 .o 和最终产物（hex/bin/dfu）均已生成
7. 完成后 `check_mojibake.py` 复查

## 安全门槛

编码不确定、无法无损转换、中文处于协议字节/校验数据/固件资源、编译器拒用 BOM、字符串移动影响链接/ABI → 暂停询问用户。

## 交付

变更清单 + 编码审计 + GBK 命中列表 + **编译通过证据**（exit 0 + .o 文件数 + 最终产物 hex/bin/dfu 已生成，注意 exit 0 不代表实际编译了 C 文件）+ 跳过/风险说明。
