# JSON Canvas 完整示例

## 带文本和连线的简单 Canvas

```json
{
  "nodes": [
    {
      "id": "8a9b0c1d2e3f4a5b",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 300,
      "height": 150,
      "text": "# 核心概念\n\n这是中心思想。"
    },
    {
      "id": "1a2b3c4d5e6f7a8b",
      "type": "text",
      "x": 400,
      "y": -100,
      "width": 250,
      "height": 100,
      "text": "## 支撑论点 A\n\n详细内容。"
    },
    {
      "id": "2b3c4d5e6f7a8b9c",
      "type": "text",
      "x": 400,
      "y": 100,
      "width": 250,
      "height": 100,
      "text": "## 支撑论点 B\n\n更多细节。"
    }
  ],
  "edges": [
    {
      "id": "3c4d5e6f7a8b9c0d",
      "fromNode": "8a9b0c1d2e3f4a5b",
      "fromSide": "right",
      "toNode": "1a2b3c4d5e6f7a8b",
      "toSide": "left"
    },
    {
      "id": "4d5e6f7a8b9c0d1e",
      "fromNode": "8a9b0c1d2e3f4a5b",
      "fromSide": "right",
      "toNode": "2b3c4d5e6f7a8b9c",
      "toSide": "left"
    }
  ]
}
```

## 带分组节点的项目看板

```json
{
  "nodes": [
    {
      "id": "5e6f7a8b9c0d1e2f",
      "type": "group",
      "x": 0,
      "y": 0,
      "width": 300,
      "height": 500,
      "label": "待办",
      "color": "1"
    },
    {
      "id": "6f7a8b9c0d1e2f3a",
      "type": "group",
      "x": 350,
      "y": 0,
      "width": 300,
      "height": 500,
      "label": "进行中",
      "color": "3"
    },
    {
      "id": "7a8b9c0d1e2f3a4b",
      "type": "group",
      "x": 700,
      "y": 0,
      "width": 300,
      "height": 500,
      "label": "已完成",
      "color": "4"
    },
    {
      "id": "8b9c0d1e2f3a4b5c",
      "type": "text",
      "x": 20,
      "y": 50,
      "width": 260,
      "height": 80,
      "text": "## 任务 1\n\n实现功能 X"
    },
    {
      "id": "9c0d1e2f3a4b5c6d",
      "type": "text",
      "x": 370,
      "y": 50,
      "width": 260,
      "height": 80,
      "text": "## 任务 2\n\n审查 PR #123",
      "color": "2"
    },
    {
      "id": "0d1e2f3a4b5c6d7e",
      "type": "text",
      "x": 720,
      "y": 50,
      "width": 260,
      "height": 80,
      "text": "## 任务 3\n\n~~配置 CI/CD~~"
    }
  ],
  "edges": []
}
```

## 带文件和链接的研究画布

```json
{
  "nodes": [
    {
      "id": "1e2f3a4b5c6d7e8f",
      "type": "text",
      "x": 300,
      "y": 200,
      "width": 400,
      "height": 200,
      "text": "# 研究课题\n\n## 关键问题\n\n- X 如何影响 Y？\n- 有什么影响？",
      "color": "5"
    },
    {
      "id": "2f3a4b5c6d7e8f9a",
      "type": "file",
      "x": 0,
      "y": 0,
      "width": 250,
      "height": 150,
      "file": "Literature/Paper A.pdf"
    },
    {
      "id": "3a4b5c6d7e8f9a0b",
      "type": "file",
      "x": 0,
      "y": 200,
      "width": 250,
      "height": 150,
      "file": "Notes/Meeting Notes.md",
      "subpath": "#Key Insights"
    },
    {
      "id": "4b5c6d7e8f9a0b1c",
      "type": "link",
      "x": 0,
      "y": 400,
      "width": 250,
      "height": 100,
      "url": "https://example.com/research"
    },
    {
      "id": "5c6d7e8f9a0b1c2d",
      "type": "file",
      "x": 750,
      "y": 150,
      "width": 300,
      "height": 250,
      "file": "Attachments/diagram.png"
    }
  ],
  "edges": [
    {
      "id": "6d7e8f9a0b1c2d3e",
      "fromNode": "2f3a4b5c6d7e8f9a",
      "fromSide": "right",
      "toNode": "1e2f3a4b5c6d7e8f",
      "toSide": "left",
      "label": "支撑"
    },
    {
      "id": "7e8f9a0b1c2d3e4f",
      "fromNode": "3a4b5c6d7e8f9a0b",
      "fromSide": "right",
      "toNode": "1e2f3a4b5c6d7e8f",
      "toSide": "left",
      "label": "提供信息"
    },
    {
      "id": "8f9a0b1c2d3e4f5a",
      "fromNode": "4b5c6d7e8f9a0b1c",
      "fromSide": "right",
      "toNode": "1e2f3a4b5c6d7e8f",
      "toSide": "left",
      "toEnd": "arrow",
      "color": "6"
    },
    {
      "id": "9a0b1c2d3e4f5a6b",
      "fromNode": "1e2f3a4b5c6d7e8f",
      "fromSide": "right",
      "toNode": "5c6d7e8f9a0b1c2d",
      "toSide": "left",
      "label": "可视化方式"
    }
  ]
}
```

