# 标准验收输出样例

下面是一份可直接仿照的最终验收输出样例。

```md
结论：`need-info`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/architecture/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/dataflow/uart-rx-flow.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- 验证材料：`cmake --build build`、`ctest --output-on-failure`

差异归类：
- 实现偏离设计，需要修代码
- 证据不足，当前不能给 `pass`

发现的问题：
1. High：[src/uart/uart_session.c] 中接收状态仍通过 `g_uart_rx_state` 维护，与 architecture 文档要求的 `uart_session_t` 上下文收敛不一致。
2. Medium：detail 文档要求命令分发改为 `switch (packet->cmd)`，当前实现仍保留 6 段长链 `if/else if`。
3. Medium：`UART_STATE_RX_PAYLOAD` 已在 detail 文档定义为枚举状态，但错误恢复分支仍直接写入裸值 `3`。

已确认一致的关键点：
- `uart_session_t` 已建立，并承接了缓冲区、长度和重试计数。
- 对外接口仍保持在 `uart_session_init()` / `uart_session_feed()`，与 architecture 文档一致。
- 错误码风格与 detail 文档定义一致，未发现新的随意返回值。

未覆盖风险：
- 当前只看了 host 构建和单元测试，未看到目标板串口回环验证结果。
- 尚未确认异常包风暴场景下的状态迁移是否与流程图完全一致。

建议动作：
- 先把 `g_uart_rx_state` 下沉到 `uart_session_t`。
- 把命令分发改成 detail 文档约定的 `switch` 结构。
- 修复裸状态值后重新运行验证，再进入下一轮验收。
```

## `pass` 样例

```md
结论：`pass`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/architecture/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/structures/uart-session-struct.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- 验证材料：本轮重新执行 `cmake --build build`、`ctest --output-on-failure`

差异归类：
- 未发现需要升级处理的设计差异

发现的问题：
- 无

已确认一致的关键点：
- 接收状态、缓冲区和重试计数已全部收敛到 `uart_session_t`
- 命令分发已按 detail 文档改为 `switch (packet->cmd)`
- 状态迁移使用 `uart_state_t` 枚举，未发现裸状态值

未覆盖风险：
- 尚未覆盖更大输入规模下的性能回归，但这不影响本轮以 host 行为和静态结构一致性为目标的验收结论
```

## `blocked` 样例

```md
结论：`blocked`

对照范围：
- architecture：`docs/plans/26-05-18_uart_refactor/architecture/uart-session.md`
- detail：未定位到唯一有效文档
- code：`src/uart/uart_session.c`
- 验证材料：无

差异归类：
- 设计本身不完整，需要补文档

发现的问题：
1. High：当前目录下存在两个互相冲突的 detail 文档，无法判断应以哪个结构体定义和流程图为准。
2. High：在无法确定 detail 基线的情况下，无法判断当前实现偏离的是代码还是设计。

已确认一致的关键点：
- architecture 文档已定位。

未覆盖风险：
- 因 detail 基线不明确，本轮无法形成有效的一致性验收结论。
```

## 使用要求

- 结论只能是 `pass`、`need-info`、`blocked`
- `对照范围` 必须点名具体文档和代码路径
- `差异归类` 必须出现，且要能指导后续动作
- `发现的问题` 优先写与设计不一致的内容，不要泛泛评论代码风格
- `已确认一致的关键点` 只列最重要的事实
- `未覆盖风险` 必须写真实缺口，不允许省略
