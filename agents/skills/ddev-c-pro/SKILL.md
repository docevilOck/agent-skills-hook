---
name: ddev-c-pro
description: 用于 C 语言项目的编写、审阅、重构和调试。当代码库为 .c/.h 且以 C 编译时，优先使用本 skill 而非 C++ 相关 skill。
---

# C Pro

资深 C 语言工程师。帮助编写、审阅、重构、调试 C 代码，关注正确性、可移植性、内存安全及 API 设计。
不要假设是 C++，除非用户明确要迁移。

## 设计规范

### 状态与数据封装

- **非必要不用全局变量**。状态封装在结构体中，通过 context pointer 传参。
- **参数超过 4–5 个用结构体封装**：`int module_init(const module_cfg_t *cfg);`
- 配置、运行时状态、输入载荷、输出结果分开建模，不要混在一个大结构体里。
- **每个 `.c` 对应一个 `.h`**，内部类型和函数不出现在 header。

### 错误码体系

- **返回值约定**：0 成功，非零错误码。每个模块定义专属 `_status_t` 或 `_ret_t` 枚举。
- **禁止混用 errno 和自定义错误码**。公开 API 不依赖 errno。
- 大型项目建议错误码编码：`(MODULE_ID << 8) | ERROR_CODE`，方便跨模块定位。
- 每个模块提供 `const char *module_strerror(module_status_t code)` 用于调试输出。
- 通用错误码保留范围：`0` 成功，`-1`/`ERR_GENERIC` 通用失败，`-2`/`ERR_INVALID_ARG` 参数错误。

```c
// 推荐：参数封装 + 返回码 + 调用方传 buffer
typedef enum {
    MODULE_OK = 0,
    MODULE_ERR_INVALID_ARG,
    MODULE_ERR_BUSY,
    MODULE_ERR_TIMEOUT,
    MODULE_ERR_OVERFLOW,
} module_status_t;

module_status_t module_encode(const input_t *in, uint8_t *out, size_t out_cap, size_t *out_len);
```

### 结构体设计

- **成员排序**：按语义分组（配置块 → 运行时状态 → 缓存/缓冲区 → 输出结果），每组之间用空行分隔。内存极度紧张时再考虑按对齐优化重排。
- **指定初始化器**：优先用 C99 指定初始化，禁止 `memset` + 逐字段赋值。
  ```c
  // 推荐
  module_cfg_t cfg = { .baud = 115200, .parity = PARITY_NONE };
  // 禁止
  module_cfg_t cfg;
  memset(&cfg, 0, sizeof(cfg));
  cfg.baud = 115200;
  cfg.parity = PARITY_NONE;
  ```
- **bit-field 谨慎使用**：位序依赖编译器实现。跨平台或涉及序列化/协议的字段禁止用 bit-field，改用位掩码 + 移位。
- **柔性数组成员（FAM）**：用于变长载荷时合法，但必须配合长度字段；禁止 FAM 结构体按值传递或放在栈上。
- **跨端通信结构体**：必须显式标注 endian 转换函数，用固定宽度类型（`uint16_t` 非 `short`）。
- 如需要 ABI 兼容或版本持久化，结构体末尾预留 `uint8_t reserved[N]`。

### 函数设计

- **长度上限**：单函数 ≤ 80 行（不含注释和空行）。超过则按职责拆分私有 `static` 辅助函数。
- **圈复杂度**：单函数分支路径数 ≤ 10。长链 `if/else` 超过 4 个固定分支改用 `switch`、表驱动或状态机。
- **`inline` 函数**：仅用于 ≤ 5 行的简单访问器/包装器；≥ 10 行的实现不要放 `.h`。
- **回调注册**：回调函数签名统一 typedef → 注册函数 → 调用点，三步缺一不可。
  ```c
  typedef void (*uart_rx_cb_t)(uint8_t byte, void *user_data);
  void uart_set_rx_callback(uart_t *u, uart_rx_cb_t cb, void *user_data);
  ```
- **变参函数（`...`）禁止在公开 API 中使用**，调试日志可用 `__attribute__((format(printf, ...)))` 做编译期格式检查。
- **纯函数标记**：不访问全局状态、不修改参数的函数标注 `__attribute__((const))` 或 `__attribute__((pure))` 辅助编译器优化。

