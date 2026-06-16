---
name: obsidian-bases
description: 创建和编辑 Obsidian Bases（.base 文件），支持视图、过滤器、公式和汇总。当处理 .base 文件、创建类似数据库的笔记视图，或用户提到 Obsidian 中的 Bases、表格视图、卡片视图、过滤器或公式时使用。
---

# Obsidian Bases 技能

## 工作流

1. **创建文件**：在 vault 中创建一个 `.base` 文件，包含合法的 YAML 内容
2. **定义范围**：添加 `filters` 来筛选显示哪些笔记（按标签、文件夹、属性或日期）
3. **添加公式**（可选）：在 `formulas` 部分定义计算属性
4. **配置视图**：添加一个或多个视图（`table`、`cards`、`list` 或 `map`），通过 `order` 指定要显示的属性
5. **验证**：验证文件是合法的 YAML，无语法错误。检查所有引用的属性和公式是否存在。常见问题：含有 YAML 特殊字符的未加引号字符串、公式表达式中引号不匹配、在 `order` 或 `properties` 中引用 `formula.X` 但未在 `formulas` 中定义 `X`
6. **在 Obsidian 中测试**：在 Obsidian 中打开 `.base` 文件确认视图正确渲染。如果显示 YAML 错误，检查下方的引号规则

## Schema

Base 文件使用 `.base` 扩展名，包含合法的 YAML。

```yaml
# 全局过滤器应用于 Base 中的所有视图
filters:
  # 可以是单个过滤器字符串
  # 或者是递归过滤器对象，仅包含一个键：and、or 或 not
  and:
    - 'status == "active"'
    - not:
        - 'file.hasTag("archived")'

# 定义可在所有视图中使用的公式属性
formulas:
  formula_name: 'expression'

# 配置属性的显示名称和设置
properties:
  property_name:
    displayName: "显示名称"
  formula.formula_name:
    displayName: "公式显示名称"
  file.ext:
    displayName: "扩展名"

# 定义自定义汇总公式
summaries:
  custom_summary_name: 'values.mean().round(3)'

# 定义一个或多个视图
views:
  - type: table | cards | list | map
    name: "视图名称"
    limit: 10                    # 可选：限制结果数量
    groupBy:                     # 可选：分组结果
      property: property_name
      direction: ASC | DESC
    filters:                     # 视图级过滤器，遵循相同规则
      and:
        - 'status == "active"'
    order:                       # 要显示的属性，按顺序排列
      - file.name
      - property_name
      - formula.formula_name
    summaries:                   # 将属性映射到汇总公式
      property_name: Average
```

## 过滤器语法

过滤器用于缩小结果范围，可以全局应用或按视图应用。

### 过滤器结构

```yaml
# 单个过滤器
filters: 'status == "done"'

# AND - 所有条件必须为 true
filters:
  and:
    - 'status == "done"'
    - 'priority > 3'

# OR - 任一条件为 true
filters:
  or:
    - 'file.hasTag("book")'
    - 'file.hasTag("article")'

# NOT - 排除匹配项
filters:
  not:
    - 'file.hasTag("archived")'

# 嵌套过滤器
filters:
  or:
    - file.hasTag("tag")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.hasTag("book")
        - file.inFolder("Required Reading")
```

### 过滤器运算符

| 运算符 | 描述 |
|--------|------|
| `==` | 等于 |
| `!=` | 不等于 |
| `>` | 大于 |
| `<` | 小于 |
| `>=` | 大于等于 |
| `<=` | 小于等于 |
| `&&` | 逻辑与 |
| `\|\|` | 逻辑或 |
| <code>!</code> | 逻辑非 |

## 属性

### 三种属性类型

1. **笔记属性**（Note properties） - 来自 frontmatter：`note.author` 或直接 `author`
2. **文件属性**（File properties） - 文件元数据：`file.name`、`file.mtime` 等
3. **公式属性**（Formula properties） - 计算值：`formula.my_formula`

### 文件属性参考

| 属性 | 类型 | 描述 |
|------|------|------|
| `file.name` | String | 文件名 |
| `file.basename` | String | 不含扩展名的文件名 |
| `file.path` | String | 文件完整路径 |
| `file.folder` | String | 父文件夹路径 |
| `file.ext` | String | 文件扩展名 |
| `file.size` | Number | 文件大小（字节） |
| `file.ctime` | Date | 创建时间 |
| `file.mtime` | Date | 修改时间 |
| `file.tags` | List | 文件中的所有标签 |
| `file.links` | List | 文件中的内部链接 |
| `file.backlinks` | List | 链接到本文件的文件 |
| `file.embeds` | List | 笔记中的嵌入内容 |
| `file.properties` | Object | 所有 frontmatter 属性 |

