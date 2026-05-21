---
name: systematic-debugging
description: 在遇到任何 bug、测试失败或异常行为时使用，且要在提出修复之前使用
---

# 系统化调试

## 概述

随手修补会浪费时间，还会引入新 bug。快速打补丁只会掩盖底层问题。

**核心原则：** 在尝试修复前，始终先找到根因。只修症状就是失败。

**Violating the letter of this process is violating the spirit of debugging.**

## 铁律

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

如果你还没完成第 1 阶段，就不能开始提出修复方案。

## 何时使用

适用于任何技术问题：
- 测试失败
- 生产环境 bug
- 异常行为
- 性能问题
- 构建失败
- 集成问题

**尤其在以下情况要用：**
- 有时间压力时（紧急情况最容易让人想猜）
- “就改一个小修复” 看起来特别明显时
- 你已经试过多个修复
- 上一次修复没起作用
- 你还没有完全理解问题

**不要跳过的情况：**
- 问题看起来很简单时（简单 bug 也有根因）
- 你很赶时（着急只会带来返工）
- 经理要求立刻修好时（系统化方法比乱试更快）

## 四个阶段

你必须先完成当前阶段，才能进入下一阶段。

### 第 1 阶段：根因调查

**在尝试任何修复之前：**

1. **仔细阅读错误信息**
   - 不要跳过错误或警告
   - 它们往往已经包含准确答案
   - 把堆栈信息完整读完
   - 记下行号、文件路径和错误码

2. **稳定复现**
   - 能否稳定触发？
   - 具体步骤是什么？
   - 每次都会发生吗？
   - 如果不能稳定复现 -> 继续收集数据，不要猜

3. **检查最近变更**
   - 哪些变更可能导致这个问题？
   - 查看 git diff 和最近提交
   - 新依赖、配置变化
   - 环境差异

4. **在多组件系统中收集证据**

   **当系统包含多个组件时（CI -> build -> signing，API -> service -> database）：**

   **在提出修复之前，先加诊断埋点：**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

   **Example (multi-layer system):**
   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **这会揭示：** 是哪一层失败了（secrets -> workflow ✓，workflow -> build ✗）

5. **追踪数据流**

   **当错误出现在很深的调用栈里时：**

   See `root-cause-tracing.md` in this directory for the complete backward tracing technique.

   **简版：**
   - 错误值最初来自哪里？
   - 是谁用这个错误值调用了它？
   - 一直往上追，直到找到源头
   - 修源头，不修症状

### 第 2 阶段：模式分析

**先找模式，再修复：**

1. **找能工作的例子**
   - 在同一代码库里找相似且正常工作的代码
   - 哪些地方和坏掉的代码相似，但能正常运行？

2. **对照参考实现**
   - 如果是在套用某个模式，要把参考实现完整读完
   - 不要扫读，要逐行看
   - 应用之前先彻底理解这个模式

3. **识别差异**
   - 正常和异常之间有什么不同？
   - 把每一个差异都列出来，哪怕很小
   - 不要想当然地认为“这个不重要”

4. **理解依赖**
   - 它还需要哪些其他组件？
   - 需要什么设置、配置、环境？
   - 它基于哪些假设？

### 第 3 阶段：假设与测试

**科学方法：**

1. **提出单一假设**
   - 清楚地说出来：“我认为 X 是根因，因为 Y”
   - 写下来
   - 要具体，不要模糊

2. **最小化测试**
   - 用尽可能小的改动验证假设
   - 一次只改一个变量
   - 不要一次修好多个问题

3. **继续前先验证**
   - 生效了吗？是 -> 进入第 4 阶段
   - 没生效？重新提出新的假设
   - 不要在上面继续叠加更多修复

4. **不知道时**
   - 直接说 “我不理解 X”
   - 不要假装自己懂
   - 该求助就求助
   - 继续研究

### 第 4 阶段：实现

**修根因，不修症状：**

1. **先创建能稳定复现问题的验证手段**
   - 用最简单的方式复现
   - 如果可以，写自动化测试
   - 如果没有框架，就写一次性测试脚本
   - 修复之前必须先有它