### 中断/并发安全

- **ISR 三禁**：禁止调用非 ISR-safe 函数、禁止阻塞操作（while 死等）、禁止动态内存分配（`malloc`/`free`）。
- **`volatile` 仅用于**：MMIO 寄存器、ISR 与主循环间共享的标志变量。`volatile` 不保证原子性 —— 多字节变量在 ISR 中读写必须配合临界区保护。
- **共享数据保护策略**：
  - 单生产者/单消费者简单标志 → `volatile sig_atomic_t` 或 `_Atomic`
  - 多字节共享变量 → `__disable_irq()` / `__enable_irq()` 临界区
  - 复杂共享结构体 → 关中断 + 最小临界区（只保护读写操作，不保护处理逻辑）
- **禁止在主循环和 ISR 中同时写同一个非原子变量**，即使"看起来不会冲突"。
- 多核/RTOS 场景：任务间共享资源用互斥锁，ISR 与任务间用关中断 + 无锁单向队列。

### 栈与静态内存

- **大数组不放栈**：超过 256 字节的数组/缓冲区默认放静态区（`static`）或堆，不放函数局部栈。
- **递归深度约束**：禁止依赖递归处理未知深度数据。如果必须递归，在函数注释中显式声明最大深度。
- **固件全局结构体**标注预期内存分区：`.bss` 零初始化 / `.data` 带初值 / `.noinit` 复位后保留。
- **启动文件**中必须显式声明栈大小和堆大小，并在注释中说明计算依据。
- **VLA（变长数组）禁止**：不在栈上分配运行时决定大小的数组。用静态区 buffer 或堆分配。
- 静态分配 buffer 时使用 `static_assert(sizeof(buffer) >= MIN_REQUIRED, "...")` 做编译期验证。

### 返回值与错误处理

- **显式返回错误码**，不依赖 errno。公开 API 必须校验 NULL pointer 和越界参数。
- **内存**：明确 ownership（谁分配谁释放），优先调用方传 buffer + capacity，避免隐式 malloc。
- **错误路径资源回滚**：分配多个资源后任一失败，必须回滚已分配的资源，用 `goto` 统一清理出口（唯一允许的 `goto` 用法）。

### 标准库替代函数（优先使用工程封装）

许多嵌入式固件工程会对标准库函数做二次封装，增加边界检查、错误日志、内存池管理或平台适配。**编写、审查或计划代码时，必须先检查工程中是否存在标准库函数的替代封装，优先使用工程封装而非裸调标准库。**

#### 常见标准库函数及其典型替代封装

| 标准库函数 | 典型工程封装 | 工程封装的常见增强 |
|-----------|-------------|------------------|
| `malloc` / `calloc` | `os_malloc` / `pvPortMalloc` / `mod_mem_alloc` | 内存池、对齐、失败日志 |
| `free` | `os_free` / `vPortFree` / `mod_mem_free` | 内存池回收、指针置 NULL |
| `memcpy` / `memmove` | `mod_memcpy_s` / `safe_memcpy` | 长度校验、重叠检查 |
| `memset` | `mod_memset` / 无替代（通常直接使用） | — |
| `strcpy` / `strncpy` | `mod_strcpy_s` / `safe_strcpy` | 缓冲区大小强制传入 |
| `strcat` / `strncat` | `mod_strcat_s` / `safe_strcat` | 剩余空间检查 |
| `strlen` | 通常直接使用 / `mod_strnlen` | 最大长度限制 |
| `sprintf` / `snprintf` | `mod_snprintf` / `log_snprintf` | 截断检测、返回值校验 |
| `sscanf` | `mod_sscanf` / 无替代 | 输入校验 |
| `fopen` / `fclose` | `mod_fs_open` / `fs_fopen` | 文件系统抽象、错误映射 |
| `fread` / `fwrite` | `mod_fs_read` / `fs_fwrite` | 重试、超时、错误恢复 |
| `printf` | `log_info` / `LOG_INFO` / 无替代 | 日志级别、模块标签 |
| `assert` | `MOD_ASSERT` / `configASSERT` | 平台特定断言行为 |

#### 审查前收集

在开始编写代码或做审查之前，必须：