### `this` 关键字

- 在主内容区域：指向 base 文件本身
- 嵌入时：指向嵌入方文件
- 在侧边栏：指向主内容中的活动文件

## 公式语法

公式从属性计算值，在 `formulas` 部分定义。

```yaml
formulas:
  # 简单算术
  total: "price * quantity"

  # 条件逻辑
  status_icon: 'if(done, "✅", "⏳")'

  # 字符串格式化
  formatted_price: 'if(price, price.toFixed(2) + " dollars")'

  # 日期格式化
  created: 'file.ctime.format("YYYY-MM-DD")'

  # 计算自创建以来的天数（使用 .days 获取 Duration）
  days_old: '(now() - file.ctime).days'

  # 计算距离截止日期的天数
  days_until_due: 'if(due_date, (date(due_date) - today()).days, "")'
```

## 常用函数

最常用的函数。所有类型（Date、String、Number、List、File、Link、Object、RegExp）的完整参考见 [FUNCTIONS_REFERENCE.md](references/FUNCTIONS_REFERENCE.md)。

| 函数 | 签名 | 描述 |
|------|------|------|
| `date()` | `date(string): date` | 将字符串解析为日期（`YYYY-MM-DD HH:mm:ss`） |
| `now()` | `now(): date` | 当前日期和时间 |
| `today()` | `today(): date` | 当前日期（时间 = 00:00:00） |
| `if()` | `if(condition, trueResult, falseResult?)` | 条件判断 |
| `duration()` | `duration(string): duration` | 解析时长字符串 |
| `file()` | `file(path): file` | 获取文件对象 |
| `link()` | `link(path, display?): Link` | 创建链接 |

### Duration 类型

两个日期相减时，结果是 **Duration** 类型（不是 number）。

**Duration 字段：** `duration.days`、`duration.hours`、`duration.minutes`、`duration.seconds`、`duration.milliseconds`

**重要：** Duration 不直接支持 `.round()`、`.floor()`、`.ceil()`。需要先访问数值字段（如 `.days`），然后再应用数值函数。

```yaml
# 正确：计算两个日期之间的天数
"(date(due_date) - today()).days"                    # 返回天数
"(now() - file.ctime).days"                          # 自创建以来的天数
"(date(due_date) - today()).days.round(0)"           # 四舍五入天数

# 错误 - 会导致报错：
# "((date(due) - today()) / 86400000).round(0)"      # Duration 不支持除法后再 round
```

### 日期运算

```yaml
# 时长单位：y/year/years、M/month/months、d/day/days、
#           w/week/weeks、h/hour/hours、m/minute/minutes、s/second/seconds
"now() + \"1 day\""       # 明天
"today() + \"7d\""        # 一周后
"now() - file.ctime"      # 返回 Duration
"(now() - file.ctime).days"  # 以天数形式获取
```

## 视图类型

### 表格视图（Table View）

```yaml
views:
  - type: table
    name: "我的表格"
    order:
      - file.name
      - status
      - due_date
    summaries:
      price: Sum
      count: Average
```

### 卡片视图（Cards View）

```yaml
views:
  - type: cards
    name: "图库"
    order:
      - file.name
      - cover_image
      - description
```

### 列表视图（List View）

```yaml
views:
  - type: list
    name: "简单列表"
    order:
      - file.name
      - status
```

### 地图视图（Map View）

需要纬度/经度属性和 Maps 社区插件。

```yaml
views:
  - type: map
    name: "位置"
    # 经纬度属性的地图特定设置
```

## 默认汇总公式

| 名称 | 输入类型 | 描述 |
|------|---------|------|
| `Average` | Number | 算术平均值 |
| `Min` | Number | 最小值 |
| `Max` | Number | 最大值 |
| `Sum` | Number | 所有数值之和 |
| `Range` | Number | 最大值 - 最小值 |
| `Median` | Number | 中位数 |
| `Stddev` | Number | 标准差 |
| `Earliest` | Date | 最早日期 |
| `Latest` | Date | 最晚日期 |
| `Range` | Date | 最晚 - 最早 |
| `Checked` | Boolean | true 值的数量 |
| `Unchecked` | Boolean | false 值的数量 |
| `Empty` | Any | 空值的数量 |
| `Filled` | Any | 非空值的数量 |
| `Unique` | Any | 唯一值的数量 |

## 完整示例

