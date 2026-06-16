---
name: json-canvas
description: 创建和编辑 JSON Canvas 文件（.canvas），支持节点、边、分组和连接。当处理 .canvas 文件、创建可视化画布、思维导图、流程图，或用户提到 Obsidian 中的 Canvas 文件时使用。
---

# JSON Canvas 技能

## 文件结构

Canvas 文件（`.canvas`）包含两个顶层数组，遵循 [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)：

```json
{
  "nodes": [],
  "edges": []
}
```

- `nodes`（可选）：节点对象数组
- `edges`（可选）：连接节点的边对象数组

## 常见工作流

### 1. 创建新 Canvas

1. 创建一个 `.canvas` 文件，基础结构为 `{"nodes": [], "edges": []}`
2. 为每个节点生成唯一的 16 位十六进制 ID（如 `"6f0ad84f44ce9c17"`）
3. 添加节点，必填字段：`id`、`type`、`x`、`y`、`width`、`height`
4. 通过 `fromNode` 和 `toNode` 引用有效节点 ID 来添加边
5. **验证**：解析 JSON 确认其有效性。验证所有 `fromNode`/`toNode` 值在 nodes 数组中存在

### 2. 向已有 Canvas 添加节点

1. 读取并解析现有 `.canvas` 文件
2. 生成不与已有节点或边 ID 冲突的唯一 ID
3. 选择位置（`x`、`y`），避免与已有节点重叠（留出 50-100px 间距）
4. 将新节点对象追加到 `nodes` 数组
5. 可选：添加连接新节点与已有节点的边
6. **验证**：确认所有 ID 唯一，所有边引用指向已存在的节点

### 3. 连接两个节点

1. 确定源节点和目标节点的 ID
2. 生成唯一的边 ID
3. 设置 `fromNode` 和 `toNode` 为源和目标 ID
4. 可选：设置 `fromSide`/`toSide`（top、right、bottom、left）指定锚点
5. 可选：设置 `label` 为边添加描述文字
6. 将边追加到 `edges` 数组
7. **验证**：确认 `fromNode` 和 `toNode` 均引用已存在的节点 ID

### 4. 编辑已有 Canvas

1. 读取并解析 `.canvas` 文件为 JSON
2. 通过 `id` 定位目标节点或边
3. 修改所需属性（文本、位置、颜色等）
4. 将更新后的 JSON 写回文件
5. **验证**：编辑后重新检查所有 ID 唯一性和边引用完整性

## 节点（Nodes）

节点是放置在画布上的对象。数组顺序决定 z-index：第一个节点 = 底层，最后一个节点 = 顶层。

### 通用节点属性

| 属性 | 必填 | 类型 | 描述 |
|------|------|------|------|
| `id` | 是 | string | 唯一的 16 位十六进制标识符 |
| `type` | 是 | string | `text`、`file`、`link` 或 `group` |
| `x` | 是 | integer | X 坐标（像素） |
| `y` | 是 | integer | Y 坐标（像素） |
| `width` | 是 | integer | 宽度（像素） |
| `height` | 是 | integer | 高度（像素） |
| `color` | 否 | canvasColor | 预设 `"1"`-`"6"` 或十六进制颜色（如 `"#FF0000"`） |

### 文本节点（Text Nodes）

| 属性 | 必填 | 类型 | 描述 |
|------|------|------|------|
| `text` | 是 | string | 支持 Markdown 语法的纯文本 |

```json
{
  "id": "6f0ad84f44ce9c17",
  "type": "text",
  "x": 0,
  "y": 0,
  "width": 400,
  "height": 200,
  "text": "# Hello World\n\n这是 **Markdown** 内容。"
}
```

**换行陷阱**：在 JSON 字符串中使用 `\n` 表示换行。**不要**使用字面量的 `\\n`——Obsidian 会将其渲染为字符 `\` 和 `n`。

### 文件节点（File Nodes）

| 属性 | 必填 | 类型 | 描述 |
|------|------|------|------|
| `file` | 是 | string | 系统内文件路径 |
| `subpath` | 否 | string | 指向标题或块的链接（以 `#` 开头） |

```json
{
  "id": "a1b2c3d4e5f67890",
  "type": "file",
  "x": 500,
  "y": 0,
  "width": 400,
  "height": 300,
  "file": "Attachments/diagram.png"
}
```

### 链接节点（Link Nodes）

| 属性 | 必填 | 类型 | 描述 |
|------|------|------|------|
| `url` | 是 | string | 外部 URL |

