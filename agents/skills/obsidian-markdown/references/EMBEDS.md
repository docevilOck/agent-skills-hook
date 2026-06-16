# Embeds 参考

## 嵌入笔记

```markdown
![[笔记名]]
![[笔记名#标题]]
![[笔记名#^block-id]]
```

## 嵌入图片

```markdown
![[image.png]]
![[image.png|640x480]]    宽 x 高
![[image.png|300]]        仅指定宽度（保持宽高比）
```

## 外部图片

```markdown
![替代文本](https://example.com/image.png)
![替代文本|300](https://example.com/image.png)
```

## 嵌入音频

```markdown
![[audio.mp3]]
![[audio.ogg]]
```

## 嵌入 PDF

```markdown
![[document.pdf]]
![[document.pdf#page=3]]
![[document.pdf#height=400]]
```

## 嵌入 Base

```markdown
![[BaseFile.base]]
![[BaseFile.base#视图名称]]
```

## 嵌入列表

```markdown
![[笔记名#^list-id]]
```

其中列表带有块 ID：

```markdown
- 项目 1
- 项目 2
- 项目 3

^list-id
```

## 嵌入搜索结果

````markdown
```query
tag:#project status:done
```
````
