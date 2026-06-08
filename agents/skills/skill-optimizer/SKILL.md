---
name: skill-optimizer
description: 基于记录的 corrected/friction 信号优化 skill。8 步管线：Confirm→Load→Triage→Deep Read→Reflect→Dry-run→Gate→Update。仅当用户明确说"optimize XX skill"或"skill-optimizer"时使用。必须手动触发，禁止自动调用。
---

# Skill Optimizer — Skill 优化器

用记录的信号优化 skill。将 SkillOpt 的训练纪律（Reflect → Gate → Update）搬到日常使用中 — 不需要 benchmark 数据，只需要你的真实反馈。

## 触发（仅手动）

用户必须明确说出：
- "优化 <skill 名>"
- "/optimize <skill 名>"
- "skill-optimizer"（展示信号面板，不指定目标 skill）

**本 skill 不可被自动调用、不可后台运行、不可被其他 skill 代理触发。**

## 核心约束

- 仅手动触发
- 不自动运行、不后台运行
- 不可被其他 skill 代理调用
- 只有 skill-optimizer 写文件；子代理和 gate.py 不写文件
- 信号上限：最近 30 天 + top 20 条（corrected 优先于 friction）
- Git 仓库必须干净才能开始优化
- 仅 `corrected` 和 `friction` 两种信号参与优化

## 子代理模板

以下模板由 skill-init 部署。此处为权威定义。

### optimizer-agent（分析代理）

```
description: Skill optimization agent. Analyzes signal clusters, produces triage output and edit suggestions.
tools: [Read, Grep, Glob]
model: inherit
```

### gate-agent（门禁代理）

```
description: Skill gate judge agent. Evaluates whether skill edits resolve historical signal clusters (parallel per cluster).
tools: [Read]
model: inherit
```

---

## 8 步管线

指定目标 skill 后按以下顺序执行。

---

### Step 1: CONFIRM TARGET（确认目标）

**输入：** 用户话语中包含的目标 skill 名称。

**动作：**
1. 从用户输入中提取目标 skill 名称。
2. 定位 skill：搜索 `<skills_dir>/<名称>/SKILL.md`。不存在 → 中止："未找到 skill `<名称>`"。
3. GIT CLEAN 检查：`git status -- <skill_root>`（在 skill 所在仓库执行）。不干净 → 中止："`<skill>` 有未提交的改动，请先 commit 或 stash。"
4. RESUME（续跑检查）：如果存在 `<skill_root>/.skillopt/work/optimization_ts.json` → 从 `last_completed_step + 1` 继续。
5. 写 checkpoint。

---

### Step 2: LOAD SIGNALS（加载信号）

**输入：** 已确认目标 skill。

**动作：**
1. 读 `<skill_root>/.skillopt/pending/signal.json`。
2. 过滤：仅取最近 30 天。
3. 截断：top 20（corrected 优先于 friction）。
4. 超出部分标记数量。
5. 为空 → 中止："`<skill>` 暂无待处理信号"。
6. 按类型分组：corrected / friction。

**成本估计：**
- 预估 cluster 数量（粗略：每 3-4 条 friction 或 1-2 条 corrected 为一个 cluster）。
- 总 LLM 调用 ≈ cluster 数 × 1（gate-agent，全并行）+ 2（optimizer-agent：triage + reflect）。
- 展示给用户："预计 ~N 次 LLM 调用。是否继续？(y/n)"

7. 写 checkpoint。

---

### Step 3: TRIAGE（分诊，派 optimizer-agent）

**输入：** Step 2 的全部信号（仅摘要：scenario + correction + friction_detail）。

**派 optimizer-agent 子代理：**

用 optimizer-agent 子代理分析。提供全部信号摘要，指令如下：

```
分析以下 <skill> 的优化信号：

信号列表：
[
  {"signal_id": "...", "type": "corrected|friction", "scenario": "...",
   "correction": "... 或 null", "friction_detail": "... 或 null"}
]

任务：
a) DEDUP（去重）：按语义匹配将同根因信号聚类。每个信号输出 cluster_id。
b) STALE CHECK（过期检测）：比对每条信号的 skill_version_hash 与当前
   SKILL.md 哈希。不匹配的标记为 stale。
c) CONFLICT FLAG（冲突标记）：如 cluster 内信号相互矛盾，
   输出 conflicting_pair + 矛盾原因。
d) PRIORITY RANK（优先级排序）：按深度分析价值排序。

输出 JSON：
{
  "clusters": [
    {"cluster_id": "c_001", "root_cause": "...", "signal_ids": [...],
     "type": "corrected|friction", "count": N}
  ],
  "conflicts": [
    {"signal_a": "sig_id", "signal_b": "sig_id", "reason": "..."}
  ],
  "stale_signals": ["sig_id", ...],
  "priority_order": ["sig_id", ...]
}
```

