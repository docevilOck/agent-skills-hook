---
name: obsidian-cli
description: 使用 Obsidian CLI 与 Obsidian vault 交互，包括读取、创建、搜索和管理笔记、任务、属性等。同时支持插件和主题开发，包括重载插件、运行 JavaScript、捕获错误、截图和检查 DOM 等命令。当用户要求与 Obsidian vault 交互、管理笔记、搜索 vault 内容、从命令行执行 vault 操作，或开发和调试 Obsidian 插件/主题时使用。
---

# Obsidian CLI

使用 `obsidian` CLI 与正在运行的 Obsidian 实例交互。需要 Obsidian 处于打开状态。

## 命令参考

运行 `obsidian help` 查看所有可用命令。此命令始终是最新的。完整文档：https://help.obsidian.md/cli

## 语法

**参数**（Parameters）使用 `=` 传值。含空格的值需要加引号：

```bash
obsidian create name="My Note" content="Hello world"
```

**标志**（Flags）是不带值的布尔开关：

```bash
obsidian create name="My Note" silent overwrite
```

多行内容使用 `\n` 换行，`\t` 缩进。

## 文件定位

许多命令接受 `file` 或 `path` 来定位文件。不指定时，使用当前活动文件。

- `file=<name>` — 像 wikilink 一样解析（仅文件名，无需路径或扩展名）
- `path=<path>` — vault 根目录下的精确路径，如 `folder/note.md`

## Vault 定位

命令默认定位到最近聚焦的 vault。使用 `vault=<name>` 作为第一个参数来指定特定 vault：

```bash
obsidian vault="My Vault" search query="test"
```

## 常用模式

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

在任何命令上使用 `--copy` 可将输出复制到剪贴板。使用 `silent` 阻止文件自动打开。在列表命令上使用 `total` 获取计数。

## 插件开发

### 开发/测试循环

对插件或主题进行代码修改后，遵循以下工作流：

1. **重载**插件以加载更改：
   ```bash
   obsidian plugin:reload id=my-plugin
   ```
2. **检查错误** — 如果出现错误，修复后从第 1 步重新开始：
   ```bash
   obsidian dev:errors
   ```
3. **可视化验证**，通过截图或 DOM 检查：
   ```bash
   obsidian dev:screenshot path=screenshot.png
   obsidian dev:dom selector=".workspace-leaf" text
   ```
4. **检查控制台输出**，查看警告或异常日志：
   ```bash
   obsidian dev:console level=error
   ```

### 其他开发者命令

在应用上下文中运行 JavaScript：

```bash
obsidian eval code="app.vault.getFiles().length"
```

检查 CSS 值：

```bash
obsidian dev:css selector=".workspace-leaf" prop=background-color
```

切换移动端模拟：

```bash
obsidian dev:mobile on
```

运行 `obsidian help` 查看其他开发者命令，包括 CDP 和调试器控制。
