# 数据流文档模板

```markdown
# [模块名] 数据流规划

> 如果本主题较大，overview 必须写到 `detail/<name>-overview.md`；本目录只放 `*-details.md` / `*-errors.md` / `*-states.md` 等数据流细节文档。

## 1. 范围
[这份数据流覆盖什么范围]

## 2. 输入与输出
- 输入来源：
- 输出去向：
- 触发条件：

## 3. 主链路
1. [入口]
2. [转换点]
3. [状态迁移]
4. [输出]

## 4. 边界和接入点
- 入口：
- 出口：
- 转换点：
- 外部依赖：

## 5. 结构体与状态依赖
- 相关结构体：
- 相关状态枚举：
- 谁持有长期状态：

## 6. 错误路径与回退
- 非法输入如何处理：
- 中途失败如何退出：
- 需要回滚或复位哪些状态：

## 7. 分发策略
- 使用守卫式返回 / `switch` / 状态机 / 表驱动：
- 为什么：

## 8. 图
[使用 `diagram-workflow` 生成的 ASCII 图]
```

## 拆分版建议

复杂数据流建议至少拆成：

- `detail/xxx-overview.md`：总览、边界、文档分布图、简图、子文档索引
- `detail/dataflow/xxx-details.md`：逐步骤细节
- `detail/dataflow/xxx-errors.md`：错误路径和回退
- `detail/dataflow/xxx-states.md`：状态迁移与持有者
