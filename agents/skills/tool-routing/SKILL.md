---
name: tool-routing
description: Unified retrieval tool routing rules. Use for choosing among codegraph_*, ctx_*, semble, and grep/Read based on whether the task needs structural facts, context sandboxing, semantic candidate discovery, or literal verification.
---

# tool-routing

## 触发条件

任何涉及以下场景的任务，必须自动匹配加载：
- 查找符号定义、调用链、模块结构、影响范围
- 使用 `ctx_*` 做上下文节流、沙箱执行或续接检索
- 需要语义候选发现、相似实现召回、命名不明确时的候选定位
- 需要对已知路径或字面量做精确核对

## 四层职责

| 层级 | 作用 | 约束 |
|---|---|---|
| `codegraph_*` | 结构化事实查询 | 主事实源，优先级最高 |
| `ctx_*` | 上下文节流 / 沙箱 / 续接检索 | 不替代结构事实判断 |
| `semble` | 语义候选发现 | 只给候选，不给最终事实 |
| `grep` / `Read` | 字面量与已知路径核对 | 不用于替代结构查询 |

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
| 上下文节流 / 沙箱 / 续接检索 | `ctx_*` |
| 相似实现 / 语义候选发现 | `semble_*` 或 `semble` CLI |
| 字面量搜索 | `grep` |
| 已知路径文件读取 | `Read` |

## 执行决策树

```
任务
├─ 结构查询（符号/调用/架构/影响）？
│   ├─ 先 codegraph_status → 未初始化则询问用户或按仓库规则初始化
│   ├─ 已初始化 → 使用 codegraph_*
│   └─ 禁止直接用 grep/Read/semble 代替事实判断
│
├─ 上下文治理（节流/沙箱/续接）？
│   └─ 使用 ctx_*
│
├─ 命名不明确或需要找相似实现候选？
│   ├─ 使用 semble
│   └─ 结果必须再用 codegraph_* 或 grep/Read 二次验证
│
├─ 已知路径或字面量核对？
│   ├─ 文本搜索 → grep
│   └─ 已知路径读取 → Read
│
└─ 基础设施 shell（git/mkdir/rm/mv/npm/pip）？
    └─ 直接执行
```

## 阻断规则

以下行为被明确禁止：
- **用 `semble` 替代 `codegraph_*` 做结构事实判断** → 禁止
- **grep 搜符号定义** → 禁止。先用 `codegraph_search`
- **Read 理解架构** → 禁止。先用 `codegraph_context`
- **假设 CodeGraph 索引已存在** → 禁止。每次先 `codegraph_status`
- **把 `ctx_*` 当作结构查询主路径** → 禁止
- **未二次验证就直接采用 `semble` 结果改代码** → 禁止

## 子代理分发约束

当使用 `task` 工具分发子代理时：
- 子代理提示里要写清目标是“结构事实”“上下文治理”“语义候选”还是“字面量核对”
- `Explore` 子代理做结构理解时优先 `codegraph_*`
- 只有在“找候选实现”场景下才允许子代理优先用 `semble`
- 子代理输出结论而非原始工具调用
- 提示规则：写「分析 A 并总结 B」，禁止写「读取 X 告诉我内容」或「把 Y 改成 Z」

## 版本说明

- 本 skill 是唯一检索工具路由入口，融合了原 `codegraph-tool-routing` 的 CodeGraph-first 规则和 `ctx_*`/`semble`/`grep`/`Read` 四层分流
