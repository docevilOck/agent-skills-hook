---
name: ddev-comment-gen
description: C 项目注释生成与审查节点。在 ddev-c-pro 编码规范审查通过后，对 .c/.h 文件逐项检查注释完整性并补齐缺失注释。由 ddev-gate 调度，作为 c-pro 之后的独立审查步骤。
---

# DDev Comment Gen — C 项目注释审查与生成

在 ddev-c-pro 编码规范审查通过后，由 ddev-gate 拉起独立 subagent 加载本 skill，对代码注释做系统性审查和补全。

## 定位

- **触发时机**：ddev-c-pro 审查 `pass` 后，ddev-gate 拉起
- **输入**：通过 ddev-c-pro 审查的最终代码（`.c` / `.h`）
- **输出**：`pass`（注释齐全）或 `blocked`（附缺失项清单 + 补全建议）
- **审查范围**：与 ddev-c-pro 审查范围一致的文件集合

## 审查维度

审查 agent 必须**逐文件、逐函数、逐结构体/枚举**核验，不得仅凭印象判断。

### 1. 文件头注释

- 每个 `.h` 和 `.c` 文件必须包含 `@file` + `@brief` 头注释
- `@brief` 须说明本文件的主要职责，不能仅重复文件名

```c
/**
 * @file module.h
 * @brief 模块公开 API 定义，提供初始化和数据处理接口
 */
```

### 2. 公开 API 函数注释

每个在 `.h` 中声明的公开函数必须包含完整 Doxygen 注释：

- `@brief`：一句话说明函数做什么
- `@param`：每个参数一个，说明含义、约束（是否可为 NULL、取值范围）
- `@return`：返回值含义（无返回值写"无"或"void"）
- `@note` / `@warning` / `@see`：按需添加

```c
/**
 * @brief  模块初始化，分配并配置硬件资源。
 * @param  cfg  配置参数，不可为 NULL，baud 须 > 0。
 * @return      MODULE_OK (0) 成功，其他为错误码。
 * @note       重复调用前须先 module_deinit。
 */
module_status_t module_init(const module_cfg_t *cfg);
```

### 3. 结构体与枚举注释

- 每个 `struct` / `union` 定义必须有 `@brief` 说明用途
- 每个结构体成员必须有 `/**< 说明 */` 行内注释
- 每个 `enum` 必须有 `@brief` 说明枚举用途
- 枚举值有非直观含义时必须加 `/**< 说明 */` 行内注释

```c
/** @brief 模块运行时上下文 */
typedef struct {
    uint32_t baud;          /**< 当前波特率 */
    volatile bool running;  /**< ISR 与主循环共享，仅原子读写 */
    uint8_t rx_buf[256];    /**< 接收环形缓冲区 */
} module_t;

/** @brief 模块操作状态码 */
typedef enum {
    MODULE_OK = 0,              /**< 成功 */
    MODULE_ERR_INVALID_ARG,    /**< 参数非法 */
    MODULE_ERR_TIMEOUT,        /**< 操作超时 */
} module_status_t;
```

### 4. 私有函数注释

- `static` 函数不强制 Doxygen 格式，但复杂逻辑必须说明意图
- 超过 30 行的 `static` 函数建议添加简要块注释说明职责

### 5. 关键逻辑注释

- 非直观算法、状态机切换、边界条件处理须有少量行内注释
- 注释解释"为什么这样做"，不重复代码本身
- 中断回调、错误恢复路径、硬件 workaround 必须有注释说明

### 6. 注释一致性

- 注释内容必须与实际代码行为一致
- 修改函数签名时必须同步更新注释
- 修改函数行为时必须同步更新注释

## 注释规范

- 使用简洁中文描述"做了什么 + 为什么/约束"
- 使用项目统一的 Doxygen 风格（`/** */` 或 `///`）
- 常用 Doxygen 标签：`@brief` / `@param` / `@return` / `@note` / `@warning` / `@see` / `@todo` / `@retval`

## 审查流程

1. 遍历所有目标 `.h` 文件，逐一检查文件头、公开函数、结构体、枚举的注释完整性
2. 遍历所有目标 `.c` 文件，逐一检查文件头、私有函数的注释完整性
3. 检查关键逻辑（中断 ISR、错误恢复、状态机、复杂算法）的注释覆盖
4. 缺失或不足的项逐条记录（文件:行号 + 缺失项 + 补全建议文本）
5. 全部通过 → `pass`；任一缺失 → `blocked` + 附缺失项清单

## 审查结论格式

```
ddev-comment-gen 审查结论：[pass | blocked]

若 blocked，清单：
- module.h:42 — module_init 缺少 @param cfg 注释
- module.c:10 — 缺少 @file 头注释
- module.h:25 — module_cfg_t 结构体缺少 @brief，成员 baud 缺少行内注释
- module.c:88 — ISR 回调缺少说明注释
```

## 审查模式

当本 skill 被 ddev-gate 作为注释审查子代理加载时，必须使用 `reviewer-prompt.md` 作为任务模板执行审查。该模板定义了审查输入、审查维度优先级、CodeGraph 辅助查询方法和输出格式。

## 进度记录

审查完成后将结果写入项目根目录的 `progress.md`：

- 通过：记录"comment-gen 审查通过"，附检查项通过数/总项数
- 阻塞：记录"comment-gen 审查发现 N 个阻塞项"，逐项列出文件:行号 + 问题描述
- 追加时间戳和审查结论到最近一次执行日志后
