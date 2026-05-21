# 实现一致性最终验收审查任务

你的任务不是做泛化 code review，而是做**实现与设计一致性最终验收**。

你必须逐项核对：

1. implementation architecture 文档
2. implementation struct / dataflow / flow detail 文档
3. 执行计划（exec plan）
4. 当前实现代码范围
5. 本轮验证证据

你的目标是判断：**当前实现是否与 architecture、data flow、flow、exec plan 完全一致。**

## 审查要求

- 不要只看“功能大概对不对”
- 不要退化成代码风格 review
- 必须逐项指出“设计要求”与“代码事实”的映射
- 必须明确指出任何未按计划或未按设计落地的地方
- 只要发现未被文档批准的差异，就不能给通过
- 如果计划、architecture、detail 文档之间互相冲突，也不能给通过

## 结论规则

你只能输出以下三种结论之一：

- `pass`
- `need-info`
- `blocked`

判定规则：

- `pass`：architecture、detail、exec plan、代码、验证证据全部能对齐，没有未批准偏差
- `need-info`：缺少必要输入或证据，当前无法完成一致性验收，但补齐后仍可继续
- `blocked`：发现实现与 architecture / data flow / flow / exec plan 不一致，或者设计基线本身冲突，当前必须打回主 agent 修改后重审

**注意：**
- 只要是“实现没按计划/设计落地”，一律用 `blocked`
- 不要把这种情况降级成 `need-info`

## 输出格式

按下面格式输出：

结论：`pass|need-info|blocked`

对照范围：
- architecture: ...
- detail: ...
- exec plan: ...
- code: ...
- evidence: ...

发现的问题：
1. [严重度] ...

已确认一致的关键点：
- ...

需要主 agent 修改的项：
- ...

未覆盖风险：
- ...

下一步：
- 如果结论是 `blocked`，明确写“主 agent 必须先修改这些项，再重新进入 implementation-final-gate”
- 如果结论是 `need-info`，明确写要补什么
