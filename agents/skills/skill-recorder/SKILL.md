---
name: skill-recorder
description: 在每轮 skill 使用过程中记录 corrected 和 friction 信号。由全局指令 checklist（AGENTS.md）调用。将结构化信号 JSON 写入目标 skill 的 .skillopt/pending/ 目录。当 agent 检测到用户纠正或自检到摩擦时使用。
---

# Skill Recorder — 信号记录

记录 `corrected` 和 `friction` 两种信号，供 skill-optimizer 后续优化使用。由全局指令中的每轮 checklist 触发（AGENTS.md / CLAUDE.md）。

## 触发

由每轮 checklist 调用：
- 每轮响应后，agent 自检是否有 corrected 或 friction 信号
- 有 → 调用本 skill 记录

## 信号类型

### `corrected`（用户纠正/指导）
用户给出了可执行的具体指导：
- "不对，用 X 而不是 Y"
- "你应该这样做：..."
- "问题出在 Z，试试 W"
- 任何给出了具体方向或指令的用户消息

记录前若 skill 归属不明确，需用户确认。

### `friction`（agent 自检摩擦）
agent 自检测到 skill 描述不完整导致额外消耗。满足**任一**即触发：
1. **重复操作**：同一类操作重复 >= 2 次才完成
2. **用户催了**：用户说"太慢了""怎么还在搞""还没好"，但任务最终完成（不是纠正，也不是拒绝）
3. **靠猜走通**：agent 判定某个步骤 skill 没写清楚，靠常识猜测或额外搜索才走通

门槛：单次 friction → 静默记录。>= 2 次同类型 friction → 优化时作为高优先级信号。

## 信号 JSON Schema

```json
{
  "signal_id": "{时间戳}_{skill名}_{短哈希}",
  "skill": "{skill 名称，小写，连字符分隔}",
  "type": "corrected | friction",
  "scenario": "{一句话任务场景}",
  "correction": "{用户的可执行指导，friction 时为 null}",
  "friction_detail": "{哪里不清楚、agent 如何兜底走通，corrected 时为 null}",
  "context": {
    "user_intent": "{用户最初想要什么}",
    "problem_turn": "{触发信号的 agent 响应/行为摘要}",
    "user_correction": "{用户纠正的原话，friction 时为 null}"
  },
  "skill_version_hash": "{记录时刻 SKILL.md 的 sha256}",
  "timestamp": "ISO 8601"
}
```

## 记录流程

1. **确定目标 skill**：回看最近 2-3 轮对话中加载了哪些 skill
   - 只有一个 skill 在范围 → 直接归属
   - 多个 skill → 弹出选择："刚才的问题属于哪个 skill？"

2. **生成 signal_id**：`{时间戳}_{skill名}_{短哈希}`
   - 时间戳：`YYYYMMDDTHHmmss`
   - 短哈希：sha256(用户最新输入) 的前 6 位

3. **计算 skill_version_hash**：当前 SKILL.md 内容的 sha256

4. **确保目录存在**：`<skill_root>/.skillopt/pending/`
   - skill_root = 包含该 skill 的 SKILL.md 的目录
   - 不存在则创建 `.skillopt/pending/`

5. **写信号**：追加一行 JSON 到 `<skill_root>/.skillopt/pending/signal.json`
   - JSONL 格式（每行一个完整 JSON 对象，行尾无逗号）
   - 不覆盖已有信号

6. **报告**：
   - friction：静默（不需要告诉用户，他们不需要知道）
   - corrected：简短确认 "已记录 code-review 的 corrected 信号"

## 约束

- 仅由全局指令 checklist 调用，不直接对用户开放
- 不修改 SKILL.md
- 不触发优化
- corrected：归属不明确时主动问用户
- friction：全自动，不打扰用户
