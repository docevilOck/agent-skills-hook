# 缓存布局

本 skill 负责初始化项目内 `.agents/cache/` 下的最小缓存集合，供后续 embedded workflow、firmware flasher、KingstVIS skill 复用。

## 目录

```text
.agents/
  cache/
    <target-name>_download.cfg
    logic_timing_windows.csv
    kingstvis_channel_maps.json
```

## 1. 固件刷写配置

文件名：

```text
.agents/cache/<target-name>_download.cfg
```

格式：INI

最小字段：

- `[device]`
  - `target_name`
  - `vid`
  - `pid`
  - `transport`
  - `path_hint`
  - `boot_vid`
  - `boot_pid`
  - `boot_transport`
  - `boot_path_hint`
  - `app_vid`
  - `app_pid`
  - `app_transport`
  - `app_path_hint`
- `[firmware]`
  - `firmware`
  - `artifact_path`
  - `artifact_type`
  - `allow_raw`
  - `header_size`
  - `chunk_size`
  - `crc_type`
- `[protocol]`
  - `command_prefix_hex`
  - `pack_length_command`
  - `ota_command`
  - `ack_prefix_hex`
  - `ack_length`
  - `ack_offset_pos`
  - `ack_status_pos`
  - `query_pack_length`
  - `query_response_length`
  - `ack_endian`
  - `delay`
  - `query_retries`
  - `query_settle_delay`
  - `io_timeout_ms`
- `[usb_comm]`
  - `default_mode`
  - `default_payload_hex`
  - `default_text`
  - `text_encoding`
  - `append_crlf`
  - `read_length`
  - `read_timeout_ms`
  - `request_delay`
- `[serial]`
  - `port`
  - `baudrate`
  - `timeout`
  - `parity`
  - `bytesize`
  - `stopbits`
  - `rtscts`
  - `dsrdtr`
  - `xonxoff`

规则：

- 未知字段允许为空字符串。
- `target_name` 必须落盘，其他字段只在用户提供或仓库已确认时写入。
- 为兼容后续工具，`firmware` 与 `artifact_path` 应写入同一条事实值。
- 为兼容旧缓存，`chunk_size` / `crc_type` 可在 `[firmware]` 与 `[protocol]` 同时保留，但消费端应优先读 `[firmware]`。
- `[serial]` 用于沉淀串口监听默认参数，供 `embedded-debug-workflow` / `serial-log-debug` 复用。
- 初始化该文件前，必须先从仓库代码中搜索设备枚举与识别逻辑，至少确认 boot 和应用两套枚举信息。
- 如果仓库存在 bootloader / 升级态 与 应用态 两套 `VID/PID` 或路径线索，必须都写入缓存，不能只保留单一状态。
- 若当前工具仍主要消费单组 `vid/pid`，应额外保留 boot 与应用两套兼容字段，避免后续 skill 误把应用态设备当升级态设备。

## 2. 逻辑分析窗口经验表

文件名：

```text
.agents/cache/logic_timing_windows.csv
```

表头固定为：

```text
test_method,test_file,test_case,trigger_mode,io_mapping,expected_window_sec,actual_window_sec,captured_complete,too_short,too_long,recommended_next_window_sec,notes
```

初始化规则：

- 文件不存在时创建，只写表头。
- 只有用户给出测试方法、测试文件、测试用例、触发方式或建议窗口时，才追加首条记录。
- `io_mapping` 建议写 JSON 字符串，便于单列保存。

## 3. KingstVIS 通道映射

文件名：

```text
.agents/cache/kingstvis_channel_maps.json
```

建议结构：

```json
{
  "targets": {
    "demo-target": {
      "channels": {
        "0": "BOOT_MARK",
        "1": "USB_IRQ"
      },
      "pins": {
        "PA1": "BOOT_MARK",
        "PB3": "USB_IRQ"
      },
      "test_methods": [
        "usb_cmd",
        "power_on"
      ],
      "notes": "optional notes"
    }
  }
}
```

规则：

- `channels` 保存逻辑分析仪通道号到语义名的映射。
- `pins` 保存 MCU 引脚到语义名的映射；未知时可省略。
- `test_methods` 保存该映射适用的测试方式列表。

## 推荐调用

只初始化固件缓存：

```powershell
python agents\skills\embedded-workflow-cache-init\scripts\init_embedded_workflow_cache.py --project-root . --target app
```

同时初始化 KingstVIS 相关缓存：

```powershell
python agents\skills\embedded-workflow-cache-init\scripts\init_embedded_workflow_cache.py --project-root . --target app --test-method usb_cmd --test-case boot-time --trigger-mode usb --expected-window-sec 1.5 --channel-map "{\"0\":\"BOOT_MARK\",\"1\":\"USB_IRQ\"}" --pin-map "{\"PA1\":\"BOOT_MARK\",\"PB3\":\"USB_IRQ\"}"
```
