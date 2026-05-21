# Codex 工具映射

这份映射只面向执行阶段的 skills；规划、架构和写计划不在这里展开。

Skills 使用的是 Claude Code 的工具名。遇到这些工具名时，请使用你所在平台的等价工具：

| Skill references | Codex equivalent |
|-----------------|------------------|
| `Task` 工具（子代理派发） | `spawn_agent` (see [Named agent dispatch](#named-agent-dispatch)) |
| 多个 `Task` 并行派发 | Multiple `spawn_agent` calls |
| `Task` 返回结果 | `wait_agent` |
| `Task` 完成后释放槽位 | `close_agent` 释放槽位 |
| `TodoWrite`（任务追踪） | `update_plan` |
| `Skill` tool (invoke a skill) | Skills load natively — just follow the instructions |
| `Read`, `Write`, `Edit` (files) | Use your native file tools |
| `Bash` (run commands) | Use your native shell tools |

## 子代理派发需要多代理支持

把下面配置加到 `~/.codex/config.toml`：

```toml
[features]
multi_agent = true
```

这会启用 `spawn_agent`、`wait_agent` 和 `close_agent`，供需要子代理派发的 skills 使用，例如并行调查、并行审查这类工作流。

## 命名代理派发

Claude Code 的一些 skill 会引用命名 agent 类型，比如 `superpowers:code-reviewer`。
Codex 没有命名 agent 注册表，`spawn_agent` 会从内置角色（`default`、`explorer`、`worker`）创建通用 agent。

当 skill 需要派发命名 agent 时：

1. Find the agent's prompt file (e.g., `agents/code-reviewer.md` or the skill's
   local prompt template like `code-quality-reviewer-prompt.md`)
2. Read the prompt content
3. Fill any template placeholders (`{BASE_SHA}`, `{WHAT_WAS_IMPLEMENTED}`, etc.)
4. Spawn a `worker` agent with the filled content as the `message`

| Skill instruction | Codex equivalent |
|-------------------|------------------|
| `Task` 工具（superpowers:code-reviewer） | `spawn_agent(agent_type="worker", message=...)`，内容来自 `code-reviewer.md` |
| `Task` 工具（general-purpose，内联提示词） | `spawn_agent(message=...)`，使用同样的提示词 |

### 消息封装

The `message` parameter is user-level input, not a system prompt. Structure it
for maximum instruction adherence:

```
Your task is to perform the following. Follow the instructions below exactly.

<agent-instructions>
[filled prompt content from the agent's .md file]
</agent-instructions>

Execute this now. Output ONLY the structured response following the format
specified in the instructions above.
```

- Use task-delegation framing ("Your task is...") rather than persona framing ("You are...")
- Wrap instructions in XML tags — the model treats tagged blocks as authoritative
- End with an explicit execution directive to prevent summarization of the instructions

### 何时可以移除这个替代方案

This approach compensates for Codex's plugin system not yet supporting an `agents`
field in `plugin.json`. When `RawPluginManifest` gains an `agents` field, the
plugin can symlink to `agents/` (mirroring the existing `skills/` symlink) and
skills can dispatch named agent types directly.

## Environment Detection

Skills that create worktrees or finish branches should detect their
environment with read-only git commands before proceeding:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

- `GIT_DIR != GIT_COMMON` → already in a linked worktree (skip creation)
- `BRANCH` empty → detached HEAD (cannot branch/push/PR from sandbox)

See `using-git-worktrees` Step 0 and the repository's finalization flow
for how each workflow uses these signals.

## Codex App Finishing

When the sandbox blocks branch/push operations (detached HEAD in an
externally managed worktree), the agent commits all work and informs
the user to use the App's native controls:

- **"Create branch"** — names the branch, then commit/push/PR via App UI
- **"Hand off to local"** — transfers work to the user's local checkout

The agent can still run tests, stage files, and output suggested branch
names, commit messages, and PR descriptions for the user to copy.
