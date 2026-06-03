---
name: serial-log-debug
description: Use when debugging hardware over a Windows local serial port, especially when UART logs must be captured, text or hex commands sent manually, and TX/RX traces reviewed during bring-up, reproduction, or log-based fault isolation.
---

# serial-log-debug

## 工具入口

> **强制**：本 skill 提供以下精确定义的工具，必须直接调用，禁止自行实现替代品。

```
$SKILL_ROOT = <本 skill 加载输出中 "Base directory for this skill:" 行的路径>
```

| 工具 | 路径 | 用途 |
|---|---|---|
| serial_tool.py | `$SKILL_ROOT/serial_tool.py` | 串口独占打开、收发、抓取、状态管理 |

执行任何串口操作时，先提取 `$SKILL_ROOT`，再用 `python "$SKILL_ROOT/serial_tool.py" ...` 调用。

---

用于 Windows 下的本地串口联调。核心原则是：**先保留原始证据，再做轻量分析**。这个 skill 只覆盖 Windows 下的本地直连串口收发、日志落盘和基于日志的初步定位，不覆盖刷写、产测和远程串口场景。

默认前置原则：

- 任何可能导致设备复位、重启、重新枚举、进入新阶段或瞬时输出关键日志的动作之前，优先先打开串口并开始持续抓取。
- 典型场景包括：固件刷写前、USB 通信测试前、发送可能触发复位的控制命令前、人工重启或重新上电前。
- 不要在动作完成后才启动串口；否则即使设备实际成功启动，也可能因首段日志缺失而误判。

## When to Use

当出现以下情况时使用：

- 需要打开某个 `COMx` 串口观察设备启动或运行日志。
- 需要给设备手动发送文本命令、hex 字节串或简单测试输入。
- 需要同时保留原始字节流和可读日志，方便后续回放或复盘。
- 需要让 AI 基于 TX/RX 记录回答“最后停在哪一步”。
- 需要对超时、无响应、乱码、回显异常做第一轮日志归类。

不要在以下情况使用本 skill：

- 需要执行固件刷写、升级编排或镜像验证。
- 需要跑产测、量产工站或批量设备并发调试。
- 需要远程串口服务器、网络透传或多机集中调度。
- 需要自动解码完整业务协议、还原状态机或直接判定业务根因。

## Preconditions

使用前必须确认：

- 宿主机环境为 **Windows**。
- 设备通过 **本地直连串口** 接入。
- 目标串口必须能被当前工具 **独占打开**。
- 调试设备已上电，且具备输出日志或接收串口输入的条件。
- 串口驱动正常、日志输出目录可写。

TP807 HTTPS 联调已知约定：

- 串口参数使用 `115200 8N1`。
- **必须开启 `RTS/CTS` 硬件流控**；不要默认按“无流控”打开串口。
- 若 AI 工具未显式支持 `RTS/CTS`，应先补齐参数支持，再开始抓取。

如果任何一条不满足，先报告前置条件不成立，不要假装 skill 已具备对应能力。

## Quick Reference

## 工程位置

```text
<skill-root>/
```

## 快速使用

```bash
# 查看总帮助
python <serial_tool.py 路径> --help

# 检查串口是否可独占打开
python <serial_tool.py 路径> connect-test --port COM3 --baudrate 115200 --json

# 发送文本
python <serial_tool.py 路径> send-text --port COM3 --text reboot --line-ending crlf --json

# 发送 hex
python <serial_tool.py 路径> send-hex --port COM3 --hex "AA 55 01 02" --json

# 抓取 3 秒日志
python <serial_tool.py 路径> capture --port COM3 --duration 3 --output-dir serial_logs --json

# 打开后台串口会话，持续落盘
python <serial_tool.py 路径> open --port COM3 --output-dir serial_logs --json

# 打开后台串口会话，默认 5 分钟空闲自动关闭
python <serial_tool.py 路径> open --port COM3 --output-dir serial_logs --json

# 如需覆盖默认值，可显式指定空闲超时
python <serial_tool.py 路径> open --port COM3 --output-dir serial_logs --idle-timeout 600 --json

# 查看会话状态
python <serial_tool.py 路径> status --session-path serial_logs\\20260513_xxx\\session.json

# 查看最近日志
python <serial_tool.py 路径> peek --session-path serial_logs\\20260513_xxx\\session.json --lines 50

# 只读取新增日志，按游标推进
python <serial_tool.py 路径> read-new --session-path serial_logs\\20260513_xxx\\session.json --cursor-name ai

# 停止后台串口会话
python <serial_tool.py 路径> stop --session-path serial_logs\\20260513_xxx\\session.json

# TP807 HTTPS 联调：115200 8N1 + RTS/CTS
python <serial_tool.py 路径> open --port COM6 --baudrate 115200 --bytesize 8 --parity N --stopbits 1 --rtscts --output-dir serial_logs --json
```

说明：

- 示例中的 `<serial_tool.py 路径>` 是占位符，应该替换成当前运行环境解析到的实际脚本路径。
- 不要假设该 skill 固定安装在 `agents/skills/`、仓库根目录或某个用户目录下。

