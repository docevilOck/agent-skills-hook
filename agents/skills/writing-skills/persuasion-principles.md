# Skill 设计中的说服原则

## 概述

LLM 对说服原则的反应，和人类有不少相似之处。理解这些心理机制，可以帮助你把 skills 写得更有效。这里的目标是在压力下确保关键实践会被遵守，不能用于操控。

**研究基础：** Meincke 等人（2025）在 28,000 段 AI 对话上测试了 7 个说服原则。使用说服技巧后，遵从率从 33% 提升到 72%（p < .001）。

## 七个原则

### 1. Authority
**含义：** 对专家、资历或官方来源的服从。

**在 skills 里的作用：**
- 使用命令式语言，例如 `YOU MUST`、`Never`、`Always`
- 用不可协商的表述，例如 `No exceptions`
- 减少决策疲劳和自我合理化空间

**适用场景：**
- 强约束型 skills（TDD、验证要求）
- 安全关键实践
- 已经被广泛认可的最佳实践

**示例：**
```markdown
✅ 写测试之前先写代码？删掉，重来。没有例外。
❌ 如果方便的话，尽量先写测试。
```

### 2. Commitment
**含义：** 人们会倾向于保持和先前行为、声明、公开承诺一致。

**在 skills 里的作用：**
- 要求明确宣告：`Announce skill usage`
- 强制做出显式选择：`Choose A, B, or C`
- 用追踪机制：例如 `TodoWrite` 清单

**适用场景：**
- 确保 skill 真的被执行
- 多步骤流程
- 需要问责的场景

**示例：**
```markdown
✅ 找到 skill 后，必须声明：`I'm using [Skill Name]`
❌ 可以随口告诉对方你在用什么 skill。
```

### 3. Scarcity
**含义：** 来自时间限制或稀缺资源的紧迫感。

**在 skills 里的作用：**
- 加上时间约束：`Before proceeding`
- 强调顺序依赖：`Immediately after X`
- 阻止拖延

**适用场景：**
- 需要立即验证
- 对时间敏感的流程
- 防止“我晚点再做”

**示例：**
```markdown
✅ 完成任务后，立刻请求代码审查，再继续下一步。
❌ 方便的时候再审查代码。
```

### 4. Social Proof
**含义：** 人会顺从“大家都这么做”或“这是常态”。

**在 skills 里的作用：**
- 使用普遍规则：`Every time`、`Always`
- 明确失败模式：`X without Y = failure`
- 建立规范感

**适用场景：**
- 记录通用实践
- 提醒常见错误
- 强化标准

**示例：**
```markdown
✅ 不配合 TodoWrite 的清单，步骤一定会漏。每次都会。
❌ 有些人觉得 TodoWrite 对清单有帮助。
```

### 5. Unity
**含义：** 共享身份、同阵营感、共同目标。

**在 skills 里的作用：**
- 使用协作语言，例如 `our codebase`、`we're colleagues`
- 强调共同目标：`we both want quality`

**适用场景：**
- 协作型流程
- 团队文化
- 非层级化实践

**示例：**
```markdown
✅ 我们是一起协作的同事。我需要你诚实的技术判断。
❌ 你最好告诉我哪里错了。
```

### 6. Reciprocity
**含义：** 人会觉得有义务回报他人给予的好处。

**在 skills 里的作用：**
- 要谨慎使用，容易显得操控性过强
- 在 skills 中通常并不需要

**适用场景：**
- 几乎不用。其他原则通常更合适。

### 7. Liking
**含义：** 人更愿意配合自己喜欢的人。

**在 skills 里的作用：**
- **不要用** 来做合规控制
- 它会削弱诚实反馈
- 容易把模型推向迎合

**适用场景：**
- 强制纪律类 skill 中，始终避免使用

## 按 Skill 类型组合原则

| Skill 类型 | 推荐使用 | 避免使用 |
|------------|----------|----------|
| 纪律约束型 | Authority + Commitment + Social Proof | Liking、Reciprocity |
| 指导/技巧型 | 适度 Authority + Unity | 过强的 Authority |
| 协作型 | Unity + Commitment | Authority、Liking |
| 参考型 | 只追求清晰 | 所有说服技巧 |

## 为什么有效：心理学原理

**明确的硬规则会减少自我合理化：**
- `YOU MUST` 会减少决策疲劳
- 绝对化表达会消除“这算不算例外”的问题
- 明确的反合理化条目，可以堵住特定漏洞

**实施意图会形成自动化行为：**
- 清晰的触发条件 + 必要动作 = 更容易自动执行
- `When X, do Y` 通常比 `generally do Y` 更有效
- 能显著降低合规时的认知负担

**LLM 具有类人特征：**
- 训练数据里本就包含这些说服模式
- 权威语言往往更容易带来遵从
- 承诺链条（先声明，再行动）经常被学习到
- 社会证明模式会建立“这是常态”的预期

## 伦理使用

**正当用途：**
- 确保关键实践被执行
- 写出更有效的文档
- 防止可预见的失败

**不正当用途：**
- 为了个人利益操控对方
- 制造虚假紧迫感
- 用内疚感逼迫服从

**检验标准：** 如果对方完全理解这种技巧，它仍然会服务于对方的真实利益吗？

## 研究引用

**Cialdini, R. B. (2021).** *Influence: The Psychology of Persuasion (New and Expanded).* Harper Business.
- 7 个说服原则
- 影响力研究的经验基础

**Meincke, L., Shapiro, D., Duckworth, A. L., Mollick, E., Mollick, L., & Cialdini, R. (2025).** *Call Me A Jerk: Persuading AI to Comply with Objectionable Requests.* University of Pennsylvania.
- 在 28,000 段 LLM 对话中测试了 7 个原则
- 使用说服技巧后，遵从率从 33% 提升到 72%
- Authority、commitment、scarcity 最有效
- 验证了 LLM 的类人行为模型

## 快速参考

在设计 skill 时，先问这 5 个问题：

1. 它属于哪一类？（纪律约束、指导、还是参考）
2. 我要改变的具体行为是什么？
3. 哪些原则适用？（纪律类通常是 authority + commitment）
4. 我是不是用得太多了？（不要把 7 个全塞进去）
5. 这样做是否合乎伦理？（是否服务于用户的真实利益）