## 流程图

```json
{
  "nodes": [
    {
      "id": "a0b1c2d3e4f5a6b7",
      "type": "text",
      "x": 200,
      "y": 0,
      "width": 150,
      "height": 60,
      "text": "**开始**",
      "color": "4"
    },
    {
      "id": "b1c2d3e4f5a6b7c8",
      "type": "text",
      "x": 200,
      "y": 100,
      "width": 150,
      "height": 60,
      "text": "步骤 1:\n收集数据"
    },
    {
      "id": "c2d3e4f5a6b7c8d9",
      "type": "text",
      "x": 200,
      "y": 200,
      "width": 150,
      "height": 80,
      "text": "**判断**\n\n数据是否有效？",
      "color": "3"
    },
    {
      "id": "d3e4f5a6b7c8d9e0",
      "type": "text",
      "x": 400,
      "y": 200,
      "width": 150,
      "height": 60,
      "text": "处理数据"
    },
    {
      "id": "e4f5a6b7c8d9e0f1",
      "type": "text",
      "x": 0,
      "y": 200,
      "width": 150,
      "height": 60,
      "text": "重新获取数据",
      "color": "1"
    },
    {
      "id": "f5a6b7c8d9e0f1a2",
      "type": "text",
      "x": 400,
      "y": 320,
      "width": 150,
      "height": 60,
      "text": "**结束**",
      "color": "4"
    }
  ],
  "edges": [
    {
      "id": "a6b7c8d9e0f1a2b3",
      "fromNode": "a0b1c2d3e4f5a6b7",
      "fromSide": "bottom",
      "toNode": "b1c2d3e4f5a6b7c8",
      "toSide": "top"
    },
    {
      "id": "b7c8d9e0f1a2b3c4",
      "fromNode": "b1c2d3e4f5a6b7c8",
      "fromSide": "bottom",
      "toNode": "c2d3e4f5a6b7c8d9",
      "toSide": "top"
    },
    {
      "id": "c8d9e0f1a2b3c4d5",
      "fromNode": "c2d3e4f5a6b7c8d9",
      "fromSide": "right",
      "toNode": "d3e4f5a6b7c8d9e0",
      "toSide": "left",
      "label": "是",
      "color": "4"
    },
    {
      "id": "d9e0f1a2b3c4d5e6",
      "fromNode": "c2d3e4f5a6b7c8d9",
      "fromSide": "left",
      "toNode": "e4f5a6b7c8d9e0f1",
      "toSide": "right",
      "label": "否",
      "color": "1"
    },
    {
      "id": "e0f1a2b3c4d5e6f7",
      "fromNode": "e4f5a6b7c8d9e0f1",
      "fromSide": "top",
      "fromEnd": "none",
      "toNode": "b1c2d3e4f5a6b7c8",
      "toSide": "left",
      "toEnd": "arrow"
    },
    {
      "id": "f1a2b3c4d5e6f7a8",
      "fromNode": "d3e4f5a6b7c8d9e0",
      "fromSide": "bottom",
      "toNode": "f5a6b7c8d9e0f1a2",
      "toSide": "top"
    }
  ]
}
```
