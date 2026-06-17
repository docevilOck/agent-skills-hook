# 标准验收输出样例

下面是一份可直接仿照的最终验收输出样例。

```md
结论：`need-info`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/dataflow/uart-rx-flow.md`
- exec plan：`docs/plans/26-05-18_uart_refactor/exec-plan.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- 验证材料：`cmake --build build`、`ctest --output-on-failure`
- cleanup stage：未进入
- c-pro review stage：未进入

差异归类：
- 实现偏离设计，需要修代码
- 实现偏离 exec plan，需要修代码
- 证据不足，当前不能给 `pass`

发现的问题：
1. High：[src/uart/uart_session.c] 中接收状态仍通过 `g_uart_rx_state` 维护，与 architecture 文档要求的 `uart_session_t` 上下文收敛不一致。
2. Medium：detail 文档要求命令分发改为 `switch (packet->cmd)`，当前实现仍保留 6 段长链 `if/else if`。
3. Medium：`UART_STATE_RX_PAYLOAD` 已在 detail 文档定义为枚举状态，但错误恢复分支仍直接写入裸值 `3`。
4. Medium：exec plan 中要求“先移除旧全局状态，再补上下文初始化测试”，当前代码里测试已补，但旧全局状态仍残留。

已确认一致的关键点：
- `uart_session_t` 已建立，并承接了缓冲区、长度和重试计数。
- 对外接口仍保持在 `uart_session_init()` / `uart_session_feed()`，与 architecture 文档一致。
- 错误码风格与 detail 文档定义一致，未发现新的随意返回值。

需要主 agent 修改的项：
- 把 `g_uart_rx_state` 下沉到 `uart_session_t`
- 把长链 `if/else if` 改成 detail 文档约定的 `switch (packet->cmd)`
- 去掉裸状态值 `3`，改回 `uart_state_t` 枚举语义
- 按 exec plan 移除旧全局状态后重新跑验证，再重新进入 `implementation-final-gate`

未覆盖风险：
- 当前只看了 host 构建和单元测试，未看到目标板串口回环验证结果。
- 尚未确认异常包风暴场景下的状态迁移是否与流程图完全一致。

下一步：
- 主 agent 必须先修改上述项，再重新进入 `implementation-final-gate`
```

## `pass` 样例

```md
结论：`pass`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/structures/uart-session-struct.md`
- exec plan：`docs/plans/26-05-18_uart_refactor/exec-plan.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- 验证材料：本轮重新执行 `cmake --build build`、`ctest --output-on-failure`
- cleanup stage：已进入且有代码修改并已重审
- c-pro review stage：已进入并已通过

差异归类：
- 未发现需要升级处理的设计差异

发现的问题：
- 无

已确认一致的关键点：
- 接收状态、缓冲区和重试计数已全部收敛到 `uart_session_t`
- 命令分发已按 detail 文档改为 `switch (packet->cmd)`
- 状态迁移使用 `uart_state_t` 枚举，未发现裸状态值

需要主 agent 修改的项：
- 无

未覆盖风险：
- 尚未覆盖更大输入规模下的性能回归，但这不影响本轮以 host 行为和静态结构一致性为目标的验收结论

下一步：
- 可进入正式收尾或后续提交流程
```

## `blocked` 样例

```md
结论：`blocked`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：未定位到唯一有效文档
- exec plan：`docs/plans/26-05-18_uart_refactor/exec-plan.md`
- code：`src/uart/uart_session.c`
- 验证材料：无
- cleanup stage：未进入
- c-pro review stage：未进入

差异归类：
- 设计本身不完整，需要补文档

发现的问题：
1. High：当前目录下存在两个互相冲突的 detail 文档，无法判断应以哪个结构体定义和流程图为准。
2. High：在无法确定 detail 基线的情况下，无法判断当前实现偏离的是代码还是设计。

已确认一致的关键点：
- architecture 文档已定位。

需要主 agent 修改的项：
- 先唯一确定可用的 detail 文档基线
- 确认本轮应采用的结构体定义和流程图后，再重新进入 `implementation-final-gate`

未覆盖风险：
- 因 detail 基线不明确，本轮无法形成有效的一致性验收结论。

下一步：
- 主 agent 必须先补齐或统一 detail 基线，再重新进入 `implementation-final-gate`
```

## 使用要求

- 结论只能是 `pass`、`need-info`、`blocked`
- `对照范围` 必须点名具体文档和代码路径
- `差异归类` 必须出现，且要能指导后续动作
- `需要主 agent 修改的项` 必须出现；若无修改项，要明确写 `无`
- `发现的问题` 优先写与设计不一致的内容，不要泛泛评论代码风格
- `已确认一致的关键点` 只列最重要的事实
- `未覆盖风险` 必须写真实缺口，不允许省略
- `cleanup stage` 必须写清是否进入 cleanup、是否改代码、是否已经重审
- `c-pro review stage` 必须写清是否进入、是否通过；若为 C 代码项目此为必填
- 如果结论是 `blocked`，必须明确写出”主 agent 需要修改的项”，以便回炉后重审
