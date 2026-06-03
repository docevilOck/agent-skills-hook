---
name: kingstvis-socket
description: Use when running KingstVIS capture/export through SocketAPI with one explicit `capture` command and fully specified parameters.
---

# KingstVIS Socket Automation

## 工具入口

> **强制**：本 skill 提供以下精确定义的工具，必须直接调用，禁止自行实现替代品。

```
$SKILL_ROOT = <本 skill 加载输出中 "Base directory for this skill:" 行的路径>
```

| 工具 | 路径 | 用途 |
|---|---|---|
| kingstvis_socket_client.py | `$SKILL_ROOT/scripts/kingstvis_socket_client.py` | KingstVIS SocketAPI 统一客户端（capture/connect/状态查询） |

执行逻辑分析仪抓取时，先提取 `$SKILL_ROOT`，再用 `python "$SKILL_ROOT/scripts/kingstvis_socket_client.py" ...` 调用。

---

Use this skill when the user wants AI-assisted KingstVIS automation through the official SocketAPI.

## Prerequisites

- KingstVIS is running.
- KingstVIS Socket function is enabled in the application.
- Default endpoint is `127.0.0.1:23367`.
- Python 3 is available.

## Output Format Guidance

- Prefer `--format csv` for normal AI-assisted timing analysis.
- The exported CSV is the primary machine-readable artifact for this skill.
- CSV output is intended to be directly read by the agent and the user without reopening KingstVIS.
- Do not tell the user they must inspect the waveform in the KingstVIS GUI unless they explicitly want manual visual review.
- Before capture, estimate the likely total duration of the target event and reserve extra time margin as much as practical.
- Prefer slightly longer capture windows over clipped captures; the default bias should be to capture the full waveform, not to minimize file size.
- When multiple timing segments may appear before or after the target point, leave enough pre-trigger and post-trigger time so the whole interval is covered.
- If the repository maintains `.agents/cache/logic_timing_windows.csv`, treat it as the primary persisted source for timing-window planning.
- Prefer reusing the historical `recommended_next_window_sec` for the matching test entry before falling back to a fresh manual estimate.
- When reporting results, prefer quoting `capture_status.json`、导出的 `.csv`、以及基于 CSV 计算的耗时摘要。
- Treat KingstVIS mainly as the acquisition backend; the CSV is the review and analysis format.

## Required Rule

- Default to `capture`. Do not use `start`, `stop`, `export`, or raw `send` as the normal workflow.
- Every normal data-collection task should be expressed as one complete `capture` command with explicit parameters.
- If `.agents/cache/logic_timing_windows.csv` exists and the current task can be mapped to a known `test_method + test_file + test_case`, read that entry first and use it to size the initial capture window.
- `capture` is a foreground blocking command. It does not return until the full capture/export flow finishes or fails.
- If other operations must continue while capture is running, use the explicit background workflow: `capture-bg` plus `capture-status` or `capture-wait`.
- When using `capture-bg`, prefer passing an explicit `--path` for single-capture tasks so the status file records the exact exported file path deterministically.
- For long capture windows, `--timeout` must be comfortably larger than `--sample-time`; otherwise the background runner may time out on the `start` step before export begins.
- Only use `connect` for connectivity check.
- Only use `get-last-error` for dedicated diagnosis after a failed run.
- Do not split one capture task into multiple manual socket steps unless the user explicitly asks to debug SocketAPI details.

## Tool

Use the bundled client:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py --help
```

Default output directory:

```text
kingstvis_captures/
```

## Standard Workflow

First verify connectivity if needed:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py connect
```

Then run one complete capture command.

Minimal example:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --format csv --output-dir kingstvis_captures
```

Common explicit example:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --sample-rate 10000000 --sample-time 0.5 --threshold-voltage 1.65 --reset-trigger --pos-edge 0 --channels 0 1 --format csv --output-dir kingstvis_captures
```

Capture planning rule:

