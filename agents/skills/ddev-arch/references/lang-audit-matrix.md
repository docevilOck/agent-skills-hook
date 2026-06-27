# 语言审计路由矩阵

> 本文档定义 ddev-arch 步骤 5（项目依赖与封装审计）和步骤 6（构建变体与环境审计）按项目语言的分流策略。
> 由 ddev-arch 在探索阶段检测项目语言后，自动选择对应的审计路径。

---

## 语言检测规则

| 检测信号 | 判定语言 | 优先级 |
|---------|---------|--------|
| 仓库中 `.c`/`.h` 文件占比 > 50% 且存在 `Makefile`/`CMakeLists.txt` | C | 1 |
| 仓库中 `.cpp`/`.hpp`/`.cc` 文件占比 > 50% | C++ | 1 |
| 存在 `Cargo.toml` 且 `.rs` 文件为主 | Rust | 2 |
| 存在 `go.mod` 且 `.go` 文件为主 | Go | 2 |
| 存在 `pyproject.toml`/`setup.py`/`requirements.txt` 且 `.py` 文件为主 | Python | 2 |
| 存在 `package.json` 且 `.ts`/`.tsx` 文件为主 | TypeScript | 2 |
| 存在 `package.json` 且 `.js`/`.jsx` 文件为主 | JavaScript | 2 |
| 存在 `pom.xml`/`build.gradle` 且 `.java` 文件为主 | Java | 3 |
| 无法匹配以上任何规则 | Generic（通用） | 4 |

检测结果写入 `01_架构总览.md` 的「技术栈」字段。后续步骤以此为分流依据。

---

## 步骤 5：项目依赖与封装审计 — 分流矩阵

| 语言 | 审计策略 | 产出文档 |
|------|---------|---------|
| **C** | 标准库替代函数审计（malloc/free/strcpy/sprintf/printf/assert 等 45+ 函数）+ 条件编译门控审计 + 第三方库适配检查 | `stdlib-wrappers.md`（含条件编译门控章节 + 门控宏速查表 + 第三方库适配表） |
| **C++** | C 标准库审计子集（内存/字符串/文件 I/O）+ STL 使用策略审计（是否禁用异常/RTTI、是否使用自定义 allocator、智能指针策略）+ 第三方库适配检查 | `stdlib-wrappers.md`（含 C/C++ 混合约束 + 第三方库适配表） |
| **Rust** | crate 依赖审计（Cargo.toml 依赖树、feature flag 矩阵、`unsafe` 封装审计、`std`/`no_std` 策略） | `dependency-audit.md`（含 crate 依赖关系图 + feature 矩阵 + unsafe 边界清单） |
| **Go** | 模块依赖审计（go.mod 依赖树、replace/retract 记录、标准库替代封装扫描、`unsafe`/`cgo` 使用审计） | `dependency-audit.md`（含模块依赖图 + unsafe/cgo 边界清单） |
| **Python** | 包依赖审计（requirements.txt/pyproject.toml 依赖树、标准库替代封装扫描、C 扩展模块审计、虚拟环境策略） | `dependency-audit.md`（含包依赖关系 + C 扩展清单） |
| **TypeScript / JavaScript** | 包依赖审计（package.json 依赖树、bundle 策略、polyfill 策略、Node.js API 使用审计） | `dependency-audit.md`（含包依赖关系） |
| **Java** | 依赖审计（Maven/Gradle 依赖树、标准库替代封装扫描、反射/JNI 使用审计） | `dependency-audit.md` |
| **Generic** | 记录依赖清单文件路径（包管理器配置文件、vendor 目录等），不做深度审计 | `dependency-manifest.md` |

### C 语言标准库审计流程（保留现有逻辑，不做修改）

当语言检测为 C 时，执行原有的「标准库替代函数审计」完整流程（2 轮搜索 + stdlib-wrappers.md 产出），详见 SKILL.md 中的对应章节。包括：
- 全量扫描 9 大类 45+ 标准库函数
- 条件编译门控审计（`#if`/`#ifdef`/`#if defined()` 扫描）
- 第三方库适配检查（FatFs/lwIP/mbedTLS/FreeRTOS 等）

### 非 C 语言审计流程（简化版）

当语言检测为非 C 时：

