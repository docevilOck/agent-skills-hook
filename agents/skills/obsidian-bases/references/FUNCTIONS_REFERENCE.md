# 函数参考

## 全局函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `date()` | `date(string): date` | 将字符串解析为日期。格式：`YYYY-MM-DD HH:mm:ss` |
| `duration()` | `duration(string): duration` | 解析时长字符串 |
| `now()` | `now(): date` | 当前日期和时间 |
| `today()` | `today(): date` | 当前日期（时间 = 00:00:00） |
| `if()` | `if(condition, trueResult, falseResult?)` | 条件判断 |
| `min()` | `min(n1, n2, ...): number` | 最小值 |
| `max()` | `max(n1, n2, ...): number` | 最大值 |
| `number()` | `number(any): number` | 转换为数值 |
| `link()` | `link(path, display?): Link` | 创建链接 |
| `list()` | `list(element): List` | 若非列表则包装为列表 |
| `file()` | `file(path): file` | 获取文件对象 |
| `image()` | `image(path): image` | 创建可渲染图片 |
| `icon()` | `icon(name): icon` | 按名称获取 Lucide 图标 |
| `html()` | `html(string): html` | 渲染为 HTML |
| `escapeHTML()` | `escapeHTML(string): string` | 转义 HTML 字符 |

## Any 类型函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `isTruthy()` | `any.isTruthy(): boolean` | 强制转换为布尔值 |
| `isType()` | `any.isType(type): boolean` | 检查类型 |
| `toString()` | `any.toString(): string` | 转换为字符串 |

## Date 函数与字段

**字段：** `date.year`、`date.month`、`date.day`、`date.hour`、`date.minute`、`date.second`、`date.millisecond`

| 函数 | 签名 | 描述 |
|------|------|------|
| `date()` | `date.date(): date` | 去除时间部分 |
| `format()` | `date.format(string): string` | 使用 Moment.js 模式格式化 |
| `time()` | `date.time(): string` | 获取时间字符串 |
| `relative()` | `date.relative(): string` | 人类可读的相对时间 |
| `isEmpty()` | `date.isEmpty(): boolean` | 对日期始终返回 false |

## Duration 类型

两个日期相减时，结果是 **Duration** 类型（不是数值）。Duration 有自己的属性和方法。

**Duration 字段：**
| 字段 | 类型 | 描述 |
|------|------|------|
| `duration.days` | Number | 时长中的总天数 |
| `duration.hours` | Number | 时长中的总小时数 |
| `duration.minutes` | Number | 时长中的总分钟数 |
| `duration.seconds` | Number | 时长中的总秒数 |
| `duration.milliseconds` | Number | 时长中的总毫秒数 |

**重要：** Duration 不直接支持 `.round()`、`.floor()`、`.ceil()`。必须先访问数值字段（如 `.days`），然后再应用数值函数。

```yaml
# 正确：计算两个日期之间的天数
"(date(due_date) - today()).days"                    # 返回天数
"(now() - file.ctime).days"                          # 自创建以来的天数

# 正确：如需四舍五入，对数值结果操作
"(date(due_date) - today()).days.round(0)"           # 四舍五入天数
"(now() - file.ctime).hours.round(0)"                # 四舍五入小时数

# 错误 - 会导致报错：
# "((date(due) - today()) / 86400000).round(0)"      # Duration 不支持除法后再 round
```

## 日期运算

```yaml
# 时长单位：y/year/years、M/month/months、d/day/days、
#           w/week/weeks、h/hour/hours、m/minute/minutes、s/second/seconds

# 加减时长
"date + \"1M\""           # 加 1 个月
"date - \"2h\""           # 减 2 小时
"now() + \"1 day\""       # 明天
"today() + \"7d\""        # 一周后

# 日期相减返回 Duration 类型
"now() - file.ctime"                    # 返回 Duration
"(now() - file.ctime).days"             # 以天数形式获取
"(now() - file.ctime).hours"            # 以小时数形式获取

# 复杂时长运算
"now() + (duration('1d') * 2)"
```