- If the repository provides `.agents/cache/logic_timing_windows.csv`, first look for a matching historical record and start from its `recommended_next_window_sec`.
- Before running `capture`, estimate the event duration and add margin for trigger latency, startup delay, tail latency, and possible retries.
- If the expected duration is uncertain, choose a longer `--sample-time` first, confirm the waveform is complete, then tighten the window later if needed.
- Do not optimize the first pass for compactness at the cost of missing the end of the waveform.
- After the capture is reviewed, the paired embedded-debug workflow should update the same file with `actual_window_sec`, completeness judgment, and `recommended_next_window_sec` for the next run.

Current capture sequence inside the script is:

`start` -> wait `--wait-after-start` -> `stop` -> optional wait `--wait-after-stop` -> `export`

The agent should still call only `capture`, not the internal steps directly.

Execution semantics:

- Foreground `capture` blocks until the whole sequence above completes.
- If the task requires more commands to run in parallel, use `capture-bg`.
- When using background execution, the agent must later call `capture-status` or `capture-wait` and confirm completion state before claiming success.

## Recommended Capture Patterns

Single capture:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --format csv --output-dir kingstvis_captures
```

Single capture with selected channels:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --channels 0 1 --format csv --output-dir kingstvis_captures
```

Single capture with sample and trigger settings:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --sample-rate 10000000 --sample-time 0.5 --threshold-voltage 1.65 --reset-trigger --pos-edge 0 --high-level 1 2 --low-level 3 4 --channels 0 1 --format csv --output-dir kingstvis_captures
```

Simulated capture when hardware is unavailable:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --simulate --count 1 --format csv --output-dir kingstvis_captures
```

Multiple captures:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 3 --interval 0.5 --format csv --output-dir kingstvis_captures
```

If CSV export is rejected by the installed KingstVIS version:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --format csv --fallback-kvdat --output-dir kingstvis_captures
```

If export timing is unstable after stop:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture --count 1 --wait-after-stop 0.5 --format csv --output-dir kingstvis_captures
```

Background capture when later steps must continue immediately:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture-bg --status-file kingstvis_captures\capture_status.json --count 1 --sample-rate 10000000 --sample-time 0.5 --channels 0 1 --format csv --path kingstvis_captures\capture.csv
```

说明：

- `capture-bg` 现在会透传完整 capture 参数给后台 runner。
- 当 `sample-time` 较长时，记得把全局 `--timeout` 一并调大，并确保明显大于 `sample-time`，例如 `--sample-time 30 --timeout 60`。
- 单次后台抓取推荐显式传 `--path`，这样 `capture_status.json` 会回填：
  - `output_path`
  - `output_exists`
- 如果只传 `--output-dir` + `--basename`，工具会在 `count=1` 时自动推导输出路径，但显式 `--path` 仍然是首选。
- 对正常时序分析，优先导出 `csv`，并直接基于 CSV 做后续 AI 分析，不要求再打开 KingstVIS 应用查看。

Check whether it is still running:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture-status --status-file kingstvis_captures\capture_status.json
```

Wait for completion before reporting success:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py capture-wait --status-file kingstvis_captures\capture_status.json --wait-timeout 60
```

## Diagnosis Only

Connectivity check:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py connect
```

Read last error after a failed capture:

```powershell
python agents\skills\kingstvis-socket\scripts\kingstvis_socket_client.py get-last-error
```

Do not use the commands below in normal agent workflow:

- `send`
- `start`
- `start --simulate`
- `stop`
- `export`
- direct parameter-setting commands such as `set-sample-rate`, `set-sample-time`, `set-trigger`

Those commands are implementation details or low-level diagnosis tools. Prefer putting all required parameters onto one `capture` command.

## Response Rules

- Treat any response beginning with `NAK` as failure.
- Report the exact `capture` command, response, output path, and whether the output file exists.
- If the output is CSV, treat it as directly analyzable evidence and prefer analyzing it in-place.
- If `capture` was started in the background, report that it is still running until completion evidence is collected.
- Do not claim export succeeded unless KingstVIS returned a non-`NAK` response or the output file actually appears.
- If the file does not appear after a successful response, report it as a residual risk because KingstVIS may write asynchronously or reject the extension silently.
- If `capture` fails and further diagnosis is needed, run `get-last-error` separately.

## Allowed Commands For Normal Use

- `connect`
- `capture`
- `capture-bg`
- `capture-status`
- `capture-wait`
- `get-last-error` only after failure diagnosis is needed
