---
name: repository-encoding-normalizer
description: 源码仓库编码规范化（UTF-8 统一 + 编译时 GBK 自动转换）。仅当用户明确要求规范化源码仓库文件编码时使用；若用户没有明确要求，禁止使用。
---

# 仓库编码规范化

## 核心原则

源码统一为 **UTF-8 with BOM**，中文运行期字面量保留在源码中，编译时由 `gbk_encode.exe` / `gbk_build.py` 自动检测含 CJK 字面量的文件并生成 GBK 编码副本供编译器使用。

> 历史方案：早期曾将中文提取到宏头文件用 `\xB4\xF2...` 字节转义，已废弃。

## 新方案架构

```
源码 (UTF-8 BOM)                      构建输出
──────                                ──────
src/                                   build/objs/
  ├── ui/menu.c ───────────┐            gbk_src/
  ├── core/init.c          │             ├── ui/menu.c          (GBK)
  ├── misc/event.c ───┐    │             ├── misc/event.c       (GBK)
  └── ...              │    │             └── ...
                       │    │
  gbk_encode.exe 扫描 ─┤    │
  (自动检测含中文)    │    │
                       │    │
  Makefile ────────────┤────┘
  (resolve_gbk 路由)   │
                        │
  UTF-8 源文件 ←───────┘ (无中文)
```

## ⛔ 强制脚本使用规则

**本 skill 附带了四个专用脚本，调用本 skill 后必须严格按顺序使用它们，禁止自行编写替代脚本。**

| 违规行为 | 正确做法 |
|---|---|---|
| 自己写编码检测逻辑 | 使用 `scan_encoding.py` |
| 手工逐文件 `iconv` / Python 读写 | 使用 `normalize_encoding.py` |
| 自己写乱码检查逻辑 | 使用 `check_mojibake.py` |
| 自己写 GBK 转换工具 | 使用 `gbk_encode.exe` |
| 在 Makefile 中自己写文件路径判断 | 使用 `resolve_gbk` 模板（见下文） |

**skill 内资源：**

| 资源 | 类型 | 用途 |
|------|------|------|
| `scan_encoding.py` | 脚本 | 编码审计扫描 |
| `normalize_encoding.py` | 脚本 | 批量编码转换（非 UTF-8 → UTF-8 with BOM） |
| `gbk_encode.exe` | 可执行文件 | GBK 编译时转换（独立 exe，无需 Python） |
| `gbk_build.py` | 源码 | GBK 转换源码（备查/修改用） |
| `check_mojibake.py` | 脚本 | 乱码巡检 |

**仓库改造时**，需将 `gbk_encode.exe` 复制到仓库的 `tool/` 目录下。

所有命令从仓库根目录执行，脚本使用绝对路径引用。

## 🚀 推荐流程

### 新仓库首次规范化

```bash
# 第一步：扫描审计
python <skill_dir>/scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json

# 第二步：编码转换（非 UTF-8 → UTF-8 with BOM）
python <skill_dir>/normalize_encoding.py --root . --compiler armcc --audit-json encoding_audit.json

# 第三步：部署 gbk_encode.exe 到仓库
copy <skill_dir>/gbk_encode.exe tool/gbk_encode.exe

# 第四步：改造 Makefile（见 Makefile 集成模板）
#   - 添加 GBK_SRC_DIR、gbk_prepare、vpath、resolve_gbk
#   - 为对象编译建立 gbk_prepare 顺序依赖
#   - 更新 clean 使用 rmdir /s /q

# 第五步：预览 GBK 转换范围
tool/gbk_encode.exe -s <src_dir> -o <out_dir> --list

# 第六步：Dry-run 验证编译路由
make -n 2>&1 | rg "gbk_src"

# 第七步：乱码复查
python <skill_dir>/check_mojibake.py --root . --files "<变更文件列表>"

# 第八步：完整编译验证
make clean && make -j12
```

### 日常开发（已有 UTF-8 源码 + 已配置 Makefile）

