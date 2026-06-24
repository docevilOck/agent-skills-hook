# 常见联动模式目录

当对代码做"新增 X"类改动（新增模块/指令/驱动/配置项/平台适配）时，按本目录逐模式搜索，确认是否有需要联动修改的位置。

**使用方式**：对每种模式，先用 codegraph_search 搜符号名，未命中则用 grep 搜正则，仍未命中则标注"未发现"并继续下一种。

---

## 1. 指令/消息分发表

**描述**：集中注册指令名→处理函数的映射表，新增指令类型时必须在此表中添加条目。

**搜索关键词（codegraph）**：`cmd_table`, `command_table`, `instruction_table`, `msg_handler`, `extra_cmd`, `cmd_handler`, `op_table`, `opcode`

**grep 正则**：`(cmd|command|instruction|msg|op|extra)_(table|handler|map)\s*\[\s*\]`

**典型位置**：`*_cmd.c`, `*_handler.c`, `*_parser.c`, `*_dispatch.c`

**判断标准**：找到的表条目中，是否存在与"本次新增类型"同类的条目？如果已有 `CMD_CLOUD_ALI`, `CMD_CLOUD_TENCENT`，新增 `CMD_CLOUD_AWS` 就必须加。

---

## 2. 回调/钩子注册

**描述**：模块对外暴露的回调注册接口或内部回调函数表，新增功能点时常需要注册对应的回调处理。

**搜索关键词（codegraph）**：`callback_register`, `event_handler`, `hook_list`, `_callback`, `notify_`, `observer_`, `listener_`

**grep 正则**：`(callback|hook|event|notify|observer|listener|signal)\s*(_register|_add|_connect|_handler|_list|_fn)`

**典型位置**：`*_event.c`, `*_callback.c`, `*_notify.c`，或模块公共头文件的注册 API

**判断标准**：是否存在通用的"事件/状态变更回调链"，本次新增的操作/状态是否会触发这些事件？如果是，需要注册对应的回调。

---

## 3. 枚举↔字符串/枚举↔函数映射表

**描述**：将枚举值映射到字符串名或处理函数的表，新增枚举值时必须同步更新。

**搜索关键词（codegraph）**：`_name_map`, `_to_string`, `_from_string`, `_type_map`, `_handler_map`, `enum_name`, `type_str`

**grep 正则**：`(map|table|dict|array)\s*\[.*enum|switch\s*\(.*type.*\)\s*\{`

**典型位置**：`*_util.c`, `*_format.c`, `*_debug.c`, `*_config.c`

**判断标准**：如果新增了一个枚举值（如新增云平台类型），所有 `switch(type)` 和 `type_name[]` 映射表是否都需要添加新条目？

---

## 4. 模块/驱动注册数组

**描述**：系统启动时通过遍历静态数组来初始化各模块/驱动，新增模块时必须在此数组中注册。

**搜索关键词（codegraph）**：`driver_list`, `module_init`, `_register`, `_init_table`, `_modules`, `device_table`, `plugin_list`

**grep 正则**：`(driver|module|device|plugin)\s*(_list|_table|_init|_register|_mgmt)`

**典型位置**：`*_init.c`, `main.c`, `*_platform.c`, `*_board.c`

**判断标准**：现有模块是否都集中注册在一个数组或初始化函数链中？新增模块时是否需要在同位置添加初始化调用？

---

## 5. 配置项初始化列表

**描述**：默认配置、参数表、K-V 配置项的集中定义，新增可配置功能时需要添加默认值。

**搜索关键词（codegraph）**：`default_config`, `config_init`, `_params`, `_settings`, `_options`, `config_table`, `cfg_default`

**grep 正则**：`(default|init|cfg)_(config|param|setting|option)`

**典型位置**：`*_config.c`, `*_defaults.c`, `*_params.h`, `*_profile.c`

**判断标准**：新增功能是否有可配置参数？如果有，配置默认值表是否需要添加条目？

---

## 6. 条件编译开关链

**描述**：通过 `#ifdef` / `#if defined()` 控制功能裁剪，新增可选功能时需要在多个文件的编译开关处添加分支。

**搜索关键词（codegraph）**：不适用（预处理器宏不是符号）。改为直接用 grep。

**grep 正则**：`#\s*if(def|\s+defined)\s*\(.*(FEATURE|ENABLE|HAS|WITH|CONFIG)_`

**典型位置**：`*_cfg.h`, `*_config.h`, `*.h`（全局配置头），以及实现文件中分散的 `#ifdef` 块

**判断标准**：同类功能的编译开关（如 `#ifdef FEATURE_CLOUD_ALI`, `#ifdef FEATURE_CLOUD_TENCENT`）是否在多个文件中被检查？新增的 `FEATURE_CLOUD_AWS` 是否需要在同样的位置添加？

---

## 7. 构建/编译系统联动

**描述**：Makefile、CMakeLists.txt、Kconfig 等构建系统中注册源文件、编译选项、配置项的位置，新增 `.c` 文件时必须同步更新。

**搜索关键词（codegraph）**：不适用（构建文件中的变量不是代码符号）。改为用 Glob + grep。

**grep 正则**：`SRC_FILES|obj-y|target_sources|add_executable|add_library|SOURCES`

**典型位置**：`CMakeLists.txt`, `Makefile`, `*.mk`, `Kconfig`, `Kbuild`, `meson.build`, `BUILD`

**判断标准**：新增的 `.c` 文件是否已添加到构建系统的源文件列表中？新增的编译宏是否已加入配置选项？

---

## 兜底规则（必须遵守）

如果对某次改动执行了上述所有模式的搜索，但全部返回空结果（项目使用非标准命名、代码生成产物、DSL 生成代码、宏展开后的符号）——

**禁止直接跳过或只写"无"**。必须在联动修改清单中显式输出：

```markdown
**联动影响分析：未发现标准化联动模式**
- 本次改动范围：[简述]
- 已搜索的模式：指令表/回调/枚举映射/模块注册/配置/编译开关/构建系统
- 搜索关键词：[列出实际使用的关键词]
- 搜索目录：[列出实际搜索的目录]
- 结论：未发现符合标准模式的联动点，**需人工确认**是否存在以下非标准形式的联动：[列举可能的非标准形式]
```

缺少搜索过程或仅写"无联动点"视为分析失败，应回退重做。
