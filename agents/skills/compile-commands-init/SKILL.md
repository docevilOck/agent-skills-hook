---
name: compile-commands-init
description: 为 C/C++ 项目初始化 compile_commands.json 和 .clangd 配置文件，使 clangd LSP 能正确进行代码补全、跳转和诊断。Linux 下使用 bear 拦截构建命令生成，Windows 下使用构建日志配合 CompilerGen.py 生成，并在生成后自动清理脚本临时产物。触发词：compile_commands.json、clangd、编译数据库、代码跳转、LSP 配置、生成 compile_commands。
---

# Compile Commands 初始化

## 概述

为 C/C++ 项目生成 `compile_commands.json`（clangd 编译数据库）和 `.clangd` 配置文件，
使 clangd 能正确解析项目头文件路径、宏定义和编译选项。

## 核心流程

1. 检测运行平台（Linux / Windows）
2. 编译或抓取日志之前先执行一次 clean，避免旧产物和过期命令污染结果
3. 按平台选择生成策略，生成 `compile_commands.json`
4. 为源码直接包含的本地头文件补充显式编译数据库条目
5. 生成 `.clangd` 配置文件
6. 验证生成结果

---

## 步骤 1：平台检测

```bash
uname -s  # Linux 或 MINGW*/MSYS*/CYGWIN*
```

- `Linux` → 使用 bear
- `MINGW*` / `MSYS*` / `CYGWIN*`（Windows）→ 使用 CompilerGen.py

---

## 步骤 2：生成 compile_commands.json

### 统一前置：先 clean

无论 Linux 还是 Windows，只要准备重新构建或重新抓构建日志，都先执行 clean。

目的：

- 避免旧 `.o`、旧中间目录、旧增量日志干扰本次编译数据库
- 避免只编译少量文件，导致 `compile_commands.json` 不完整
- 避免沿用过时的 include 路径、宏定义或条件编译开关

执行要求：

- 优先使用仓库已有 clean 命令
- 没有标准 clean 目标时，先找项目文档、构建脚本或 IDE 工程里的清理入口
- 不要手工大面积删除不确定目录；只清理构建系统本来就会清理的产物

常见命令示例：

```bash
make clean
cmake --build build --target clean
```

### Linux — bear

```bash
# 安装（如未安装）
sudo apt install bear -y 2>/dev/null || sudo dnf install bear -y 2>/dev/null

# 先 clean，再完整构建并拦截（根据实际构建命令调整）
make clean 2>/dev/null || true
bear -- make -j$(nproc)
```

如果项目使用 CMake：
```bash
cmake --build build --target clean
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cp build/compile_commands.json .
```

### Windows — 构建日志 + CompilerGen.py

**第一步：获取构建日志**

将完整编译输出保存为 `build_log.txt`。方式取决于构建系统：

- **Makefile**（Git Bash/MSYS2）：
  ```bash
  # 先 clean，再抓完整日志
  make clean 2>/dev/null || true
  make -j 2>&1 | tee build_log.txt
  ```
- **Keil MDK / IAR**：从 IDE 构建输出窗口复制完整编译日志，保存为 `build_log.txt`
- **已有日志文件**：直接使用现有的构建日志

要求：

- 不要直接复用明显过期的 `build_log.txt`
- 如果日志来自 IDE，尽量先执行 IDE 自带 Rebuild/Clean，再复制完整输出
- 如果项目包含多个 target，优先抓当前目标的一次完整重建日志

**诊断：build_log.txt 异常短小**

如果 `make clean && make` 后 `build_log.txt` 仅包含少量行（例如仅 1-2 行
"nothing to be done" 或行数远少于项目源文件数），说明 clean 不彻底或未生效
——所有目标仍是 up-to-date 状态，实际未重新编译任何文件。

此时**不要**更换 shell 重定向或捕获方式反复抓取——根因是增量构建，不是
日志捕获失败。立即执行：

1. 检查构建产物目录（如 `out/`、`build/`）是否确实为空；若有残留 `.o`，
   手动删除或排查 clean 目标为何未覆盖
2. 确认 clean 已生效后再次 `make -j 2>&1 | tee build_log.txt`
3. 检查 `build_log.txt` 是否包含实际编译命令行（带有 `-c`、`-o` 等编译参数）；
   若仍为空或极短，重复第 1 步

**第二步：用 CompilerGen.py 生成**

```bash
python <skill-dir>/scripts/CompilerGen.py <compiler>
```

脚本支持的编译器名：
| 名称 | 匹配的编译器 |
|------|-------------|
| `armcc` | armcc / armcc.exe |
| `armclang` | armclang / armclang.exe |
| `gcc` | gcc / arm-none-eabi-gcc |

注意：传给 `CompilerGen.py` 的编译器名必须和 `build_log.txt` 里的真实编译器一致。
如果日志里是 `armcc.exe -c ...`，就传 `armcc`；不要误传 `armclang`。

