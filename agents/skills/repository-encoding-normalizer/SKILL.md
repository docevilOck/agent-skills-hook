---
name: repository-encoding-normalizer
description: 仅当用户明确要求规范化源码仓库文件编码时使用；处理 armcc/armclang 嵌入式 C/C++ 项目中 UTF-8 与历史本地编码混合源码；若用户没有明确要求，禁止使用。
---

# 仓库编码规范化

## 核心原则

**按文件内容分类处理，不搞一刀切。**

1. **纯注释中文文件**：GBK 中文字符全部在注释中，无运行时字符串 → 转 UTF-8 with BOM
2. **含运行时中文文件**：有中文字符串字面量在代码中运行期使用 → **保持原始 GBK 编码，不转换**
3. **Makefile / 汇编**：转 UTF-8 无 BOM

**为什么运行时中文文件不转换？**

armcc/armclang 对 GBK 源码中的字符串字面量"原样保留字节"。源文件编码从 GBK 转 UTF-8 后，中文字符串的运行时字节语义会从 GBK 字节变为 UTF-8 字节，而打印机固件始终期望 GBK 字节。转换必然导致运行时乱码。

迁出到 hex 转义宏的"补救"方案已被实践证明有两大 bug 来源：
1. C 转义序列（`\r` `\n` 等）被逐字节转义为字面文本而非控制字节
2. 源文件中残留未覆盖的直接 UTF-8 中文字符串

**保留 GBK 是最少 bug 的策略。**

## 适用范围

用于含混合编码的 C/C++ 嵌入式源码仓库。常见目标包括 `.c` `.h` `.s` `.S` `.mk` 及文本资源。

## 工作流程

### 1. 扫描审计

```bash
python scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json
```

产出三类文件清单：
- `comment_only` — 中文只在注释中
- `string_or_runtime` / `mixed_comment_and_runtime` — 含运行时中文字符串
- `code_only_needs_review` — 中文在代码区

### 2. 分类处理

| 文件类别 | 处理方式 | 原因 |
|----------|---------|------|
| `comment_only`（GBK） | 转 UTF-8 with BOM | 注释可读，无运行时影响 |
| `string_or_runtime` / `mixed`（GBK） | **保持 GBK，不转换** | 运行时字节语义不能变 |
| 已 UTF-8 的文件 | 保持不动 | 无需处理 |
| `.mk` 文件 | 转 UTF-8 **无 BOM** | Make 工具不识别 BOM |
| `.s` / `.S` / startup 汇编 | 转 UTF-8 **无 BOM** | 汇编器不识别 BOM |
| `.txt` / `.md` / 纯文本 | 转 UTF-8 with BOM | 文档文件，不涉及运行时 |

### 3. 转换

```bash
# 仅转换 comment_only 文件和新类型文件
python normalize_encoding.py \
    --root . \
    --compiler armclang \
    --files "<comment_only 文件列表>" \
    --no-bom-files "<.mk/.s 文件列表>"
```

**禁用** `--macro-header` `--macro-name` `--macro-value` `--old-string` 等宏迁移参数。新策略不再需要创建 hex 转义宏。

### 4. 验证

```bash
# 基础检查
python check_mojibake.py --root . --files "<变更文件>.c,<变更文件>.h"

# 深度检查（含语义乱码检测）
python check_mojibake.py --root . --files "<变更文件>" --deep
```

验证清单：
- 确认运行时中文文件保持 GBK 编码
- 确认纯注释文件转为了 UTF-8 with BOM
- 确认 `.mk` / `.s` / `.S` 文件是 UTF-8 无 BOM
- 项目构建通过

### 5. 统一入口

```bash
python encoding_workflow.py scan    --root /path/to/repo                # 扫描
python encoding_workflow.py convert --root /path/to/repo --compiler armclang  # 转换
python encoding_workflow.py verify  --root /path/to/repo --deep         # 验证
```

## 常见错误

| 错误 | 正确做法 |
|---|---|
| 把运行时中文文件也转 UTF-8 | 保持 GBK，运行时字节语义不变 |
| 创建 hex 转义宏迁移运行期字符串 | 新策略不需要，保留 GBK 源文件即可 |
| `.mk` / `.s` 文件带 BOM | 必须 UTF-8 无 BOM |
| 编译器路径有反斜杠（Git Bash） | 用正斜杠覆盖 `ARMROOT="/c/Keil_v5/ARM"` |

## 安全门槛

遇到以下情况暂停并询问用户：
- 编码识别不确定
- 文件无法无损解码
- 中文文本处于协议字节、校验敏感数据、固件资源中
- 编译器/工具链无法处理 GBK 源码（需先验证）

## 交付标准

- 变更文件清单，标注每类处理方式
- 编译验证通过
- 乱码检查无新增问题
- 跳过的运行时中文文件清单及原因

---

## 工具脚本

### scan_encoding.py

扫描仓库目标文本文件，检测原始编码，识别中文字符位置（注释 vs 字符串字面量 vs 代码区），生成审计报告。

```bash
python scan_encoding.py --root . --out encoding_audit.md --json-out encoding_audit.json
```

### normalize_encoding.py

根据审计结果批量执行编码转换。只转换 `comment_only` / 纯文本 / `.mk` / 汇编文件，**不处理运行时中文文件**。

```bash
python normalize_encoding.py --root . --compiler armclang --files "a.c,b.h" --no-bom-files "c.mk"
```

### check_mojibake.py

转换后乱码巡检。检查 `�`、连续 `?`、`锟斤拷` 等典型乱码，BOM 误写，`--deep` 模式下含语义乱码检测。

```bash
python check_mojibake.py --root . --files "a.c,b.h" --deep
```

### encoding_workflow.py

统一入口，串联 scan → convert → verify 三步。

```bash
python encoding_workflow.py scan    --root .        # 扫描
python encoding_workflow.py convert --root . --compiler armclang  # 转换（仅 comment_only）
python encoding_workflow.py verify  --root . --deep  # 验证
```