```json
{
  "id": "c3d4e5f678901234",
  "type": "link",
  "x": 1000,
  "y": 0,
  "width": 400,
  "height": 200,
  "url": "https://obsidian.md"
}
```

### 分组节点（Group Nodes）

分组是用于组织其他节点的可视化容器。将子节点放置在分组的边界内。

| 属性 | 必填 | 类型 | 描述 |
|------|------|------|------|
| `label` | 否 | string | 分组的文本标签 |
| `background` | 否 | string | 背景图片路径 |
| `backgroundStyle` | 否 | string | `cover`、`ratio` 或 `repeat` |

```json
{
  "id": "d4e5f6789012345a",
  "type": "group",
  "x": -50,
  "y": -50,
  "width": 1000,
  "height": 600,
  "label": "项目概览",
  "color": "4"
}
```

## 边（Edges）

边通过 `fromNode` 和 `toNode` ID 连接节点。

| 属性 | 必填 | 类型 | 默认值 | 描述 |
|------|------|------|--------|------|
| `id` | 是 | string | - | 唯一标识符 |
| `fromNode` | 是 | string | - | 源节点 ID |
| `fromSide` | 否 | string | - | `top`、`right`、`bottom` 或 `left` |
| `fromEnd` | 否 | string | `none` | `none` 或 `arrow` |
| `toNode` | 是 | string | - | 目标节点 ID |
| `toSide` | 否 | string | - | `top`、`right`、`bottom` 或 `left` |
| `toEnd` | 否 | string | `arrow` | `none` 或 `arrow` |
| `color` | 否 | canvasColor | - | 线条颜色 |
| `label` | 否 | string | - | 文本标签 |

```json
{
  "id": "0123456789abcdef",
  "fromNode": "6f0ad84f44ce9c17",
  "fromSide": "right",
  "toNode": "a1b2c3d4e5f67890",
  "toSide": "left",
  "toEnd": "arrow",
  "label": "指向"
}
```

## 颜色

`canvasColor` 类型接受十六进制字符串或预设编号：

| 预设 | 颜色 |
|------|------|
| `"1"` | 红色 |
| `"2"` | 橙色 |
| `"3"` | 黄色 |
| `"4"` | 绿色 |
| `"5"` | 青色 |
| `"6"` | 紫色 |

预设颜色值有意不定义具体色值——各应用使用自己的品牌颜色。

## ID 生成

生成 16 位小写十六进制字符串（64 位随机值）：

```
"6f0ad84f44ce9c17"
"a3b2c1d0e9f8a7b6"
```

## 布局指南

- 坐标可以为负数（画布无限延伸）
- `x` 向右递增，`y` 向下递增；坐标位置为左上角
- 节点之间留 50-100px 间距；分组内部留 20-50px 内边距
- 对齐到网格（10 或 20 的倍数）以获得更整洁的布局

| 节点类型 | 建议宽度 | 建议高度 |
|---------|---------|---------|
| 小文本 | 200-300 | 80-150 |
| 中文本 | 300-450 | 150-300 |
| 大文本 | 400-600 | 300-500 |
| 文件预览 | 300-500 | 200-400 |
| 链接预览 | 250-400 | 100-200 |

## 验证清单

创建或编辑 canvas 文件后，验证以下内容：

1. 所有 `id` 值在节点和边中全局唯一
2. 每个 `fromNode` 和 `toNode` 引用已存在的节点 ID
3. 每种节点类型的必填字段均已填写（文本节点需要 `text`，文件节点需要 `file`，链接节点需要 `url`）
4. `type` 为以下之一：`text`、`file`、`link`、`group`
5. `fromSide`/`toSide` 值为以下之一：`top`、`right`、`bottom`、`left`
6. `fromEnd`/`toEnd` 值为以下之一：`none`、`arrow`
7. 颜色预设为 `"1"` 到 `"6"` 或有效十六进制值（如 `"#FF0000"`）
8. JSON 合法且可解析

如果验证失败，检查是否存在重复 ID、悬空边引用或格式错误的 JSON 字符串（特别是文本内容中未转义的换行符）。

## 完整示例

完整的 canvas 示例（思维导图、项目看板、研究画布、流程图）参见 [references/EXAMPLES.md](references/EXAMPLES.md)。

## 参考

- [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)
- [JSON Canvas GitHub](https://github.com/obsidianmd/jsoncanvas)