1. **检查工程的标准库替代文档**：如果 `docs/architecture/stdlib-wrappers.md` 存在，先读取该文档，了解工程中已有的全部替代封装
2. **搜索工程头文件**：如果替代文档不存在，搜索 `*.h` 中的内存分配/字符串操作/文件 I/O 封装函数
3. **优先使用工程封装**：所有通过搜索发现的工程封装函数，如果提供了标准库函数的等价功能，必须优先使用

#### 强制约束

- 如果工程存在 `malloc` 替代（如 `os_malloc`），**禁止直接使用 `malloc`**
- 如果工程存在字符串安全操作封装，**禁止使用裸 `strcpy`/`strcat`/`sprintf`**
- 审查时发现裸调标准库函数而工程中存在替代封装 → `blocked`
- 如果工程的标准库替代文档（`docs/architecture/stdlib-wrappers.md`）不存在或已过期，应在审查意见中标注 `need-info`，建议先运行 `ddev-arch` 的标准库审计步骤

#### 第三方库封装适配（禁止第三方库脱离工程体系）

引入或使用第三方库（如 FatFs、lwIP、mbedTLS、FreeRTOS、protobuf-c 等）时，**禁止让第三方库直接裸调标准库函数**。必须通过适配层注入工程的替代封装，确保第三方库运行在工程统一的内存/IO/断言体系内。

**适配方式（按优先级）：**

1. **利用第三方库的配置宏**：多数嵌入式第三方库提供了内存分配/断言/IO 的配置入口：
   ```c
   // FatFs 示例：在 ffconf.h 中重定向
   #define ff_memalloc(n)  os_malloc(n)
   #define ff_memfree(p)   os_free(p)
   
   // FreeRTOS 示例：在 FreeRTOSConfig.h 中重定向
   #define configASSERT(x)  MOD_ASSERT(x)
   
   // mbedTLS 示例：在 mbedtls_config.h 中重定向
   #define MBEDTLS_PLATFORM_MEMORY
   #define mbedtls_calloc(n, s)  os_calloc(n, s)
   #define mbedtls_free(p)       os_free(p)
   ```
2. **如果第三方库不支持配置宏，写轻量适配层**：新建 `thirdparty/<libname>/<libname>_port.c`，实现第三方库期望的接口签名，内部转发到工程封装：
   ```c
   // thirdparty/lwip/lwip_port.c
   #include "os/heap.h"
   
   // lwIP 期望的内存分配函数 → 转发到工程封装
   void *mem_malloc(mem_size_t size) { return os_malloc((size_t)size); }
   void  mem_free(void *ptr)          { os_free(ptr); }
   ```
3. **如果第三方库不支持任何方式替换，必须在架构文档中显式声明风险**：标注该库绕过了工程体系，明确允许的例外范围。

**强制约束：**

- 引入第三方库时，**必须在 spec/detail 阶段就确认其 stdlib 依赖是否能通过工程封装满足**
- 适配代码必须与第三方库源码分离（放在独立 `_port.c` 或配置头文件中），不直接修改第三方库原始文件
- 审查时发现第三方库裸调标准库而无适配封装 → `blocked`
- `docs/architecture/stdlib-wrappers.md` 中必须记录每个第三方库的适配策略

## 头文件规范

- **自包含（self-contained）**：每个头文件必须独立可编译。用以下方式验证：
  ```c
  // 模块自身头文件必须最先 include，确保不依赖 include 顺序
  #include "module_under_test.h"
  #include <stdint.h>
  // ...
  ```
- **include guard**：推荐 `#pragma once`（现代编译器通用）；若需最大兼容性用 `#ifndef MODULE_H_` / `#define MODULE_H_` / `#endif` 传统守卫。
- **include 顺序**：对应自身的 `.h` → 标准库 `<stdint.h>` `<stdbool.h>` 等 → 第三方库 → 本项目其他模块。空行分隔四组。
- **前向声明优先**：当仅用到类型的指针/引用时，用前向声明而非 `#include`，减少编译依赖。
  ```c
  // 头文件中：前向声明即可
  typedef struct uart_s uart_t;
  int uart_send(uart_t *u, const uint8_t *data, size_t len);
  // .c 文件中再 include 完整定义
  ```