### 输入参数

优先使用以下参数口径：

- `--port`
- `--baudrate`
- `--timeout`
- `--parity`
- `--bytesize`
- `--stopbits`
- `--output-dir`
- `--json`

### 建议支持的动作

| 动作 | 目的 |
|---|---|
| `connect-test` | 验证目标串口是否能独占打开 |
| `send-text` | 发送文本命令，可选编码和行尾 |
| `send-hex` | 发送十六进制字节串 |
| `listen` | 持续监听串口输出 |
| `capture` | 按时长或字节数抓取一段日志 |
| `session` | 完成一次监听 → 发送 → 接收 → 落盘闭环 |
| `open` | 启动后台串口会话并持续落盘 |
| `status` | 查询后台串口会话状态 |
| `peek` | 读取最近日志片段，供 AI 判断是否继续 |
| `read-new` | 按游标读取新增日志，避免重复读历史内容 |
| `stop` | 停止后台串口会话 |

### 结果要求

每次执行都应尽量返回 machine-readable 结果，至少包含：

- `ok`
- `command`
- `port`
- `baudrate`
- `timeout`
- `log_path_raw`
- `log_path_text`
- `tx_bytes`
- `rx_bytes`
- `error_type`
- `error_message`

`error_type` 至少区分：`port_not_found`、`port_busy`、`invalid_param`、`read_timeout`、`write_failed`、`log_write_failed`。

## Operating Pattern

1. 先确认场景属于“Windows + 本地直连串口 + 独占访问”。
2. 明确串口参数，不自动猜测端口号、波特率或协议。
3. 任何会触发设备状态变化的外部动作之前，先建立连接或启动监听。
   - 包括但不限于：刷写、USB 测试、发送复位命令、人工重启或重新上电。
   - 目标是连续覆盖动作前、动作中、动作后的完整日志窗口，避免丢失首段证据。
   - 默认直接以目标波特率（例如 `115200`）打开串口；若现场存在异常，应按真实日志和错误类型继续排查，而不是在 skill 内隐式切换波特率重试。
   - 若仓库或现场已有明确串口约定，必须显式传入对应流控参数；对 TP807 HTTPS 联调，默认使用 `115200 8N1 + RTS/CTS`。
   - 若未显式提供 `--port`，可以先枚举本机可见串口，并优先尝试 USB 串口设备（例如 CH340）。
4. 推荐优先使用状态驱动模式：
   - `open`
   - `status`
   - `peek`
   - `read-new`
   - `stop`
5. 同时保留两类日志：
   - 原始日志：完整字节流
   - 可读日志：时间戳 + TX/RX + text/hex + 摘要
6. 分析时只基于实际日志片段做轻量归纳，不补全不存在的证据。

## Logging Rules

- 不因文本解码失败而丢弃原始字节。
- 不可打印字符优先转为 hex 展示。
- 摘要允许截断，但原始日志文件必须完整保留。
- 会话应有独立 ID、文件名和输出目录。
- 长时间监听应有显式停止方式，例如 `Ctrl+C`，必要时支持时长或字节上限。

## Analysis Boundaries

允许做的事：

- 标记 TX / RX。
- 总结最后一个可见状态。
- 抽取关键错误片段。
- 将异常初步归类为超时、无响应、乱码、参数错误、端口占用等。

不要做的事：

- 不把日志自动解释成完整业务协议语义。
- 不在证据不足时臆测设备内部状态。
- 不把串口观测结果直接升级成“根因已确定”。

## Common Mistakes

- 端口被其他串口助手占用却继续重试，导致误判设备无响应。
- 只保存文本日志，导致二进制数据丢失。
- 把乱码直接当协议异常，而不是先检查波特率或参数。
- 在没有证据时把“无回显”直接解释成死机。
- 把本 skill 与固件刷写 skill 混用，扩散了范围。

## Current Implementation

当前 skill 已包含 supporting CLI 和示例文件：

- `serial_tool.py`
- `examples/send_text.txt`
- `examples/sample_log.txt`
- `README.md`

这些名称表示当前 skill 目录内的实现文件；迁移到其他目录时，应按实际落点定位，不要写死父目录结构。

当前实现已经覆盖参数解析、统一 JSON 输出、错误分类、日志双文件落盘和最小子命令骨架。若宿主机未安装 `pyserial`，工具会返回结构化 `dependency_missing` 错误，而不是伪造串口执行结果。

当前实现还包含以下打开策略：

- 未传 `--port` 时，自动枚举当前可见串口，并优先选择 USB 串口设备。
- 实际打开串口时，直接按请求的目标波特率打开，并保留有限次重试。
- Windows 下 `PermissionError` / `access is denied` 会映射为 `port_busy`，避免误报成 `port_not_found`。
- `open` 会创建后台 worker 持续写入日志文件，并通过 `session.json` 暴露状态。
- `open` 默认启用 300 秒 idle 超时；若持续未收到新的 RX 数据，会自动关闭并写入关闭原因。
- AI 可在测试过程中的任意阶段反复执行 `status`、`peek`、`read-new`，不需要预先固定抓取窗口。