2. **Implement Single Fix**
   - Address the root cause identified
   - ONE change at a time
   - No "while I'm here" improvements
   - No bundled refactoring

3. **Verify Fix**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?

4. **If Fix Doesn't Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If ≥ 3: STOP and question the architecture (step 5 below)**
   - DON'T attempt Fix #4 without architectural discussion

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with your human partner before attempting more fixes**

   This is NOT a failed hypothesis - this is a wrong architecture.

## Red Flags - STOP and Follow Process

如果你发现自己在想下面这些话：
- “先随便修一下，回头再调查”
- “先改 X 看看能不能好”
- “多改几处，一起跑测试”
- “测试先不写，我手工验证就行”
- “大概是 X，我先修它”
- “我没完全理解，但这也许能行”
- “模式说要 X，但我换个方式适配一下”
- “主要问题是这些：[没调查就列一堆修复]”
- 在追踪数据流之前就开始提方案
- **“再试一次修复”**（已经试过 2 次以上时）
- **每次修复都会在别的地方冒出新问题**

**以上任何一种情况都意味着：立刻停止，回到第 1 阶段。**

**如果已经失败了 3 次以上：** 就要质疑架构（见第 4.5 步）

## 你的协作对象发出的“你走偏了”信号

**留意这些纠偏：**
- “不是没发生吗？” - 你在没验证的情况下做了假设
- “它会不会显示出……？” - 你本该先加证据收集
- “别猜了” - 你在没理解前就开始提修复
- “把这个问题想深一点” - 该质疑的是基本原理，不只是症状
- “我们卡住了？”（带着挫败感）- 你的方法没有奏效

**一旦听到这些信号：** 立刻停止，回到第 1 阶段。

## 常见合理化

| 借口 | 现实 |
|--------|---------|
| “问题很简单，不需要流程” | 简单问题也有根因。对简单 bug 来说，流程反而更快。 |
| “这是紧急情况，没时间走流程” | 系统化调试比乱猜乱试更快。 |
| “先试这个，等会儿再调查” | 第一个修复会定下模式。开头就要做对。 |
| “先确认修复有效，再写测试” | 没测试的修复不稳。先测试才能证明。 |
| “一次改多个地方更省时间” | 没法分辨到底是哪一处起作用，还容易引入新 bug。 |
| “参考太长了，我按模式改一下就行” | 只懂一半，必然会出 bug。要完整读完。 |
| “我看到问题了，直接修就行” | 看到症状，不等于理解根因。 |
| “再试一次修复就好”（已经失败 2 次以上） | 失败 3 次以上说明是架构问题。该质疑模式，不该继续乱修。 |

## 快速参考

| 阶段 | 关键动作 | 成功标准 |
|-------|---------------|------------------|
| **1. 根因** | 看错误、复现、查变更、收集证据 | 明白是什么、为什么 |
| **2. 模式** | 找正常例子、对比 | 找出差异 |
| **3. 假设** | 提出理论、最小化测试 | 证实或产生新假设 |
| **4. 实现** | 创建测试、修复、验证 | bug 已解决，测试通过 |

## 当流程显示“没有根因”时

如果系统化调查后发现，这个问题确实是环境相关、时序相关，或者来自外部：

1. 说明你已经完成了流程
2. 记录你调查过什么
3. 加入合适的处理方式（重试、超时、错误提示）
4. 为后续调查加上监控/日志

**但是：** 95% 的“没有根因”案例，其实都是调查还不完整。

## 配套技巧

下面这些技巧是系统化调试的一部分，也都在这个目录里：

- **`root-cause-tracing.md`** - Trace bugs backward through call stack to find original trigger
- **`defense-in-depth.md`** - Add validation at multiple layers after finding root cause
- **`condition-based-waiting.md`** - Replace arbitrary timeouts with condition polling

**相关 skills：**
- **superpowers:verification-before-completion** - Verify fix worked before claiming success

## 实际影响

来自调试实战：
- 系统化方法：15-30 分钟修好
- 随机修法：2-3 小时反复折腾
- 首次修复成功率：95% 对 40%
- 引入新 bug 的数量：几乎为零，对比常见