- **最小化 include**：头文件只 include 自身必需的类型。实现文件（`.c`）需要的头文件不放进 `.h`。
- **禁止在头文件中暴露内部类型**：仅公开 API 需要的 typedef、enum、struct 定义放 `.h`，内部辅助类型放 `.c`。
- 头文件中不定义变量（`extern` 声明即可）、不定义 `static` 函数实现。
- 每个 `.c` 对应一个 `.h`，公开 `.h`，私有的 `static` 函数声明放 `.c` 顶部。

## 常量与宏规范

- **类型选择**：
  - `enum`：状态码、错误码、有限集合的离散值
  - `static const`：只读常量数据（数组、结构体）
  - `#define`：编译期常量、条件编译开关（`#if`/`#ifdef`）、版本号
- **宏函数必须用 `do { ... } while (0)` 包装**，避免 if/else 悬挂问题：
  ```c
  #define LOG_ERR(fmt, ...) do { \
      if (g_log_level >= LOG_LVL_ERR) { printf("[ERR] " fmt "\n", ##__VA_ARGS__); } \
  } while (0)
  ```
- **宏参数加括号**：`#define MAX(a, b) ((a) > (b) ? (a) : (b))` — 函数式宏必须标注多次求值风险（副作用参数如 `MAX(i++, j)` 会导致 bug）。
- **禁止宏覆盖标准库符号、关键字**。禁止用宏改变语言语义（如 `#define private public`）。
- 多语句宏用 `do-while(0)` 包装；多行宏对齐续行符 `\`。
- 条件编译用 `#if` 而非 `#ifdef` 做特性开关（`#if FEATURE_ENABLED` 优于 `#ifdef FEATURE_ENABLED`，前者遗漏定义时报错而非静默跳过）。
- 复杂表达式拆成 `static inline` 函数优于宏，利用类型检查和调试友好性。

### 魔术字禁止（No Magic Numbers）

**所有非 0/1/-1 的字面量必须定义为命名常量。** 裸数字出现在代码中即为违规，审查时标记为 `blocked`。

- **必须命名常量化的字面量**（非穷举）：
  - 超时毫秒数、延时 tick 数
  - 缓冲区大小、数组长度
  - 重试次数、最大连接数
  - 状态值、错误码（已有 enum 的不重复定义）
  - 寄存器地址、位掩码偏移
  - 协议字段长度、MTU、包大小
  - GPIO 引脚号、外设基地址
- **命名方式**：`#define MODULE_TIMEOUT_MS 3000` / `static const uint32_t kRetryMax = 5;` / `enum { BUF_SIZE = 256 };`
- **大数字可读化**：≥ 1024 的数量（缓冲区大小、字节数、容量等）必须用 `N * 1024` / `N * 1024 * 1024`（KB/MB 语义）的可读表达式书写，并**优先定义为宏**，禁止裸写大数（如 `16384`、`4194304`）：
  ```c
  // 推荐：单位即语义，128 * 1024 一眼看出是 128 KB
  #define MOD_TX_BUF_SIZE      (16 * 1024)        // 16 KB 发送缓冲
  #define MOD_IMAGE_MAX_SIZE   (4 * 1024 * 1024)  // 4 MB 固件镜像上限
  // 禁止：16384 / 4194304 无法直接读成 KB/MB
  #define MOD_TX_BUF_SIZE      16384
  #define MOD_IMAGE_MAX_SIZE   4194304
  ```
- **注释要求**：每个常量定义必须用行内注释说明取值依据（数据手册章节、协议规范、实测标定）
- **例外**：`0`/`1`/`-1` 用于循环初始值、数组索引、真/假比较、指针 NULL 检查时不要求命名；但用于业务语义（如 `if (state == 1)`）必须用 enum 替代

## 工作原则

1. **确定 C 方言**：断言语言特性前先确认标准（C99/C11/C17/C23）和编译器（GCC/Clang/MSVC）。
2. **严格对待 UB**：关注越界、use-after-free、integer overflow、未初始化、strict aliasing、data race。
3. **简单可审计**：明确 ownership，`static` 限制可见性，`const` 表达只读，`enum` 表示状态，避免取巧宏。

## 代码审阅清单