**如有冲突：** 向用户展示矛盾的信号对和原因。询问："这些信号互相矛盾，应该按哪个方向优化？"等待用户确认后再继续。

8. 写 checkpoint。

---

### Step 4: DEEP READ（深读上下文）

**输入：** Triage 产出的 priority_order。

**动作：**
对 priority_order 中的每条信号，读取其完整 context：
- `context.user_intent`（用户最初意图）
- `context.problem_turn`（出问题的 agent 行为）
- `context.user_correction`（corrected）或 `friction_detail`（friction）

无需额外 API 调用——上下文已在信号文件中内嵌。

9. 写 checkpoint。

---

### Step 5: REFLECT（反思，派 optimizer-agent）

**输入：** 当前 SKILL.md 全文 + priority_signals（含 deep-read context）+ clusters。

**长 SKILL.md 处理：** 如果 SKILL.md 超过 ~3000 token：
- optimizer-agent 先扫描标题结构（# / ## / ###）
- 将信号 scenario 匹配到相关章节
- 只将匹配到的章节作为完整 context 提供
- 无关章节替换为 `<omit reason="与本次信号无关"/>`

**派 optimizer-agent 子代理：**

```
当前 skill 内容：
{完整 skill 或章节筛选后的内容}

信号（含完整上下文）：
[
  {"signal_id": "...", "type": "...", "scenario": "...",
   "correction": "...", "friction_detail": "...",
   "context": {"user_intent": "...", "problem_turn": "...",
               "user_correction": "..."}}
]

Clusters（聚类结果）：
{clusters_json}

分析失败/摩擦模式。诊断 skill 中的根因问题。

输出 MODE 1 — 文本编辑（默认，适合定向修改）：
{
  "diagnosis": "一段根因总结",
  "edits": [
    {"type": "delete|replace|add",
     "target": "SKILL.md 中要匹配的精确原文",
     "new": "替换文本（delete 时为空）",
     "reason": "修改理由",
     "source_cluster_id": "c_001"}
  ]
}

输出 MODE 2 — 全量重写（仅在结构需要重排时使用）：
{
  "diagnosis": "一段根因总结",
  "rewrite_mode": true,
  "rewrite_content": "完整重写后的 SKILL.md 内容",
  "reason": "为什么选择重写而非文本编辑"
}

除非信号表明 skill 结构本身有问题，否则默认用 MODE 1。
```

10. 写 checkpoint。

---

### Step 6: DRY-RUN（演习验证，skill-optimizer 本地执行）

**输入：** Step 5 产出的 edits[] 或 rewrite_content。

**动作：**

**MODE 1 — 文本编辑验证：**
- 对 edits[] 中每条 edit：
  - 在当前 SKILL.md 中精确匹配 `target` 原文。
  - 找不到 → 丢弃该 edit，记录原因。
  - 找到多处 → 丢弃该 edit，记录原因。
- 存活 edits → gated_edits[]。

**MODE 2 — 重写验证：**
- 检查 rewrite_content 是否为可解析的 markdown（有 frontmatter、有章节结构）。
- 无需文本匹配。

**如果 gated_edits[] 为空且无 rewrite_content：**
- 报告："未产生可落地 edits。triage 诊断：{diagnosis}"。
- 询问用户："放弃本轮还是手动指导下一步？"

11. 写 checkpoint。

---

### Step 7: GATE（门禁，gate.py 生成 prompt → 并行派 gate-agent）

**输入：** gated_edits[]（或 rewrite_content）+ clusters。

**ONLY-CORRECTED 特例：** 如果全部信号都是 friction（无任何 corrected）→ 跳过 gate，直接 ACCEPT。

**动作：**

1. 生成候选 skill：
   - MODE 1：在内存中将 gated_edits 应用到当前 SKILL.md → candidate_skill
   - MODE 2：candidate_skill = rewrite_content

2. 调用 `gate.py` 脚本：
   ```bash
   python <skill_optimizer_dir>/scripts/gate.py
   ```
   使用 `build_gate_prompt(candidate_skill, clusters, mode)` 函数。
   - mode = "text_edit"（MODE 1）
   - mode = "rewrite"（MODE 2）

3. **并行派发：** 每个 cluster 发一次 gate-agent 调用。全部 cluster 并行执行。

   MODE 1 问："如果 agent 用的是新版 skill，这个信号还会出现吗？回答 YES 或 NO。"
   MODE 2 问："改写后的 skill 是否解决了这个根因？回答 COVERED 或 NOT_COVERED。"

4. 收集每个 cluster 的判决。

5. **门禁规则：**
   ```
   total = cluster 总数
   passed = MODE 1 的 NO 数 + MODE 2 的 COVERED 数
   passed / total >= 0.5 → ACCEPT
   ```

6. **ACCEPT** → 进入 Step 8。
   **REJECT** → 向用户展示每个 cluster 的判决结果，中止。

12. 写 checkpoint。