```bash
# Makefile 中 gbk_prepare 已挂载到 all 依赖链，每次 make 自动执行
# 无需额外手动步骤
```

> `<skill_dir>` = `C:/Users/DELL/.config/opencode/skills/repository-encoding-normalizer`（Windows）。

## gbk_encode.exe — GBK 编译时转换

### 原理

扫描源码目录下所有 `.c` 和 `.h` 文件，检测双引号字符串字面量内是否含 CJK（中文字符及中文标点），命中则生成 GBK 编码副本供编译器使用。

自动扫描模式下还要清理 **陈旧 GBK 副本**：如果某文件以前命中过中文、现在已不再命中，旧镜像必须删除，否则 `resolve_gbk` 仍可能继续命中旧副本。

**检测跳过以下行**（不会误判注释中的中文）：
- 以 `#` 开头的预处理指令（含 `#define` 宏）
- `//` 注释行
- `/*` / `*` 注释行

> 源文件必须是 UTF-8 编码。非 UTF-8 源文件需先用 `normalize_encoding.py` 转为 UTF-8。

### 独立 exe（推荐，无需 Python 环境）

skill 目录下预置 `gbk_encode.exe`，改造仓库时复制到仓库 `tool/` 目录即可。

```bash
# 仓库改造
copy <skill_dir>/gbk_encode.exe tool/gbk_encode.exe

# 使用
tool/gbk_encode.exe -s <src_root> -o <out_dir> [-q] [--force] [--list]
```

### Python 源码（备查/修改用）

`gbk_build.py` 为 exe 的源码。如需修改逻辑，编辑后必须同时更新 exe：

```bash
# 修改逻辑
python <skill_dir>/gbk_build.py -s <src> -o <out> --list  # 验证改动

# 重新打包
pip install pyinstaller
pyinstaller --onefile --name gbk_encode gbk_build.py

# 更新 skill 内置 exe + 各仓库中的 exe
copy dist/gbk_encode.exe <skill_dir>/gbk_encode.exe
copy dist/gbk_encode.exe <repo>/tool/gbk_encode.exe       # 每个使用了该工具的仓库
```

**注意**：修改源码后不更新 exe，会导致各仓库仍使用旧版本逻辑。源码和 exe 必须保持同步。

**额外注意**：不要只看 `gbk_encode.exe --version`。版本号字符串相同，不代表仓库里正在使用的 exe 已经替换为最新打包产物。若现场仍出现旧行为，必须至少做其中一项：
- 对比 `Get-FileHash <skill_dir>/gbk_encode.exe`、`Get-FileHash dist/gbk_encode.exe`、`Get-FileHash <repo>/tool/gbk_encode.exe`
- 或先把最新打包产物复制为新文件名验证，再原位替换旧 exe

已踩过的真实问题：源码和 `--version` 都显示 `1.1.0`，但仓库 `tool/gbk_encode.exe` 仍是旧哈希文件，最终导致构建继续生成脏 `gbk_src` 副本。

近期已确认需要同步到 exe 的行为包括：
- 自动扫描模式下删除陈旧 `gbk_src` 副本
- `.c/.h` 双扩展名扫描
- 显式 `files...` 模式不做陈旧副本清理

### 命令参数

| 参数 | 说明 |
|------|------|
| `-s DIR` | 源码根目录（必填） |
| `-o DIR` | GBK 副本输出目录（必填） |
| `--list` | 仅列出含中文的文件，不转换 |
| `--force` | 忽略 mtime 检查，强制重新转换 |
| `-q` | 静默模式（make 集成用） |

## Makefile 集成模板

### gbk_prepare 目标

```makefile
GBK_SRC_DIR := $(OBJDIR)gbk_src/

.PHONY: gbk_prepare
gbk_prepare:
	tool/gbk_encode.exe -s "$(PRJDIR)" -o "$(GBK_SRC_DIR)" -q

# 关键：对象编译必须先完成 gbk_prepare
$(objc): | gbk_prepare
```

### resolve_gbk 路由（armcc / armclang 通用）

