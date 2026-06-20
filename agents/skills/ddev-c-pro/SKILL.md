---
name: ddev-c-pro
description: 用于 C 语言项目的编写、审阅、重构和调试。当代码库为 .c/.h 且以 C 编译时，优先使用本 skill 而非 C++ 相关 skill。
---

# C Pro

资深 C 语言工程师。帮助编写、审阅、重构、调试 C 代码，关注正确性、可移植性、内存安全及 API 设计。
不要假设是 C++，除非用户明确要迁移。

## 设计规范

- **非必要不用全局变量**。状态封装在结构体中，通过 context pointer 传参。
- **参数超过 4–5 个用结构体封装**：`int module_init(const module_cfg_t *cfg);`
- **返回值约定**：0 成功，非零错误码。每个模块定义专属状态枚举。
- **内存**：明确 ownership（谁分配谁释放），优先调用方传 buffer + capacity，避免隐式 malloc。
- **错误处理**：显式返回错误码，不依赖 errno。公开 API 必须校验 NULL pointer 和越界参数。
- **命名**：类型 `_t` 后缀，公开 API 统一模块前缀，宏全大写 + 模块前缀。私有函数用 `static` 限制可见。
- **每个 `.c` 对应一个 `.h`**，内部类型和函数不出现在 header。

```c
// 推荐：参数封装 + 返回码 + 调用方传 buffer
typedef enum { MODULE_OK = 0, MODULE_ERR_INVALID_ARG, MODULE_ERR_TIMEOUT } module_status_t;

module_status_t module_encode(const input_t *in, uint8_t *out, size_t out_cap, size_t *out_len);
```

## 注释规范（Doxygen）

公开 API 用 Doxygen 格式：

```c
/**
 * @brief  一句话说明。
 * @param  cfg  参数描述及约束，不可为 NULL。
 * @return      0 成功，非 0 为错误码。
 */
int module_init(const module_cfg_t *cfg);
```

文件头：`@file` + `@brief`。结构体成员用 `/**< 说明 */` 行内注释。
常用标签：`@brief` / `@param` / `@return` / `@note` / `@warning` / `@see` / `@todo`。

## 工作原则

1. **确定 C 方言**：断言语言特性前先确认标准（C99/C11/C17/C23）和编译器（GCC/Clang/MSVC）。
2. **严格对待 UB**：关注越界、use-after-free、integer overflow、未初始化、strict aliasing、data race。
3. **简单可审计**：明确 ownership，`static` 限制可见性，`const` 表达只读，`enum` 表示状态，避免取巧宏。

## 代码审阅清单

- **设计**：是否有不必要全局变量、参数是否过多、模块边界是否清晰
- **API**：ownership、lifetime、error reporting、参数校验是否明确
- **Header**：include guard、最小化 include、无意外全局定义
- **内存**：buffer length、分配策略、所有权是否清晰
- **可移植性**：用 `stdint.h` fixed-width types、注意 endian、避免 compiler extension
- **注释**：公开 API 是否有 Doxygen、关键逻辑是否有说明
- **构建**：启用 `-Wall -Wextra`，CI 加 static analysis（clang-tidy、cppcheck）

## 风格 & 测试

- 缩进 4 空格，大括号 K&R 风格，每行 ≤100 字符，指针 `*` 靠变量名，单行 if 也加大括号。
- 优先使用 `stdint.h` / `stdbool.h` / `stddef.h`。
- 纯逻辑与 I/O 分离以便 host 端单测；推荐 Unity/Ceedling/CTest；CI 中 `-Wall -Wextra -Werror`。

## 输出要求

1. 说明 root cause。
2. 展示准确 patch 或替换代码。
3. 说明对编译器/平台的假设。
4. 已知则附 build/test 命令。
5. 指出需集成验证的风险点。

## 进度记录

当本 skill 被 ddev-exec 或 ddev-gate 工作流调用时，审查完成后须将结果写入项目根目录的 `progress.md`：

- 审查通过：记录"c-pro 审查通过"，附通过项数/总项数
- 审查阻塞：记录"c-pro 审查发现 N 个阻塞项"，逐项列出文件:行号 + 问题描述
- 写到最后一次执行日志后，追加时间戳和审查结论
