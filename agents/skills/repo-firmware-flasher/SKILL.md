---
name: repo-firmware-flasher
description: 当需要基于仓库代码推导刷写参数，并复用统一流程完成固件探测、分包或刷写时使用。
---

# 仓库固件刷写

## 何时使用

- 仓库里已经有升级链路，但 `VID/PID`、固件产物、OTA 指令、ACK 帧格式不能靠猜，必须先从代码里查。
- 需要把某个项目的刷写信息整理成可复用配置，并沉淀到项目内。
- 需要先做探测、固件检查、分包验证，再决定是否真实刷写。

## 工作流

1. 先读 `references/repo-firmware-flash-playbook.md`，按里面的清单去仓库里找升级相关事实。
2. 从仓库代码、构建脚本、旧下载工具中提取刷写参数，并写入项目内 `.agents/cache/<目标名>_download.cfg`。
3. 优先用 `scripts/repo_flash.py` 执行统一流程：
   - `probe`：探测设备路径
   - `inspect-firmware`：检查固件文件
   - `make-packets`：按配置生成分包数据
   - `flash`：真实下发
4. 真实刷写前，先完成以下最小闭环：
   - 配置文件已落盘
   - 本轮涉及新代码时，必须先等待编译完成，并确认本次刷写文件来自当前构建产物或仓库已指定产物
   - 已确认正确固件产物
   - 已确认 ACK 规则
   - 已完成一次探测或单包验证
5. 如果后续动作会真实写入设备、触发复位，或依赖启动日志判定，先用 `serial-log-debug` 先开串口抓取，再执行刷写。
6. 除非用户当前轮明确要求写入设备，否则默认只做到分析、配置生成和无写入验证。

## 执行要求

- 不要在没查仓库前硬编码任何 `VID/PID`、命令字、ACK、固件名。
- 配置文件必须写到项目内 `.agents/cache/`，文件名建议为 `<目标名>_download.cfg`。
- 如果仓库里存在多条升级路径，先判断当前目标实际使用哪一条，再选择是否复用本脚本。
- 如果协议明显不匹配，不要强行套用，应该保留这套工作流并按目标另写脚本。
- 每次执行刷写前一定要确保等待编译完成；严禁编译和刷写并行执行。
- 探测、固件检查、分包、刷写默认按单目标、单会话串行执行，不要自行扩展成并行多设备或交错下发流程。
- 真实刷写前先开串口抓取；不要等设备自动复位或输出过首段启动日志后才开始监听。
- 真实刷写时，把会话证据落到 `artifacts/`。

## 配置文件要求

配置文件建议使用 INI 格式，至少覆盖这些信息：

- 设备识别：`vid`、`pid`、`transport`
- 固件信息：`firmware`、`artifact_type`、`allow_raw`
- 分包参数：`chunk_size`
- 协议指令：`command_prefix_hex`、`pack_length_command`、`ota_command`
- ACK 规则：`ack_prefix_hex`、`ack_length`、`ack_offset_pos`、`ack_status_pos`
- 读包长规则：`query_pack_length`、`query_response_length`
- 校验规则：`crc_type`

## 参考

- `references/repo-firmware-flash-playbook.md`：仓库内信息定位方法、字段提取清单、配置文件模板。
- `scripts/repo_flash.py`：统一刷写脚本，从 `.agents/cache/*.cfg` 读取目标参数。