```makefile
# 注册 GBK 子目录到 vpath（后续构建生效）
vpath %.c $(wildcard $(GBK_SRC_DIR)*/)
vpath %.c $(GBK_SRC_DIR)

# 判断是否有 GBK 副本：有则用 GBK 路径，否则用原始 UTF-8 路径
resolve_gbk = $(if $(wildcard $(GBK_SRC_DIR)$(subst $(PRJDIR),,$1)),$(GBK_SRC_DIR)$(subst $(PRJDIR),,$1),$1)

# armcc 编译配方
%.o: %.c
	$(CC) -c $(call resolve_gbk,$<) $(CFLAGS) -o $(OBJDIR)$(notdir $@)
```

### 全套 CheckList

### clean / distclean

```makefile
ifeq ($(SHELL), cmd.exe)
RMDIR := rmdir /s /q
else
RMDIR := rm -rf
endif

clean:
	-if exist $(subst /,\,$(OBJDIR)) $(RMDIR) $(subst /,\,$(OBJDIR))
	-$(RM) $(subst /,\,$(OUTDIR)*.*)
```

不要只删 `$(OBJDIR)*.*`。那样会漏掉 `$(OBJDIR)gbk_src/...` 子目录。

将以下内容加入到仓库 Makefile：

| 项目 | 说明 |
|------|------|
| `GBK_SRC_DIR` 变量 | 指向构建目录下的 gbk_src 子目录 |
| `gbk_prepare` 目标 | 定义目标本身，并通过 `$(objc): | gbk_prepare` 建立顺序依赖 |
| `vpath` 子目录注册 | `$(wildcard $(GBK_SRC_DIR)*/)` 递归覆盖 |
| `resolve_gbk` 函数 | 编译配方中 `$<` → `$(call resolve_gbk,$<)` |
| `clean` 递归删除 | `rmdir /s /q $(OBJDIR)` 确保清理 gbk_src |
| 陈旧副本清理 | 自动扫描模式下删除不再命中的 `gbk_src` 镜像 |

## 进阶 Makefile 集成

### GBK 路由收窄

- 用 `gbk_src_file` 目标变量绑定每个对象到其 GBK 副本路径，避免 `$<` 裸名导致 `resolve_gbk` 失效；编译命令中 `$(if $(wildcard $(gbk_src_file)),$(gbk_src_file),$(call resolve_gbk,$<))` 优先取绑定路径。
- `gbk_prepare` 只做扫描转换，不要在当中用 `xcopy` 整树复制源目录——那会让不需要 GBK 的文件也被 `wildcard` 命中，误走 `gbk_src` 路径。确需普通副本时在模式规则里 `@if not exist` 按需补。
- `$(GBK_SRC_DIR)%.c` 规则加 `| gbk_prepare` 保证整目录扫描先于单文件副本生成。

### 通用 Makefile 要点

- Makefile 顶部加 `.DEFAULT_GOAL := all`，避免默认目标落在首个对象文件。
- 型号可能自定义的关键路径变量（如 `SCATTER`）用 `?=` 而非 `:=`，仅提供默认值。

### 文本内联脚本

用 Python 做宏→字符串内联时，`re.sub` 的替换字符串会重新解析转义，需用 lambda 传递替换值：

```python
result = re.sub(pattern, lambda m, v=val: '"' + v + '"', result)
```

## 验证

```bash
# 验证 GBK 文件编码（确认生成了有效的 GBK 文件）
python -c "
data = open('<out_dir>/dev_ui/prt_menu_table.c','rb').read()
try: data.decode('utf-8')
except: print('NOT UTF-8 (likely GBK) - OK')
"

# Dry-run 验证编译路由（确认 gbk_src 出现在含中文文件的编译命令中）
make -n 2>&1 | rg "gbk_src"

# 验证 .d 依赖文件指向正确路径
Get-Content "out/hma300s/objs/prt_menu_table.d"
# 应指向 gbk_src/dev_ui/prt_menu_table.c（而非原始 UTF-8 路径）

# 手动执行 GBK 转换（dry-run）
tool/gbk_encode.exe -s arch/lpc546/hma300s -o out/hma300s/objs/gbk_src --list

# 乱码复查
python <skill_dir>/check_mojibake.py --root . --files "<变更文件列表>"
```

