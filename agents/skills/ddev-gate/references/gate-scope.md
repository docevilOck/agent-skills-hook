# 改动面清单格式（`gate-scope.yaml`）

机械闸的输入契约。**生成方**：`ddev-plan`（计划定稿时）、`ddev-exec`（执行中维护）。**消费方**：`ddev-gate` P0 机械闸与 P2 漂移对账。审查 subagent 只读，不修改本文件。

## 位置

`<计划目录>/gate-scope.yaml`，与 `exec_plans/` 同级。例：`docs/plans/26-10-21_xxx/gate-scope.yaml`。

## 结构

```yaml
version: 1
task: 26-10-21_z3pro-usb-photo-storage      # 计划目录名
base_ref: HEAD                               # 对账基线（分支/commit）；无提交时用 stash hash
generated_by: ddev-plan                      # ddev-plan | ddev-exec
updated_at: 26-10-21T14:05

planned_files:
  modify:
    - path: src/module/prt_usb_cfg.c
      reason: 新增 Z3Pro USB 遮罩接口
  create:
    - path: src/ui/z3pro/screen/prt_screen_usb.c
      reason: 遮罩页
  delete:
    - path: src/ui/z3pro/screen/showstatus_usb.case
      reason: 路由改向

allowed_globs:                               # 计划允许的整目录改动（脚本产物、文档）
  - src/ui/z3pro/**
  - docs/plans/26-10-21_z3pro-usb-photo-storage/**

impact_surface:
  symbols:                                   # 本计划新增/修改的公共符号
    - prt_usb_ms_arm
  callers:                                   # 已知调用方（计划阶段 grep 到的）
    - src/ui/z3pro/prt_z3pro_sys.c
  headers:                                   # 会被多文件 include 的公共头
    - src/module/prt_usb_cfg.h

registration_points:                         # 必须同步登记的联动点
  - kind: enum                               # enum | dispatch_table | callback_table | build_switch | data_key
    file: src/ui/z3pro/screen/prt_screen.h
    symbol: PRT_SCREEN_USB
  - kind: dispatch_table
    file: src/ui/z3pro/screen/prt_screen.c
    symbol: prt_screen_usb

verification:
  commands:
    - name: build
      cmd: ./build_z3pro.sh
      evidence: build/build_z3pro.log
    - name: sim
      cmd: ./sim_build.sh verify
      evidence: sim/out/verify.log
  latest_run: 26-10-21T13:40
  evidence_fresh: true                       # 证据 mtime 晚于最后一次代码修改

baseline:                                    # 累计漂移锚点，ddev-gate 首轮写入
  ref: 3f2c1ab                               # HEAD 或 stash hash
  captured_at: 26-10-21T14:05
  declared_scale:
    files: 6
    lines: 420

deviations:                                  # 执行期偏离（ddev-exec 维护）
  - id: DEV-usb-01
    point: 额外修改 prt_power_manage_unit.c 增加电源键守卫
    reason: 遮罩态需拦截电源键，计划文件表未列
    impact: 电源状态机三处早退，仅 Z3Pro 生效
    disposition: record                      # fix | record | reject
    reviewed_round: 2
```

## 字段约束

| 字段 | 必填 | 用途 |
|---|---|---|
| `planned_files` | 是 | M1 判越界与漏改 |
| `allowed_globs` | 否 | 允许的整目录改动，优先级高于 planned_files |
| `impact_surface` | 是 | P2 影响面兜底对账基准 |
| `registration_points` | 是（无则空数组） | M4 注册点核验 |
| `verification` | 是 | M5 证据新鲜度 |
| `baseline` | 首轮由 gate 写入 | 累计漂移 |
| `deviations` | 否 | Deviations 闭环（DEV-ID） |

## 维护规则

1. **ddev-plan** 定稿时生成，`planned_files` 来自计划的文件结构表，`registration_points` 来自 spec 的联动修改清单。
2. **ddev-exec** 每完成一个任务更新一次：追加实际改动、追加 `deviations`、刷新 `verification.latest_run`。
3. **ddev-gate** 首轮写 `baseline`；终轮用 `baseline.ref` 做累计 diff 对账。
4. 清单与代码事实冲突时，以代码事实为准并记 `SCOPE_DRIFT`，不得静默修改清单来"对齐"实现。

## 缺失时的降级

| 场景 | 处理 |
|---|---|
| streaming 路线缺清单 | `need-info`：要求补清单，或主 agent 从 spec/detail 手工整理后落盘 |
| compact 路线缺清单 | 允许由 diff 推导，标 `SCOPE: derived`；推导范围不得作为最终 `pass` 的唯一依据 |
| 清单字段残缺（无 registration_points） | 不阻塞，但 M4 记为 `skipped` 并在报告中声明 |
