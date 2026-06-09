---
name: codegraph-tool-routing
description: CodeGraph tool selection routing rules. Enforces the decision tree for choosing codegraph_* vs grep/Read/Shell tools. Use for structural queries — symbol lookup, call tracing, architecture understanding, impact analysis. Blocks grep/Read from being used for symbol/architecture queries.
---

# codegraph-tool-routing

## 触发条件

任何涉及以下场景的任务，必须自动匹配加载：
- 查找函数/变量/宏/类型的定义或声明
- 理解模块、功能、架构的工作方式
- 追踪调用链（谁调了谁、谁被谁调）
- 评估代码改动的影响范围
- 查看多个相关符号的源代码
- 探索项目文件结构

## 核心原则

**CodeGraph 工具用于结构查询。通用命令仅限基础设施操作。**

## 统一工具映射表

| 场景 | 工具 |
|---|---|
| 找符号定义 | `codegraph_search` |
| 理解功能/架构 | `codegraph_context` |
| 追踪调用链 | `codegraph_trace` |
| 查看调用者/被调用 | `codegraph_callers` / `codegraph_callees` |
| 评估改动影响 | `codegraph_impact` |
| 查看多个符号源码 | `codegraph_explore` |
| 列出项目文件 | `codegraph_files` |
| 字面量/文本搜索 | grep |

## 执行决策树

```
任务
├─ 结构查询（符号/调用/架构）？
│   ├─ 先 codegraph_status → 未初始化则询问用户
│   ├─ 已初始化 → 按上表选 codegraph_* 工具
│   └─ 禁止直接用 grep/Read 找定义
│
├─ 字面量/文本搜索？
│   └─ grep
│
└─ 基础设施 shell（git/mkdir/rm/mv/npm/pip）？
    └─ 直接执行
```

## 阻断规则

以下行为被明确禁止：
- **grep 搜符号** → 禁止。用 `codegraph_search`
- **Read 理解架构** → 禁止。用 `codegraph_context`
- **假设索引已存在** → 禁止。每次先 `codegraph_status`
- **grep 验证 CodeGraph 结果** → 禁止。信任 AST 解析

## 子代理分发约束

当使用 `task` 工具分发子代理时：
- `Explore` 子代理应优先使用 codegraph_* 工具进行符号定位和调用链梳理
- 子代理输出结论而非原始工具调用
- 提示规则：写「分析 A 并总结 B」，禁止写「读取 X 告诉我内容」或「把 Y 改成 Z」
