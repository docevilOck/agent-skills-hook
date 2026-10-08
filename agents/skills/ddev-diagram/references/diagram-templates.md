# 图形模板

## 架构图模板

```mermaid
flowchart LR
  Caller --> Module --> Storage
```

## 接入点图模板

```mermaid
flowchart LR
  E1["Entry 1"] --> Core
  E2["Entry 2"] --> Core
  Core["Core"]
```

## 流程图模板

```mermaid
flowchart TD
  A["Receive input"] --> B["Validate"]
  B --> C{"Valid?"}
  C -->|yes| D["Run"]
  C -->|no| E["Error"]
```

## 前后对照图模板

同一套节点名，两张图并排放在同一小节：

```mermaid
flowchart LR
  subgraph Before
    A1["Old Flow"] --> B1["Handler"]
  end
```

```mermaid
flowchart LR
  subgraph After
    A1["Old Flow"] --> B1["Handler"]
    A1 --> B2["New Hook"]
  end
```

## 状态图模板

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Running: start
  Running --> Idle: done
  Running --> Fault: error
  Fault --> Idle: reset
```

## 时序图模板

```mermaid
sequenceDiagram
  participant App
  participant Drv
  participant HW
  App->>Drv: open()
  Drv->>HW: init()
  HW-->>Drv: ack
  Drv-->>App: fd
```

## Unicode 框图模板（退回路径）

只在字节/位布局、目录树、或 Mermaid 表达失真时使用。框内标签用英文。

```text
┌──────────┬──────────┐
│  Byte 0  │  Byte 1  │
├──────────┼──────────┤
│   type   │  length  │
└──────────┴──────────┘
```

```text
detail/
├── overview.md
└── structures/
    └── job-context.md
```
