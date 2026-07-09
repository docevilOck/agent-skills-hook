---
name: ddev-hardware
description: 固件/嵌入式项目硬件资源分析与文档化。从 sdkconfig、peripheral_cfg.h、分区表等文件中提取 MCU 算力、存储、外设、GPIO 信息，输出结构化硬件规格文档。
---

# ddev-hardware — 硬件资源搜索与文档化

从固件仓库的配置文件中提取硬件资源信息，输出结构化的 Markdown 硬件规格文档。

## 触发条件

用户请求分析硬件资源、硬件规格、主板资源、外设清单、引脚定义，或要求"硬件文档""hardware spec""板级资源""GPIO 汇总"。

## 输入约定

执行前需确认两个信息（若用户未提供则主动扫描）：

1. **当前激活的机型** — 从机型配置头文件中提取（通常是 `prt_cfg.h`、`board_cfg.h`、`*_cfg.h` 中 `#define` 的宏）
2. **项目根目录** — 当前工作目录或用户指定的路径

## 执行流程

### 1. 定位当前机型

在项目根目录下搜索机型定义：

```
grep -rn "^#define TP\|^#define BOARD_\|^#define PRODUCT_" --include="*_cfg.h" --include="*board*.h" | head -30
```

**规则**：
- 以非注释的 `#define <NAME>` 行为准
- 优先识别含 `GEN`、`DEV`、`V2`、`MT` 等版本/变体后缀的宏
- 若用户指定了目标机型，直接使用，不做自动检测

### 2. 提取计算与存储资源

从 ESP-IDF 的 `sdkconfig` 或等效内核配置文件中提取：

```bash
# CPU 核数与频率
grep -E "UNICORE|DEFAULT_CPU_FREQ|NUMBER_OF_CORES" sdkconfig

# 缓存配置
grep -E "INSTRUCTION_CACHE_SIZE|DATA_CACHE_SIZE|CACHE" sdkconfig

# Flash 配置
grep -E "FLASHSIZE|FLASHMODE|FLASHFREQ|FLASH_SIZE" sdkconfig

# PSRAM / 外部 RAM
grep -E "SPIRAM|PSRAM|EXTERNAL_RAM" sdkconfig
```

**必须回答的关键问题**：
- MCU 型号是什么？（从 `IDF_TARGET` 或 CMakeLists 推导）
- CPU 架构/内核？（ESP32→LX6, ESP32-S3→LX7, ESP32-C3/C6→RISC-V，类推）
- 几核？主频多少？
- 片内 SRAM 多大？有无片上 ROM？
- I-Cache / D-Cache 各多大？
- **固件存哪里**？（片内 Flash 还是片外 SPI Flash？容量多少？）
- 有无 PSRAM？容量多大？

> 嵌入式 MCU 的片内 ROM/SRAM 值可从芯片 datasheet 常量获取，不需要从配置文件推导。

### 3. 提取 Flash 分区布局

搜索项目中的分区表文件：

```bash
find . -name "partitions*.csv" -o -name "partitions*.h" | head -10
```

根据当前机型选择对应的分区表文件，解析 CSV 格式的分区表：
- 跳过 `#` 注释行
- 提取 Name、Offset、Size 列
- 标注每个分区的用途（根据 Name 推断：factory→出厂固件，ota→OTA 升级区，parameter/nvs→参数存储，font→字库，wave→音频）

**必须注明**：固件写入的起始偏移、最大可用空间。

### 4. 提取外设硬件

在项目中搜索外设配置文件（常见文件名：`prt_peripheral_cfg.h`、`peripheral_cfg.h`、`board_pin.h`、`pin_mux.h`）：

```bash
find . -name "*peripheral*" -o -name "*pin_mux*" -o -name "*board_pin*" | head -10
```

从该文件中逐段扫描，每个 `// =====` 或明显的注释分隔块对应一类外设。提取以下信息：

**通信接口**：
- UART：编号、TX/RX/RTS/CTS 引脚、用途（连接什么模块）
- SPI：总线号、MOSI/MISO/SCK/CS 引脚、频率、连接的设备
- I2C：SCL/SDA 引脚、频率、连接的设备
- I2S：MCLK/BCK/WS/DATA 引脚、采样率、连接的 Codec
- USB：DP/DM/VBUS 引脚、用途
- WiFi：芯片型号、接口类型（SDIO/SPI/UART）、复位引脚
- 蓝牙：是否使能
- 4G/LTE：模块型号、UART 绑定、电源/复位引脚
- 以太网：是否使能、复位引脚

**执行机构**（若为打印机/电机控制类设备）：
- 打印头/显示：数据总线绑定、锁存/使能引脚
- 电机：驱动芯片型号、各相/步进引脚、使能/休眠引脚、数量
- 切刀/机械：传感器引脚、步数配置

**传感器与检测**：
- ADC 通道：各通道用途（温度/电压/位置检测）、对应的 GPIO
- GPIO 传感器：纸张检测、位置检测、盖板检测等

**音频**：
- DAC/Codec 型号、接口类型
- 扬声器控制引脚、PWM 通道

**人机交互**：
- LED：颜色数量、各 GPIO
- 物理按键：功能、GPIO
- 触摸按键：GPIO

**电源与系统**：
- 外设供电控制 GPIO
- 系统电源使能 GPIO
- 复位引脚

### 5. 整理 GPIO 汇总表

将所有 GPIO 整理成统一表格：GPIO 号、功能、方向（I/O）、备注（复用/特殊说明）。

过滤规则：
- `PRT_GPIO_UNVALID`、`-1`、`0xFF` 等无效值不列出
- 同一个 GPIO 被多个功能复用时要明确标注

### 6. 提取机型差异（可选）

若 `prt_cfg.h` 中存在多个 `#if defined(MODEL_A) ... #elif defined(MODEL_B)` 分支，提取当前机型所在分支的 `#define` 列表，并与相邻机型分支对比，总结功能差异。

### 7. 输出文档

写入 `docs/spec/<MODEL>-hardware-spec.md`，按以下结构：

```
# <MODEL> 硬件资源规格
> 整理自: <源文件列表>
> 日期: <当前日期>

## 一、主控与计算资源
- MCU 型号、内核架构和说明、核数、主频
- I-Cache / D-Cache 大小
- 片内 SRAM / ROM 大小

## 二、存储资源
- 片内存储（SRAM、ROM、RTC 内存）
- 片外 Flash（容量、接口类型、频率、用途）
- 片外 PSRAM（容量、接口类型、频率、用途）
- 明确指出固件烧录到哪个物理介质

## 三、Flash 分区布局
- 主分区表（名称、偏移、大小、用途）
- 子分区（如有）

## 四、通信接口
## 五、打印/执行子系统（根据实际硬件调整标题）
## 六、音频子系统
## 七、人机交互
## 八、电源与系统
## 九、系统参数（任务栈、RTOS 配置等）
## 十、GPIO 汇总
## 十一、机型差异对比（如有多个变体）
```

## 注意事项

- 不要假设项目目录名或文件名；所有路径通过 `find` / `grep` 搜索得到
- 芯片 datasheet 中的常数值（片内 SRAM/ROM 大小）直接写入文档，无需验证
- 分区表解析时跳过 `#` 注释行，正确处理 hex 偏移值
- 对于 `PRT_GPIO_UNVALID` / `-1` 等占位符，视为"未使用"，不写入汇总
- PSRAM 若配置为自动检测，标注"自动检测"而非猜测具体数值
- 文档中使用物理量单位（KB/MB/MHz）而非 hex 原始值，两者可同时出现
- 若用户指定了机型而当前代码激活的是另一个机型，需要提醒用户
