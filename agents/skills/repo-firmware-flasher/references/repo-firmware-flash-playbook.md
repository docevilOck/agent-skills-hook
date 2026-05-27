# 仓库固件刷写参考手册

## 目标

目标是先从仓库里查清刷写事实，再整理成配置文件，最后复用统一脚本执行；不要记忆某个设备的固定参数。

标准产出有两项：

- 项目内 `.agents/cache/<目标名>_download.cfg`
- 可执行命令：`probe`、`inspect-firmware`、`make-packets`、`flash`

## 先查什么

开始刷写前，至少确认以下信息：

1. 目标身份
- 当前项目目录
- 当前板级目录
- 构建目标名、机型宏、板卡宏

2. 固件产物
- 最终刷写文件名
- 是否存在打包、加密、补 CRC、合并镜像
- 原始 bin 和 OTA bin 哪个才是下载入口真正使用的文件
- 如果本轮验证依赖新代码，必须先等待编译完成，再确认当前构建产物路径；严禁编译和刷写并行执行

3. 连接方式
- `VID/PID`
- 传输类型：`usbprint`、`winusb`、串口、HID 或其他
- 设备路径特征、接口 GUID、`CreateFile` 路径模式

4. 升级协议
- 进入升级的命令
- 查询分包长度的命令
- 每包发送前是否需要额外命令头
- ACK 是设备主动上报，还是主机轮询读取

5. 包格式
- 包头长度
- `offset`、`length`、`crc` 的布局和字节序
- ACK 前缀、ACK 总长度、状态码位置
- 单包最大长度和实测稳定长度

## 去哪里查

优先查这些位置：

- 板级头文件、项目配置头文件
- `make`、`cmake`、批处理打包脚本
- 升级协议处理代码、命令分发表、boot/app 下载处理函数
- 历史 PC 下载工具、上位机脚本、升级助手源码
- 固件打包工具、镜像后处理工具

## 推荐搜索关键词

可以直接在仓库里搜这些关键词：

- `VID_`
- `PID_`
- `usbprint`
- `WinUsb`
- `CreateFile`
- `pack_length`
- `file_info`
- `ota`
- `update`
- `offset`
- `crc`
- `ack`
- `firmware`
- `encrypt`
- `pack`

## 配置文件格式

建议写成下面这种 INI：

```ini
[device]
transport = usbprint
vid = 1234
pid = abcd
path_hint =

[firmware]
firmware = out/target/firmware.bin
artifact_type = auto
allow_raw = false
header_size = 12
chunk_size = 8192
crc_type = crc32_init_ffffffff

[protocol]
command_prefix_hex = 1b1c2620563120
pack_length_command = getval "pack_length"\r\n
ota_command = do "ota"\r\n
query_pack_length = true
query_response_length = 4
ack_prefix_hex = 1b1c26
ack_length = 8
ack_offset_pos = 3
ack_status_pos = 7
ack_endian = little
delay = 0.05
query_retries = 2
query_settle_delay = 0.2
io_timeout_ms = 5000
```

## 字段解释

- `transport`：当前脚本主要支持 `usbprint`
- `vid`、`pid`：十六进制字符串，不带 `0x`
- `firmware`：默认固件路径，可在命令行覆盖
- `artifact_type`：`auto`、`packed`、`raw`
- `allow_raw`：是否允许跳过打包文件检查
- `header_size`：单包包头长度
- `chunk_size`：默认分包大小
- `crc_type`：当前脚本支持 `crc32_init_ffffffff`
- `command_prefix_hex`：命令公共前缀，十六进制字节串
- `pack_length_command`：查询单包长度的命令体
- `ota_command`：每包发送前的命令体
- `query_pack_length`：是否先查询设备返回的单包上限
- `query_response_length`：查询返回字节数
- `ack_prefix_hex`：ACK 前缀
- `ack_length`：ACK 固定长度
- `ack_offset_pos`：ACK 中 `offset` 的起始字节位置
- `ack_status_pos`：ACK 中状态字节位置
- `ack_endian`：当前支持 `little`

## 建议流程

1. 从仓库里定位刷写入口和协议代码。
2. 如果本轮依赖新代码或新产物，先执行构建并等待编译完成；构建未完成或失败时，不进入后续刷写步骤。
3. 把查到的参数写成 `.agents/cache/<目标名>_download.cfg`。
4. 如果后续要真实写入设备，且需要观察复位后的启动日志，先开串口抓取，不要等刷写后再补抓。
5. 先执行：

```powershell
python <repo_flash.py 路径> probe --config .agents/cache/<目标名>_download.cfg
```

6. 再执行：

```powershell
python <repo_flash.py 路径> inspect-firmware --config .agents/cache/<目标名>_download.cfg
```

7. 如需验证分包：

```powershell
python <repo_flash.py 路径> make-packets --config .agents/cache/<目标名>_download.cfg --out artifacts\packet_blob.bin
```

8. 只有在用户明确要求真实刷写时，才执行：

```powershell
python <repo_flash.py 路径> flash --config .agents/cache/<目标名>_download.cfg --yes
```

路径原则：

- 示例中的 `<repo_flash.py 路径>` 只是占位符，不要假设 skill 固定安装在某个用户目录或仓库目录。
- 若运行环境支持按 skill 名定位脚本，优先用运行时解析结果；否则显式传入脚本实际路径。

刷写顺序要求：

- 若设备刷写完成后会自动复位或立刻输出关键启动日志，必须先开串口抓取，再执行 `flash`。
- 不要在 `flash` 完成后才启动串口；否则可能漏掉判断是否成功启动所需的首段日志。
- 每次执行 `flash` 前一定要确保编译已经完成，且当前不存在正在进行的构建任务；严禁编译和刷写并行执行。
- 默认只对单个目标串行执行探测、检查、分包和刷写，不并发对多个设备或多个会话同时刷写。

## 判断是否可复用本脚本

满足以下条件时，可以直接复用：

- Windows 下通过 `CreateFile + ReadFile + WriteFile` 访问设备
- 每包是“命令 + OTA 包体”的串行写入方式
- ACK 是定长帧，能明确提取 `offset` 和 `status`
- 包头是固定结构，且 CRC 规则已知

不满足时，不要硬套。应保留“先查仓库、再写 cfg、再验证”的方法，但按目标协议另写脚本。
