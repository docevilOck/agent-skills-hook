---
name: codegraph-tool-routing
description: Legacy compatibility entry for CodeGraph-first routing. Use when a runtime still references codegraph-tool-routing; migrate new routing rules to tool-routing, which now owns codegraph_*, ctx_*, semble, and grep/Read dispatch.
---

# codegraph-tool-routing

> 兼容说明：这是旧入口名。新的统一路由规则已迁移到 `tool-routing`，新会话与新入口文档应优先加载 `tool-routing`。

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

同时保留迁移约束：
- `codegraph-tool-routing` 仍只负责强调 CodeGraph-first 事实查询
- `ctx_*`、`semble`、`grep/read` 的统一分流规则由 `tool-routing` 承接
- 如果运行时仍只加载旧 skill，不得把 `semble` 提升为主事实源

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

## 迁移路径

- 保留当前 skill 名称，避免旧入口立即失效
- 新增 `tool-routing` 作为统一工具路由 skill
- 三套运行时入口文档切换到 `tool-routing` 后，这个旧 skill 只保留兼容说明与 CodeGraph-first 子集规则