### 任务追踪 Base

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'file.ext == "md"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'
  is_overdue: 'if(due, date(due) < today() && status != "done", false)'
  priority_label: 'if(priority == 1, "🔴 高", if(priority == 2, "🟡 中", "🟢 低"))'

properties:
  status:
    displayName: 状态
  formula.days_until_due:
    displayName: "距离截止天数"
  formula.priority_label:
    displayName: 优先级

views:
  - type: table
    name: "活跃任务"
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - status
      - formula.priority_label
      - due
      - formula.days_until_due
    groupBy:
      property: status
      direction: ASC
    summaries:
      formula.days_until_due: Average

  - type: table
    name: "已完成"
    filters:
      and:
        - 'status == "done"'
    order:
      - file.name
      - completed_date
```

### 阅读清单 Base

```yaml
filters:
  or:
    - file.hasTag("book")
    - file.hasTag("article")

formulas:
  reading_time: 'if(pages, (pages * 2).toString() + " 分钟", "")'
  status_icon: 'if(status == "reading", "📖", if(status == "done", "✅", "📚"))'
  year_read: 'if(finished_date, date(finished_date).year, "")'

properties:
  author:
    displayName: 作者
  formula.status_icon:
    displayName: ""
  formula.reading_time:
    displayName: "预计时间"

views:
  - type: cards
    name: "图书馆"
    order:
      - cover
      - file.name
      - author
      - formula.status_icon
    filters:
      not:
        - 'status == "dropped"'

  - type: table
    name: "阅读清单"
    filters:
      and:
        - 'status == "to-read"'
    order:
      - file.name
      - author
      - pages
      - formula.reading_time
```

### 日记索引

```yaml
filters:
  and:
    - file.inFolder("Daily Notes")
    - '/^\d{4}-\d{2}-\d{2}$/.matches(file.basename)'

formulas:
  word_estimate: '(file.size / 5).round(0)'
  day_of_week: 'date(file.basename).format("dddd")'

properties:
  formula.day_of_week:
    displayName: "星期"
  formula.word_estimate:
    displayName: "~字数"

views:
  - type: table
    name: "最近笔记"
    limit: 30
    order:
      - file.name
      - formula.day_of_week
      - formula.word_estimate
      - file.mtime
```

## 嵌入 Base

在 Markdown 文件中嵌入：

```markdown
![[MyBase.base]]

<!-- 指定视图 -->
![[MyBase.base#View Name]]
```

## YAML 引号规则

- 包含双引号的公式使用单引号包裹：`'if(done, "Yes", "No")'`
- 简单字符串使用双引号：`"My View Name"`
- 复杂表达式中正确转义嵌套引号

## 故障排查

### YAML 语法错误

**未加引号的特特殊字符**：包含 `:`、`{`、`}`、`[`、`]`、`,`、`&`、`*`、`#`、`?`、`|`、`-`、`<`、`>`、`=`、`!`、`%`、`@`、`` ` `` 的字符串必须加引号。

```yaml
# 错误 - 未加引号的字符串中含有冒号
displayName: Status: Active

# 正确
displayName: "Status: Active"
```

**公式中引号不匹配**：当公式包含双引号时，用单引号包裹整个公式。

```yaml
# 错误 - 双引号内嵌套双引号
formulas:
  label: "if(done, "Yes", "No")"

# 正确 - 单引号包裹双引号
formulas:
  label: 'if(done, "Yes", "No")'
```

### 常见公式错误

**Duration 运算未访问字段**：日期相减返回 Duration，不是 number。始终要访问 `.days`、`.hours` 等。

```yaml
# 错误 - Duration 不是 number
"(now() - file.ctime).round(0)"

# 正确 - 先访问 .days，再 round
"(now() - file.ctime).days.round(0)"
```

**缺少空值检查**：属性可能并非在所有笔记中都存在。使用 `if()` 做守卫。

```yaml
# 错误 - 如果 due_date 为空会崩溃
"(date(due_date) - today()).days"

# 正确 - 用 if() 守卫
'if(due_date, (date(due_date) - today()).days, "")'
```

**引用未定义的公式**：确保 `order` 或 `properties` 中每个 `formula.X` 在 `formulas` 中都有对应定义。

```yaml
# 如果 'total' 未在 formulas 中定义，会静默失败
order:
  - formula.total

# 修复：定义它
formulas:
  total: "price * quantity"
```

## 参考

- [Bases 语法](https://help.obsidian.md/bases/syntax)
- [函数](https://help.obsidian.md/bases/functions)
- [视图](https://help.obsidian.md/bases/views)
- [公式](https://help.obsidian.md/formulas)
- [完整函数参考](references/FUNCTIONS_REFERENCE.md)