## 常见故障

### vpath 扁平搜索失效

**现象**：GBK 文件正确生成，但编译器始终使用 UTF-8 原始文件。

**根因**：`vpath %.c $(GBK_SRC_DIR)` 只扁平搜索一级目录，GBK 文件在子目录中（如 `gbk_src/dev_ui/menu.c`）无法匹配。

**修复**：添加 `vpath %.c $(wildcard $(GBK_SRC_DIR)*/)` 覆盖子目录。

### mtime 缓存导致未重新转换

**现象**：修改了源码中的中文字符串，但编译结果未更新。

**根因**：`gbk_build.py` 默认比较 mtime 跳过未变文件。但如果 clean 不彻底（旧 GBK 文件残留），或文件已不再包含中文而陈旧副本未删除，`resolve_gbk` 仍可能继续命中旧镜像。

**修复**：
- `clean` 用 `rmdir /s /q` 递归删除整个 `objs` 目录
- 自动扫描模式下清理陈旧 `gbk_src` 副本
- 必要时使用 `--force` 参数强制重转

### `all: gbk_prepare $(objc)...` 在并行构建下失效

**现象**：`make -j8` 时偶发编译命中旧 `gbk_src`，或者对象编译在 `gbk_prepare` 完成前就启动。

**根因**：GNU make 并列前置依赖不保证执行顺序，`gbk_prepare` 不能只挂在 `all` 上。

**修复**：

```makefile
$(objc): | gbk_prepare
```

### `.h` 头文件中的中文字符串

**现象**：`.h` 头文件中含中文运行期字面量，编译后仍是 UTF-8。

**说明**：`gbk_encode.exe` 已支持扫描 `.c` 和 `.h` 文件，但 Makefile 的 vpath 路由机制仅作用于编译目标的 `.c` 文件。通过 `#include` 引用的 `.h` 文件不会走 vpath。

**建议**：将运行期中文字符串放在 `.c` 文件中，`.h` 仅保留声明和注释。

## 适用范围

用于含混合编码的 C/C++ 嵌入式源码仓库。常见目标包括 `.c/.h/.s/.S/.mk/.bat/.cmd`。

仅在用户明确要求执行编码规范化时使用。

## 必须遵守的规则

1. 普通目标文本文件统一转换为 **UTF-8 with BOM**
2. 启动和汇编相关文件（`*.s`、`*.S`）必须转换为 **UTF-8 无 BOM**
3. 转换前必须识别每个文件的原始编码，并保留审计清单
4. 不修改注释、格式、逻辑、API 或行为
5. 不处理二进制、生成物、供应商目录、构建输出目录
6. 每次完成编码统一后，必须用 `check_mojibake.py` 复查

## 安全门槛

遇到以下情况必须暂停并询问用户：
- 编码识别不确定
- 文件无法无损解码/重新编码
- 中文文本处于协议字节、校验敏感数据、固件资源中
- 编译器/工具链拒绝某类文件使用 BOM
- 移动字符串可能改变内存段、链接属性或 ABI

## 常见错误

| 错误 | 正确做法 |
|---|---|---|
| 自己写编码检测/转换脚本 | **必须使用** skill 自带脚本 |
| 在 armcc/armclang 项目中不区分工具链 | 先确认编译器类型，armcc 用 BOM |
| 修改生成物/供应商/构建输出 | 默认排除 |
| `vpath` 只指定一级目录 | 添加 `$(wildcard $(GBK_SRC_DIR)*/)` |
| clean 用 `del` 不递归 | 用 `rmdir /s /q` 确保删除 gbk_src 子目录 |

## 交付标准

完成一次编码规范化时，必须提供：
- 仓库相对路径的变更文件清单
- 原始编码审计证据
- GBK 文件生成证据（`--list` 输出）
- Makefile 集成检查清单
- 构建/编译验证证据
- 跳过文件和风险项说明