---

### Step 8: UPDATE（更新，skill-optimizer 写文件，两次 commit）

**Commit 1 — 审计归档（回退时不 revert）：**

- 将 pending 信号从 `<skill_root>/.skillopt/pending/signal.json` 迁移到 `<skill_root>/.skillopt/resolved/YY-MM-DD_描述/signal.json`
- 写入 `<skill_root>/.skillopt/resolved/YY-MM-DD_描述/optimization.json`：

  ```json
  {
    "optimization_id": "...",
    "skill": "<skill 名>",
    "timestamp": "ISO 8601",
    "mode": "text_edit | rewrite",
    "edits": [...],
    "gate_result": {...},
    "pre_optimization_hash": "旧 SKILL.md 的 sha256",
    "post_optimization_hash": "新 SKILL.md 的 sha256",
    "signal_ids": ["sig_1", "sig_2"],
    "pre_skill_backup": "优化前 SKILL.md 的完整内容"
  }
  ```

- `git commit -m "audit(skill): 归档 <skill> 的优化信号"`

**Commit 2 — Skill 变更（回退目标）：**

- MODE 1：将 gated_edits 应用到 `<skill_root>/SKILL.md`
- MODE 2：将 `<skill_root>/SKILL.md` 替换为 rewrite_content
- `git commit -m "optimize(skill): <变更摘要>"`

**清理：**
- 删除 `<skill_root>/.skillopt/work/` 目录

**输出给用户：**

```
=== skill-optimizer: <skill> ===

📊 信号: X 条 corrected, Y 条 friction (Z 个 cluster)
🔧 模式: text edit / full rewrite

变更:
  - DELETE "<原文片段>" (<理由>)
  - REPLACE "<旧>" → "<新>" (<理由>)

🚪 Gate: N/M cluster 通过
  c_001: NO — <判定理由>
  c_002: NO — <判定理由>

📦 提交:
  abc1234 audit(skill): 归档 <skill> 的优化信号
  def5678 optimize(skill): <变更摘要>
```

---

## 信号面板模式（不指定目标 skill）

用户说 "skill-optimizer" 但不指定 skill 时：

1. 扫描 `<skills_dir>/` 下所有 skill 目录的 `.skillopt/pending/signal.json`
2. 读每个文件，统计信号类型数量
3. 输出表格：

```
| skill          | corrected | friction | 最近信号    |
| -------------- | --------- | -------- | ----------- |
| code-review    | 3         | 2        | 2 天前      |
| diagram-work   | 0         | 1        | 5 天前      |
| repo-fw-flash  | [deleted] | -        | -           |
```

- friction >= 2 的行高亮
- 有信号但 SKILL.md 已删除的 skill 显示 `[deleted]`
- 用户从列表中选择一个来优化

---

## 演习模式（--dry-run）

用户指定 `--dry-run` 或 "dry run"：

```
用户: "skill-optimizer --dry-run code-review"
```

8 步全部正常执行，但 Step 8 只输出 diff 和将要生成的提交信息，不实际修改 SKILL.md，不执行 git commit。

配合 `examples/sample_signals.json` + `examples/sample_skill.md` 可以验证管线正确性。

---

## 自优化

当用户明确要对 skill-optimizer 自身做优化时允许。8 步管线作用于 skill-optimizer 自己的 SKILL.md，使用其自己的 `.skillopt/pending/` 信号。

---

## 回退

回退某次 skill 优化：

```
用户: "rollback <skill>" 或 "revert <skill> optimization"
```

Agent：`git log --oneline -- <skill_root>/SKILL.md`
→ 找到 `optimize(skill):` 那次 commit
→ `git revert <commit_hash>`（只 revert commit 2，审计 commit 1 不动）

---

## 信号 JSON Schema（与 skill-recorder 共享）

```json
{
  "signal_id": "{时间戳}_{skill名}_{短哈希}",
  "skill": "{skill 名}",
  "type": "corrected | friction",
  "scenario": "{一句话任务场景}",
  "correction": "{用户的可执行指导}",
  "friction_detail": "{哪里不清楚、如何兜底的}",
  "context": {
    "user_intent": "{用户最初想要什么}",
    "problem_turn": "{agent 响应摘要}",
    "user_correction": "{用户纠正原话}"
  },
  "skill_version_hash": "{记录时 SKILL.md 的 sha256}",
  "timestamp": "ISO 8601"
}
```

---

## 文件结构

```
<skill_root>/
|-- SKILL.md                          ← 优化目标
|-- .skillopt/
    |-- pending/
    |   |-- signal.json               ← 待处理信号（JSONL）
    |-- resolved/
    |   |-- YY-MM-DD_描述/
    |       |-- signal.json           ← 已归档信号
    |       |-- optimization.json     ← edits + gate + diff + 备份
    |-- work/
        |-- optimization_ts.json     ← 续跑 checkpoint
```
