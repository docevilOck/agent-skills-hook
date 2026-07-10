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

**多点拆分规则**：若用户在一条消息中给出多个独立纠正点（判断标准：纠正点之间无因果依赖、分别针对不同行为或规则），必须逐条拆分为独立的 corrected 信号——每个纠正点单独生成 signal_id、单独写一行 JSONL，禁止合并为一条。

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

2. **拆分多点纠正**：检查用户消息是否包含多个独立纠正点
   - 是 → 逐条拆分，对每个纠正点独立执行步骤 3-7
   - 否（单点纠正或 friction）→ 继续
   - 判断标准：纠正点之间无因果依赖、分别针对不同行为或规则

3. **生成 signal_id**：`{时间戳}_{skill名}_{短哈希}`
   - 时间戳：`YYYYMMDDTHHmmss`
   - 短哈希：sha256(用户最新输入) 的前 6 位

4. **计算 skill_version_hash**：当前 SKILL.md 内容的 sha256

5. **确保目录存在**：`<skill_root>/.skillopt/pending/`
   - skill_root = 包含该 skill 的 SKILL.md 的目录
   - 不存在则创建 `.skillopt/pending/`

6. **写信号**：追加一行 JSON 到 `<skill_root>/.skillopt/pending/signal.json`（**文件名必须是 `signal.json`，禁止使用 `signal.jsonl`**）
   - JSONL 格式（每行一个完整 JSON 对象，行尾无逗号）
   - 不覆盖已有信号

6.5 **校验信号可扫描**（所有信号写完后执行一次）：
   - 运行扫描脚本：`python <skills_root>/skill-optimizer/scripts/scan_signals.py --json`
   - 其中 `<skills_root>` 为 skill 目录的父目录（如 `~/.claude/skills`）
   - 解析 JSON 输出，检查目标 skill（如 `"skill": "skill-recorder"`）是否出现在 result 数组中
   - 若目标 skill 未出现 → **报错**："信号未被 scan_signals.py 识别，请检查文件名是否为 `signal.json`（非 `signal.jsonl`）"
   - 校验通过 → 继续步骤 7

7. **报告**：
   - friction：静默（不需要告诉用户，他们不需要知道）
   - corrected：简短确认 "已记录 code-review 的 corrected 信号"

## 禁止直接修改目标 skill 文件

**硬性门禁：skill-recorder 检测到任何 skill 存在问题时，严禁直接修改目标 skill 的任何文件（SKILL.md、配套文档、脚本等）。** 即使问题明确、解决方案清晰，也不得直接编辑或新增文件。

必须遵循以下流程：

1. **只记录信号**：将问题写成 `corrected` 或 `friction` 信号，写入目标 skill 的 `.skillopt/pending/` 目录。
2. **不自行改代码**：不在同一轮对话中直接编辑或新增目标 skill 的任何文件（含 SKILL.md、配套文档、脚本等）。
3. **提示走 skill-optimizer**：若用户要求立即修改，明确告知："此修改需要走 `skill-optimizer` 流程。信号已记录，可使用 `optimize <skill名>` 触发优化管线。"

## 约束

- 仅由全局指令 checklist 调用，不直接对用户开放
- **禁止修改目标 skill 的任何文件**（参见上方"禁止直接修改目标 skill 文件"章节）
- 不触发优化
- corrected：归属不明确时主动问用户
- friction：全自动，不打扰用户