1. **识别依赖清单文件**：定位包管理器配置文件（如 `Cargo.toml`、`go.mod`、`pyproject.toml`、`package.json`）
2. **提取依赖树**：解析配置文件，提取直接依赖和版本约束
3. **扫描标准库替代封装**：在项目源码中搜索对标准库函数的封装（如 Python 的 `os.path` 封装、Rust 的 allocator 自定义等）
4. **记录关键依赖关系**：产出依赖清单，标注风险依赖（已废弃、有已知漏洞、版本过旧）
5. **不要求多轮审计**：非 C 语言审计为单轮，不要求 2 轮循环验证

---

## 步骤 6：构建变体与环境审计 — 分流矩阵

| 语言 | 审计策略 | 产出位置 |
|------|---------|---------|
| **C（嵌入式）** | 机型宏扫描与注入（搜索 `cfg.h`、提取 `#define MODELNAME`、识别构建变体、注入 `CLAUDE.md`） | 机型子目录或根目录 `CLAUDE.md` |
| **C（非嵌入式）** | 记录构建命令、产物路径、编译选项；无变体则单条目记录 | 根目录 `CLAUDE.md` |
| **C++（嵌入式）** | 同 C（嵌入式）逻辑 | 同 C |
| **C++（非嵌入式）** | 记录构建系统类型（CMake/Bazel/...）、构建命令、产物路径 | 根目录 `CLAUDE.md` |
| **Rust** | 记录 cargo 构建命令、feature flag 组合、target 矩阵、产物路径 | 根目录 `CLAUDE.md` |
| **Go** | 记录 `go build` 命令、GOOS/GOARCH 组合、产物路径 | 根目录 `CLAUDE.md` |
| **Python** | 记录虚拟环境策略、入口脚本路径、打包方式（wheel/sdist/pepx） | 根目录 `CLAUDE.md` |
| **TypeScript / JavaScript** | 记录构建工具（webpack/vite/esbuild）、环境变量、产物路径 | 根目录 `CLAUDE.md` |
| **Java** | 记录 Maven/Gradle 构建命令、profile/flavor 矩阵、产物路径 | 根目录 `CLAUDE.md` |
| **Generic** | 记录构建命令和产物路径（如果能识别），否则跳过 | 根目录 `CLAUDE.md` 或跳过 |

### 嵌入式 C 机型宏扫描（保留现有逻辑，不做修改）

当语言检测为 C 且判定为嵌入式项目（存在 `cfg.h`、`VERSION_MAJOR`、`#define MODELNAME` 等信号）时，执行原有的「机型宏扫描与注入」完整流程，详见 SKILL.md 中的对应章节。包括：
- 搜索所有 `cfg.h`
- 提取机型宏定义
- 判断仓库类型（多机型分目录 / 单构建多机型 / 单机型）
- 注入机型信息到对应 `CLAUDE.md`

### 非嵌入式项目构建审计（简化版）

当语言检测为非嵌入式 C 或其他语言时：

1. **识别构建系统**：定位构建配置文件（Makefile/CMakeLists.txt/Cargo.toml/go.mod/pyproject.toml/package.json）
2. **提取构建命令**：从构建系统推断标准构建命令
3. **记录产物路径**：识别输出目录（build/dist/target/out）
4. **记录环境变量**：如果存在 `.env` / `.env.example` / `config/` 等环境配置，记录关键环境变量
5. **写入 `CLAUDE.md`**：在根目录 `CLAUDE.md` 中追加简化版构建说明

---

## 验收标准 — 按语言动态生成

ddev-arch 的验收标准中，以下检查项按项目语言条件化：

| 检查项 | C 项目 | 非 C 项目 |
|--------|--------|----------|
| 标准库审计 | ✅ 必须 | 变更为「依赖清单审计」：依赖清单文件已解析，关键依赖已记录 |
| 标准库审计质量 | ✅ 必须 | 变更为「依赖完整性」：直接依赖无遗漏 |
| 条件编译门控 | ✅ 必须 | ❌ 跳过 |
| 第三方库适配 | ✅ 必须 | 变更为「第三方依赖清单」：依赖树已提取，风险依赖已标注 |
| 机型宏注入 | ✅ 嵌入式 C 必须 | ❌ 跳过 |
| 机型宏完整性 | ✅ 嵌入式 C 必须 | ❌ 跳过 |
| 构建信息注入 | ✅ | ✅（简化版：构建命令 + 产物路径） |

---

## AGENTS.md 注入模板 — 按语言调整

AGENTS.md/CLAUDE.md 注入模板中：

- **C 项目**：保留「先确认当前机型宏」提示 + 保留机型说明段
- **非 C 项目**：去掉「先确认当前机型宏」，机型说明段替换为「构建说明」段（含构建命令 + 产物路径 + 环境变量）
