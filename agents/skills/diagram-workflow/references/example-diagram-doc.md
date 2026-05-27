# 图形方法示例

## 目的

这份示例展示的是：一个图文档应该怎么组织，才适合后续反复维护。

## 文件对

- `examples/26-05-03_diagram-workflow-overview.puml`
- `examples/26-05-03_diagram-workflow-overview.md`

## 文档结构

```markdown
# 图文档标题

## 1. 说明
[一句话说明这张图回答什么问题]

Source: examples/26-05-03_diagram-workflow-overview.puml

## 2. ASCII 图
[最终展示 ASCII 图；复杂图可为手工维护版本]

## 3. 备注
[必要时补少量说明或表格]
```

## 带正文时的更新方式

如果 `.md` 同时包含展示图、正文分析、分节说明或表格，更新时按下面方式处理：

````markdown
# 模块接入点说明

## 1. 背景
[这里是人工维护的正文，不因图更新而整段重写]

## 2. 当前结构图
Source: diagrams/module-entry.puml

```text
[这里只替换当前图块]
```

## 3. 接入点说明
[这里是人工维护的说明、约束或表格，默认保留]
````

这种文档在图更新时，只替换 `## 2. 当前结构图` 下的 `Source:` 和 ASCII 图代码块，不整份覆盖。

## 示例规则

- `.puml` 源文件要和 `.md` 展示文档放在一起，便于同步维护
- 只要调用这个 skill 修改图，就默认同时更新 `.puml` 和 `.md`，不要只改源图不改 text/ASCII 图
- 复杂图默认手工维护 ASCII，不把 PlantUML ASCII 自动输出直接作为最终展示
- 只要 `.puml` 改了，就要回看 `.md` 中的 ASCII 图是否仍然准确
- 纯图展示文档可以整份刷新；带正文的图文档只替换图块和必要的 `Source:` 行
- 不要先写展示图，再倒着猜源文件
- 如果别人看不懂 ASCII，先判断是不是该改成手工 ASCII，而不是默认继续重渲染
