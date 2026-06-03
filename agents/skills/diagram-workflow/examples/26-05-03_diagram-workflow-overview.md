# 图形方法示例

说明：展示 diagram-workflow 的工作流程，直接手写 ASCII 到 `.md`。

```text
                                    Diagram Workflow Overview

         ,-.
         `-'
         /|\
          |               ,----------------.          ,-------------.
         / \              |diagram-workflow|          |  final .md  |
      Developer           `-------+--------'          `------+------'
          |   request diagram     |                          |
          |---------------------->|                          |
          |                       |                          |
          |                       |----.                     |
          |                       |    | choose diagram type |
          |                       |<---'                     |
          |                       |                          |
          |                       |   hand-draw ASCII        |
          |                       |------------------------->|
          |                       |                          |
          |  review and refine    |                          |
          |<- - - - - - - - - - - |                          |
      Developer           ,-------+--------.          ,------+------.
         ,-.              |diagram-workflow|          |  final .md  |
         `-'              `----------------'          `-------------'
         /|\
          |
         / \
```
