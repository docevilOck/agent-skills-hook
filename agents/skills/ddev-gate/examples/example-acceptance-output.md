# 标准验收输出样例

下面是一份可直接仿照的最终验收输出样例。

## `need-info` 样例

```md
结论：`need-info`

对照范围：
- spec：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/dataflow/uart-rx-flow.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- implementation-notes：`docs/plans/26-05-18_uart_refactor/implementation-notes.md`
- 验证材料：`cmake --build build`、`ctest --output-on-failure`
- 本轮审查方式：一致性审查 + 代码评审并行

并行审查摘要：
- 一致性审查：`need-info`（发现 2 处架构偏离，1 处缺少最终代码验证证据）
- 代码评审：`pass`（HIGH 0 条；注释完整；未执行清理）

架构偏离处置表：

| # | 偏离点 | 文档依据 | 处置 | 位置 |
|---|--------|----------|------|------|
| 1 | 接收状态仍通过 `g_uart_rx_state` 维护 | spec 要求状态收敛到 `uart_session_t` | 未处理（可修正） | `src/uart/uart_session.c:88` |
| 2 | 命令分发仍为 6 段长链 `if/else if` | detail 约定 `switch (packet->cmd)` | 未处理（可修正） | `src/uart/uart_session.c:210` |

发现的问题：
1. High：接收状态未下沉到 `uart_session_t`，与 spec 的架构约束不一致。
2. Medium：命令分发未按 detail 约定改为 `switch`。
3. need-info：当前只有 host 单元测试结果，缺少目标板串口回环证据，无法支撑 `pass`。

已确认一致的关键点：
- `uart_session_t` 已建立，并承接了缓冲区、长度和重试计数。
- 对外接口仍保持在 `uart_session_init()` / `uart_session_feed()`，与 spec 一致。

需要主 agent 修改的项：
- 把 `g_uart_rx_state` 下沉到 `uart_session_t`
- 把长链 `if/else if` 改成 detail 约定的 `switch (packet->cmd)`
- 补充目标板串口回环验证证据后，基于最终代码重跑双审查

未覆盖风险：
- 异常包风暴场景下的状态迁移未验证。

下一步：
- 主 agent 先完成上述修改和证据补充，再重新进入 `ddev-gate`
```

## `pass` 样例

```md
结论：`pass`

对照范围：
- spec：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：`docs/plans/26-05-18_uart_refactor/detail/structures/uart-session-struct.md`、`detail/flows/uart-rx-flow.md`
- code：`src/uart/uart_session.c`、`src/uart/uart_session.h`
- implementation-notes：`docs/plans/26-05-18_uart_refactor/implementation-notes.md`
- 验证材料：本轮重新执行 `cmake --build build`、`ctest --output-on-failure`
- 本轮审查方式：一致性审查 + 代码评审并行；已基于清理后最终代码完成只读复审

并行审查摘要：
- 一致性审查：`pass`（无未处理架构偏离）
- 代码评审：`pass`（CRITICAL 0 / HIGH 0 / MEDIUM 1 / LOW 2；注释完整；已执行受限清理）

架构偏离处置表：

| # | 偏离点 | 文档依据 | 处置 | 位置 |
|---|--------|----------|------|------|
| — | 无 | — | — | — |

发现的问题：
- 无阻塞问题；1 条 MEDIUM（`uart_session_feed()` 错误分支可合并）已记录，不阻塞。

已确认一致的关键点：
- 接收状态、缓冲区和重试计数已全部收敛到 `uart_session_t`。
- 命令分发已按 detail 文档改为 `switch (packet->cmd)`。
- 对外接口与依赖方向与 spec 一致，未发现新增跨模块耦合。

清理与修复说明：
- 发生过代码修改：首轮代码评审清理了 1 处死代码、2 处重复分支，未改变行为、接口与架构。
- 清理后已重新运行 `cmake --build build`、`ctest --output-on-failure`，均通过。
- 已基于清理后最终代码并行重跑一致性审查与代码评审只读复审，双审查均 `pass` 且该轮无代码修改。

未覆盖风险：
- 尚未覆盖更大输入规模下的性能回归，但不影响本轮以架构一致性和代码质量为目标的有效结论。

下一步：
- 可进入正式收尾或后续提交流程，等待用户确认
```

## `blocked` 样例

```md
结论：`blocked`

对照范围：
- spec：`docs/plans/26-05-18_uart_refactor/spec/uart-session.md`
- detail：未定位到唯一有效文档
- code：`src/uart/uart_session.c`
- implementation-notes：`docs/plans/26-05-18_uart_refactor/implementation-notes.md`
- 验证材料：无
- 本轮审查方式：一致性审查 + 代码评审并行

并行审查摘要：
- 一致性审查：`blocked`（存在未修正且未记录的架构偏离）
- 代码评审：`blocked`（HIGH 1 条）

架构偏离处置表：

| # | 偏离点 | 文档依据 | 处置 | 位置 |
|---|--------|----------|------|------|
| 1 | 新增了 spec 未批准的 `uart_bus_shared_t` 全局共享状态 | spec 仅批准 `uart_session_t` 上下文 | 未修正、未记录 | `src/uart/uart_session.c:42` |

发现的问题：
1. High：实现新增了 spec 未批准的跨模块共享状态，且既未修正、也未写入 `implementation-notes.md` 的 Deviations。
2. High：当前目录下存在两个互相冲突的 detail 文档，无法确定架构基线。
3. High：代码评审发现接收缓冲区长度校验缺失，存在越界风险。

已确认一致的关键点：
- spec 文档已定位，`uart_session_init()` 接口位置正确。

需要主 agent 修改的项：
- 先唯一确定可用的 detail 文档基线
- 移除或按 spec 收敛 `uart_bus_shared_t`；若决定保留，必须写入 `implementation-notes.md` 的 Deviations（偏离点、理由、影响范围）
- 修复接收缓冲区长度校验缺失

未覆盖风险：
- 因详设基线不明确，本轮无法形成有效的一致性验收结论。

下一步：
- 主 agent 必须先完成上述修改/记录，再基于最终代码重新并行派发一致性审查与代码评审
```

## 使用要求

- 结论只能是 `pass`、`need-info`、`blocked`
- `对照范围` 必须点名具体文档和代码路径
- `并行审查摘要` 必须分别给出一致性和代码评审的结论；compact 路线合并为一份「整合审查结论」
- `架构偏离处置表` 必须出现；没有偏离写“无”；每项必须标注已修正 / 已记录 / 未处理
- `发现的问题` 优先写与文档架构不一致或代码评审阻塞的内容
- `已确认一致的关键点` 只列最重要的事实
- `清理与修复说明` 必须写清是否改过代码、改动范围、验证证据、是否完成只读复审
- `未覆盖风险` 必须写真实缺口，不允许省略
- 如果结论是 `blocked`，必须明确写出”主 agent 需要修改的项”，以便回炉后重审
