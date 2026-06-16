# 属性（Frontmatter）参考

属性使用位于笔记开头的 YAML frontmatter：

```yaml
---
title: 我的笔记标题
date: 2024-01-15
tags:
  - project
  - important
aliases:
  - 我的笔记
  - 替代名称
cssclasses:
  - custom-class
status: in-progress
rating: 4.5
completed: false
due: 2024-02-01T14:30:00
---
```

## 属性类型

| 类型 | 示例 |
|------|------|
| 文本（Text） | `title: 我的标题` |
| 数值（Number） | `rating: 4.5` |
| 复选框（Checkbox） | `completed: true` |
| 日期（Date） | `date: 2024-01-15` |
| 日期时间（Date & Time） | `due: 2024-01-15T14:30:00` |
| 列表（List） | `tags: [one, two]` 或 YAML 列表格式 |
| 链接（Links） | `related: "[[其他笔记]]"` |

## 默认属性

- `tags` - 笔记标签（可搜索，在图谱视图中显示）
- `aliases` - 笔记的替代名称（用于链接建议）
- `cssclasses` - 应用于笔记在阅读/编辑视图中的 CSS 类

## 标签（Tags）

```markdown
#tag
#nested/tag
#tag-with-dashes
#tag_with_underscores
```

标签可包含：字母（任意语言）、数字（不能作为首字符）、下划线 `_`、连字符 `-`、正斜杠 `/`（用于嵌套）。

在 frontmatter 中：

```yaml
---
tags:
  - tag1
  - nested/tag2
---
```