脚本自动生成 `compile_commands.json` 和 `.clangd`，并在成功后默认清理 `build_log.txt` 这类脚本临时产物。
生成 `compile_commands.json` 时，脚本会自动补充两类头文件编译条目：

1. **直接 `#include "..."` 头文件**：扫描每个源码文件的 `#include "..."` 指令，
   为可解析到的 `.h/.hpp/.hh/.hxx` 头文件补充 `-x c-header` 或 `-x c++-header` 显式条目
2. **`-D` 宏配置头文件**：扫描编译参数中的 `-DCONFIG_FILE="xxx.h"` 模式
   （如 mbedTLS 的 `-DMBEDTLS_CONFIG_FILE="tp807_tls13_config.h"`），
   为这些由宏间接指定的配置头文件也自动生成编译条目

两类补充均避免 clangd 只能用错误或残缺的推断上下文解析头文件。

对于 ARMCC / ARMCLANG 日志，脚本会尽量保留真实预包含语义，把 `--preinclude` / `-include`
转换成 clangd 可识别的 `-include <header>`。

如果项目使用了 `repository-encoding-normalizer`（gbk_encode 在 `out/.../gbk_src/` 下生成 GBK 编码副本），
构建日志中的编译命令会指向副本路径而非原始源码。生成 `compile_commands.json` 后，必须将所有
`file` 字段从副本路径回写到原始源码路径：副本路径中去除 `gbk_src/` 子目录前缀即为原始路径
（例如 `out/tp80k/gbk_src/app/main.c` → `app/main.c`）。回写规则：将 file 中 `gbk_src/` 及之前
的目录部分替换为项目根目录中对应的原始源路径。必须确保最终交付的数据库中没有任何 `gbk_src` 条目残留。

如需保留 `build_log.txt`：

```bash
python <skill-dir>/scripts/CompilerGen.py <compiler> --keep-build-log
```

**超时风险**：大型项目（数百以上源文件）的 `build_log.txt` 可能达到数 MB，
CompilerGen.py 解析全部编译命令并扫描头文件依赖耗时可能超过 60 秒。
如果使用 `timeout` 或限制了执行时间的 shell 环境，请确保超时值足够大
（建议 300 秒以上），避免脚本被中途截断。脚本使用原子写入（先写 `.tmp`
再 `os.replace`），即使被截断也不会损坏已有 `compile_commands.json`。

---

## 步骤 3：.clangd 配置原则

`.clangd` 只负责移除 clangd 不兼容或无意义的编译器参数，并指定 `CompilationDatabase: .`。

不要在 `.clangd` 中额外添加 `--target`、`-mcpu`、`-mfpu`、`-mfloat-abi` 或系统头路径。
这些信息应来自 `compile_commands.json` 的真实构建命令。额外追加目标参数会和不同项目、
不同芯片或不同工具链的编译数据库冲突，导致 clangd 索引残缺、头文件 inactive region 判断错误。

## 步骤 4：验证

```bash
# 检查文件存在
ls -la compile_commands.json .clangd

# 验证 JSON
python -c "import json; data=json.load(open('compile_commands.json')); print(f'OK: {len(data)} entries')"

# 检查 clangd（如已安装）
which clangd && clangd --version || echo "clangd 未安装，可后续安装验证"
```

验证时额外检查：

- `compile_commands.json` 条目数是否明显过少；若只有少量文件，优先怀疑 clean/rebuild 不完整
- `compile_commands.json` 是否包含关键头文件条目；例如 `ssl_tls13_keys.h` 这类被源码直接包含的头文件应有自己的 `file` 条目
- 检查 JSON 是否完整：如果条目数异常少或末尾行缺失（JSON 解析失败），说明脚本可能被超时截断，应延长超时重新运行
- 检查 `-D` 宏配置头文件是否已覆盖：搜索 `MBEDTLS_CONFIG_FILE`、`OTP_CONFIG_FILE` 等宏指定的头文件是否出现在 `compile_commands.json` 的 `file` 字段中
- 检查关键预包含头是否仍存在；例如 ARMCC 项目应能看到 `-include xxx_cfg.h`
- **硬性门禁：gbk_src 副本残留检测**。必须运行以下检查，0 matched 才算通过：
  ```bash
  python -c "import json; data=json.load(open('compile_commands.json')); gbk=[e for e in data if 'gbk_src' in e.get('file','')]; print(f'gbk_src残留: {len(gbk)} 条'); [print(f'  {e[\"file\"]}') for e in gbk]"
  ```
  若有残留，必须逐条回写 file 字段到原始源码路径（去除 gbk_src/ 前缀），直到上述命令输出 0 条为止
- `.clangd` 中不应出现全局 `CompileFlags.Add` 注入目标架构参数
- 如果未传 `--keep-build-log`，确认 `build_log.txt` 已被自动清理

---

## 资源

| 资源 | 路径 | 用途 |
|------|------|------|
| CompilerGen.py | `scripts/CompilerGen.py` | Windows 下从构建日志解析生成 compile_commands.json 和 .clangd |
