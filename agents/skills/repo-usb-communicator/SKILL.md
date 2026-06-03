---
name: repo-usb-communicator
description: 当需要基于仓库代码定位 USB 设备参数，并通过脚本打开设备、发送数据或读取响应时使用。
---

# 仓库 USB 通信

## 工具入口

> **强制**：本 skill 提供以下精确定义的工具，必须直接调用，禁止自行实现替代品。

```
$SKILL_ROOT = <本 skill 加载输出中 "Base directory for this skill:" 行的路径>
```

| 工具 | 路径 | 用途 |
|---|---|---|
| repo_usb_comm.py | `$SKILL_ROOT/scripts/repo_usb_comm.py` | 设备探测、打开、发送、请求响应、交换数据 |
| repo-usb-communication-playbook.md | `$SKILL_ROOT/references/repo-usb-communication-playbook.md` | 设备识别定位方法和配置模板 |

执行 USB 通信时，先提取 `$SKILL_ROOT`，再用 `python "$SKILL_ROOT/scripts/repo_usb_comm.py" ...` 调用。

---

## 何时使用

- 需要先从仓库里查 `VID/PID`、设备路径线索、传输方式，再对设备发命令。
- 需要一个统一脚本完成设备探测、打开、发送和请求响应。
- 需要把设备识别参数沉淀到项目内 `.agents/cache/*.cfg`，供多个 skill 复用。

## 工作流

1. 先读 `references/repo-usb-communication-playbook.md`，按清单到仓库里找设备识别和通信事实。
2. 把查到的内容写入项目内 `.agents/cache/<目标名>_download.cfg`。
3. 复用该配置中的 `[device]`，必要时新增 `[usb_comm]` 段。
4. 如果本轮 USB 动作可能触发设备复位、重新枚举、状态切换，或需要结合启动日志判定，先用 `serial-log-debug` 先开串口抓取。
5. 使用 `scripts/repo_usb_comm.py` 执行：
   - `probe`：探测匹配设备
   - `open`：验证设备可打开
   - `send`：发送文本或十六进制数据
   - `request`：发送后读取固定长度响应
   - `exchange`：发送后持续读取直到空闲或超时
   - `read`：不发送，单独读取当前设备输出
6. 如果仓库里已有协议前缀或固定命令头，可复用同一配置中的 `command_prefix_hex`。

## 执行要求

- 不要在没查仓库前硬编码 `VID/PID`、路径、命令前缀或报文内容。
- 配置文件仍然写到项目内 `.agents/cache/`，建议与刷写 skill 共用同一份 cfg。
- 如果设备不是 `usbprint` 访问方式，不要强行套用当前脚本，应保留这套发现流程并另写脚本。
- 任何可能影响设备启动窗口或运行状态的 USB 测试前，都应先开串口抓取；不要等 USB 动作结束后再补抓。
- USB 指令默认严格串行：发送一条，等待响应、超时或结果判定完成，再发下一条。
- 真实收发时，把会话证据落到 `artifacts/`。

## 配置复用原则

- 直接复用 `[device]`：
  - `transport`
  - `vid`
  - `pid`
  - `path_hint`
- 可复用 `[protocol]`：
  - `command_prefix_hex`
- 新增 `[usb_comm]` 用于通信默认值：
  - `default_mode`
  - `default_payload_hex`
  - `default_text`
  - `text_encoding`
  - `append_crlf`
  - `read_length`
  - `read_timeout_ms`
  - `request_delay`

## 参考

- `references/repo-usb-communication-playbook.md`：仓库内定位方法、配置模板、收发建议。
- `scripts/repo_usb_comm.py`：统一 USB 通信脚本，优先读取 `.agents/cache/*.cfg`。