- **设计**：是否有不必要全局变量、参数是否过多、模块边界是否清晰
- **API**：ownership、lifetime、error reporting、参数校验是否明确
- **Header**：include guard、最小化 include、自包含、前向声明优先、无内部类型泄露
- **内存**：buffer length、分配策略、所有权是否清晰；大数组是否在栈上
- **中断/并发**：ISR 中是否禁止阻塞/分配/非安全调用；共享变量是否有保护；volatile 使用是否合理
- **错误码**：是否定义了模块专属状态枚举、是否混用 errno、是否提供 strerror
- **结构体**：指定初始化器、bit-field 风险、endian 转换、成员语义分组
- **函数**：长度和复杂度是否超标、inline 是否合理、回调是否 typedef
- **标准库替代**：是否裸调了工程中有替代封装的标准库函数（malloc/strcpy/sprintf/fopen 等）；若工程存在 `stdlib-wrappers.md`，是否已读取并遵守
- **宏**：参数是否加括号、多语句是否 do-while(0)、是否用 static inline 更合适
- **可移植性**：用 `stdint.h` fixed-width types、注意 endian、避免 compiler extension
- **构建**：启用 `-Wall -Wextra`，CI 加 static analysis（clang-tidy、cppcheck）
- **命名**：类型 `_t` 后缀、公开 API 模块前缀、宏全大写 + 模块前缀、私有函数 `static`
- **安全**：硬编码凭据/密钥/令牌、缓冲区溢出、注入风险（格式字符串、命令注入）、路径遍历、敏感数据日志泄露、整数溢出导致的安全绕过
- **架构性能**：跨模块调用链中的 N+1 模式、不合理算法选择（O(n²) 可优化为 O(n) 或 O(n log n)）、不必要的重复内存分配、缺失的缓存策略（如适用）
- **死代码与重复**：未被调用的 static 函数、不可达分支、跨文件的重复逻辑（DRY 违规）
- **魔术字**：是否出现非 0/1/-1 的裸字面量（毫秒数、缓冲区大小、重试次数、寄存器地址等），必须替换为命名常量 + 注释说明取值依据；缓冲区大小等大数字（≥1024）必须用 `N * 1024` 表达式 + 宏，禁止裸写大数

## 风格 & 测试

- 缩进 4 空格，大括号 K&R 风格，每行 ≤100 字符，指针 `*` 靠变量名，单行 if 也加大括号。
- 优先使用 `stdint.h` / `stdbool.h` / `stddef.h`。
- **命名规范**：类型 `_t` 后缀（`module_cfg_t`），公开 API 统一模块前缀（`module_init`），宏全大写 + 模块前缀（`MODULE_BUF_SIZE`），私有函数 `static` 限制可见。
- 纯逻辑与 I/O 分离以便 host 端单测；推荐 Unity/Ceedling/CTest；CI 中 `-Wall -Wextra -Werror`。
- **推荐编译警告**（GCC/Clang）：`-Wall -Wextra -Wshadow -Wundef -Wconversion -Wenum-conversion -Wmissing-prototypes -Wstrict-prototypes -Wcast-align`。
- 静态分析：CI 中集成 clang-tidy 或 cppcheck；关注 `readability-*`、`bugprone-*`、`performance-*` 规则集。
- **测试文件命名**：`test_<module>.c`，放在 `test/` 目录。mock 硬件依赖通过回调注入或链接期替换。

## 输出要求

1. 说明 root cause。
2. 展示准确 patch 或替换代码。
3. 说明对编译器/平台的假设。
4. 已知则附 build/test 命令。
5. 指出需集成验证的风险点。

## 审查模式

当本 skill 被 ddev-gate 作为 C 代码审查子代理加载时（已吸收原 `ddev-code-review` 的代码质量审查职责），必须使用 `reviewer-prompt.md` 作为任务模板执行审查。该模板定义了审查输入、维度优先级、CodeGraph 辅助查询方法和输出格式。

审查覆盖范围：C 编码规范 + 代码质量（安全、架构性能、死代码/重复）。C 项目的 ddev-gate 流程中不再单独调用 `ddev-code-review`，由本 skill 统一完成。

## 进度记录

当本 skill 被 ddev-exec 或 ddev-gate 工作流调用时，审查完成后须将结果写入项目根目录的 `progress.md`：

- 审查通过：记录"c-pro 审查通过"，附通过项数/总项数
- 审查阻塞：记录"c-pro 审查发现 N 个阻塞项"，逐项列出文件:行号 + 问题描述
- 写到最后一次执行日志后，追加时间戳和审查结论
