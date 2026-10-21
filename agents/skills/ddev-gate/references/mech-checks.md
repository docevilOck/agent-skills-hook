# 机械闸检查清单（P0）

由主 agent 执行，**不派 subagent**。所有命令在项目根跑；`<BASE>` 取 `gate-scope.yaml:base_ref`，`<FILES>` 取本次改动文件集（`git diff --name-only <BASE>` + `git status --porcelain` 的未跟踪文件）。

原则：**能用命令判定的，不写进审查报告**。命中项只作为 P1 输入或 backlog，不逐条论述。

## M1 范围对账（FAIL 阻塞派发）

```bash
git diff --name-only <BASE>                      # 已跟踪改动
git status --porcelain | awk '$1=="??"{print $2}' # 未跟踪（必须计入，否则漏审新文件）
```

- 与 `planned_files`（modify / create / delete）+ `allowed_globs` 求差集
- 不在清单内 → **越界**；清单内但未改 → **漏改**（需说明是计划变更还是未完成）
- 越界项若确属必要，先更新 `gate-scope.yaml` 并写明理由，再继续

## M2 注释机械项（不阻塞派发，进 backlog 或先修）

```bash
# 文件头 @file / @brief
for f in <FILES>; do case "$f" in *.c|*.h) head -8 "$f" | grep -q '@file' || echo "MISS @file $f";
  head -8 "$f" | grep -q '@brief' || echo "MISS @brief $f";; esac; done

# 英文注释（中文项目）
grep -nE '^[[:space:]]*(//|/\*).*[A-Za-z]{4,}' <FILES>

# 计划/阶段术语泄漏
grep -nE '阶段|迁移|本轮|本次|版本演进|方案|TODO|FIXME' <FILES>

# 注释掉代码 / #if 0
grep -nE '#if[[:space:]]+0' <FILES>
grep -nE '^[[:space:]]*//[[:space:]]*[A-Za-z_].*[;{()]' <FILES>

# 定义处冗余 extern（.c 文件）
grep -nE '^[[:space:]]*extern[[:space:]].*\(' <FILES> | grep '\.c:'
```

判定：`@file`/`@brief` 缺失 = 机械 HIGH（修完再派发）；其余只进 backlog。

## M3 卫生项（不阻塞派发，进 backlog）

```bash
# 裸 printf / fprintf / sprintf / puts（未走项目日志封装时；snprintf 一般安全，禁用 stdio 的项目再报）
grep -nE '\b(printf|fprintf|sprintf|snprintf)[[:space:]]*\(' <FILES>

# 魔术数字（排除 0/1/2/-1 与宏定义行）
grep -nE '[^A-Za-z0-9_]([3-9]|[1-9][0-9]+)[^A-Za-z0-9_]' <FILES> | grep -v '#define'

# 过长函数（粗略：单文件内大括号深度与行数）
awk '/^[A-Za-z_].*\(.*\)[[:space:]]*\{/{s=NR} /^\}/{if(s&&NR-s>80)print FILENAME":"s" len="NR-s; s=0}' <FILES>

# 零引用符号（对新增 static 函数/宏抽样）
grep -rn '<symbol>' --include='*.c' --include='*.h' .
```

判定：只进 backlog；**不阻塞**。存量代码（非本轮改动行）默认不报。

## M4 注册点（FAIL 阻塞派发）

逐项遍历 `registration_points`：

```bash
grep -n '<symbol>' <file>   # 必须命中；kind=dispatch_table 时同时确认表内新增行
```

判定：任一未命中 → FAIL，主 agent 先补注册。

## M5 证据新鲜度（FAIL 阻塞派发）

```bash
# 最后一次代码修改时间 vs 证据文件 mtime
find <FILES> -newer <evidence_file> -print   # 有输出 = 证据过期
```

判定：证据缺失或早于最后一次代码修改 → FAIL，重跑验证命令。

## M6 文档基线（FAIL 阻塞派发）

```bash
git diff --name-only <BASE> -- '*/spec/*' '*/detail/*' 'docs/architecture/*'
git status --porcelain -- '*/spec/*' '*/detail/*' 'docs/architecture/*'
```

判定：有改动 → 设计基线已变。未声明为设计变更 → `blocked`；已声明 → 重跑 A 全量，且该轮不计入 3 轮预算。

## 输出

压缩成一行 + 一张明细表：

```
MECH: M1=pass M2=3hit M3=2hit M4=pass M5=pass M6=pass
```

| 组 | 结果 | 命中项 | 处置 |
|---|---|---|---|
| M1 | pass | — | — |
| M2 | 3 hit | `prt_x.c` 缺 @brief 等 3 处 | 已修 2 / backlog 1 |
| … | | | |

## 阈值与可移植性

- 项目根 `AGENTS.md` / `CLAUDE.md` 可覆写各组的命令模板（不同语言的注释语法、日志封装名不同）
- 命令模板没覆盖的语言（非 C），M2 / M3 标 `skipped` 并在报告声明，不假装检查过
- 误报处理：同一规则被标误报 ≥2 次 → 加入项目的 `mech-ignore` 列表并写明理由，禁止静默忽略