## String 函数

**字段：** `string.length`

| 函数 | 签名 | 描述 |
|------|------|------|
| `contains()` | `string.contains(value): boolean` | 检查子串 |
| `containsAll()` | `string.containsAll(...values): boolean` | 所有子串均存在 |
| `containsAny()` | `string.containsAny(...values): boolean` | 任一子串存在 |
| `startsWith()` | `string.startsWith(query): boolean` | 以 query 开头 |
| `endsWith()` | `string.endsWith(query): boolean` | 以 query 结尾 |
| `isEmpty()` | `string.isEmpty(): boolean` | 为空或不存在 |
| `lower()` | `string.lower(): string` | 转为小写 |
| `title()` | `string.title(): string` | 转为首字母大写 |
| `trim()` | `string.trim(): string` | 去除空白字符 |
| `replace()` | `string.replace(pattern, replacement): string` | 替换模式 |
| `repeat()` | `string.repeat(count): string` | 重复字符串 |
| `reverse()` | `string.reverse(): string` | 反转字符串 |
| `slice()` | `string.slice(start, end?): string` | 截取子串 |
| `split()` | `string.split(separator, n?): list` | 分割为列表 |

## Number 函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `abs()` | `number.abs(): number` | 绝对值 |
| `ceil()` | `number.ceil(): number` | 向上取整 |
| `floor()` | `number.floor(): number` | 向下取整 |
| `round()` | `number.round(digits?): number` | 四舍五入到指定位数 |
| `toFixed()` | `number.toFixed(precision): string` | 定点表示法 |
| `isEmpty()` | `number.isEmpty(): boolean` | 不存在 |

## List 函数

**字段：** `list.length`

| 函数 | 签名 | 描述 |
|------|------|------|
| `contains()` | `list.contains(value): boolean` | 元素存在 |
| `containsAll()` | `list.containsAll(...values): boolean` | 所有元素均存在 |
| `containsAny()` | `list.containsAny(...values): boolean` | 任一元素存在 |
| `filter()` | `list.filter(expression): list` | 按条件过滤（使用 `value`、`index`） |
| `map()` | `list.map(expression): list` | 转换元素（使用 `value`、`index`） |
| `reduce()` | `list.reduce(expression, initial): any` | 归约为单个值（使用 `value`、`index`、`acc`） |
| `flat()` | `list.flat(): list` | 展平嵌套列表 |
| `join()` | `list.join(separator): string` | 连接为字符串 |
| `reverse()` | `list.reverse(): list` | 反转顺序 |
| `slice()` | `list.slice(start, end?): list` | 截取子列表 |
| `sort()` | `list.sort(): list` | 升序排序 |
| `unique()` | `list.unique(): list` | 去除重复 |
| `isEmpty()` | `list.isEmpty(): boolean` | 无元素 |

## File 函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `asLink()` | `file.asLink(display?): Link` | 转换为链接 |
| `hasLink()` | `file.hasLink(otherFile): boolean` | 包含指向文件的链接 |
| `hasTag()` | `file.hasTag(...tags): boolean` | 包含任一标签 |
| `hasProperty()` | `file.hasProperty(name): boolean` | 包含属性 |
| `inFolder()` | `file.inFolder(folder): boolean` | 位于文件夹或其子文件夹中 |

## Link 函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `asFile()` | `link.asFile(): file` | 获取文件对象 |
| `linksTo()` | `link.linksTo(file): boolean` | 链接指向该文件 |

## Object 函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `isEmpty()` | `object.isEmpty(): boolean` | 无属性 |
| `keys()` | `object.keys(): list` | 键列表 |
| `values()` | `object.values(): list` | 值列表 |

## 正则表达式函数

| 函数 | 签名 | 描述 |
|------|------|------|
| `matches()` | `regexp.matches(string): boolean` | 测试是否匹配 |
