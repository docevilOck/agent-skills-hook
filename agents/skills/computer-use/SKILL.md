---
name: computer-use
description: Control the Windows desktop like a human — screenshot the screen or a window, list/activate windows, move/click/drag the mouse, scroll, type text and send hotkeys. Use when the user asks to "看屏幕"、"截个图点一下"、操作某个桌面软件（如 QMT 交易端、Excel、ERP 客户端）、点击/输入/拖拽界面元素、或任何需要 GUI 自动化而浏览器自动化（agent-browser）不适用的场景。
---

# computer-use (Windows)

## 工具入口

> **强制**：本 skill 提供下列唯一脚本，必须直接调用，禁止另写截图/鼠标/键盘代码。

```
pwsh -NoProfile -ExecutionPolicy Bypass -File "C:\Users\hasee\.dsh\skills\computer-use\scripts\cu.ps1" <action> [参数]
```

所有输出为单行 JSON；失败时输出 `{"error":"..."}` 且退出码 1。

## 核心循环

1. `info` → 拿屏幕物理尺寸、DPI、光标位置
2. `shot` → 截图，把返回的 `path` 交给 `read_image` 看
3. 决定坐标 → `activate` / `click` / `type` / `hotkey`
4. **再截一次图确认结果**（不要凭想象宣布成功）

## 坐标规则（最容易踩的坑）

- 脚本内部已 `SetProcessDPIAware`，**所有坐标都是物理像素**。
- 本机 DPI 150%：主屏物理 2560×1440，副屏 2560×1600 且在负坐标（x 从 -2560 起）。
- `read_image` 会把图缩小。取模型看到的图宽 `wi`，截图返回的 `w`，则
  **物理坐标 = 图上坐标 × (w / wi)**。算错就一定点歪。
- 拿不准就用 `shot -Hwnd <hwnd>` 只截该窗口，比例最简单。

## 动作速查

| 目的 | 命令 |
|---|---|
| 环境信息 | `info` |
| 截全屏 / 区域 / 窗口 | `shot` / `shot -X 0 -Y 0 -W 800 -H 600` / `shot -Hwnd 1234` || 列窗口 | `windows -Filter QMT`（加 `-All` 看全部） |
| 前置窗口 | `activate -Title QMT` 或 `-Hwnd 1234` |
| 移动 / 点击 / 双击 / 右键 | `move -X -Y` / `click -X -Y` / `click -X -Y -Double` / `click -Button right` |
| 拖拽 | `drag -X1 100 -Y1 200 -X2 500 -Y2 600` |
| 滚动 | `scroll -Delta -360 -Times 3`（负=向下） |
| 输入文本 | `type -Text "600519"`（中文可用，走 Unicode 注入） |
| 按键 | `key -Name ENTER -Times 2`（ENTER/TAB/ESC/F1..F12/A..Z/UP/DOWN/…） |
| 组合键 | `hotkey -Keys "CTRL+S"`、`"CTRL+SHIFT+ESC"`、`"ALT+F4"` |
| 自检 | `selftest`（弹一个测试窗口，验证点击坐标与输入） |

## 窗口截图

`shot -Hwnd` 优先用 `PrintWindow`（返回 `mode:"printwindow"`），**被遮挡的窗口也能截到内容**；失败时自动退回屏幕区域抓取（`mode:"screen"`，此时拿到的是该位置最上层的画面）。截图失败或全黑就以 `activate` 把窗口提到前台再截。

## 操作铁律

- **破坏性/不可逆动作必须先问**：下单、撤单、转账、删除、确认保存、关闭未保存文档。截图给用户看，说明要点哪里，等确认。
- 交易类界面（QMT/券商客户端）默认只读探索；涉及资金的操作永远先确认。
- 输入密码前停下，让用户自己敲；不要 `type` 密码。
- 点之前先 `activate` 目标窗口，否则点到的是别的窗口。
- 每步之间给界面留时间：脚本内部已带 60~250ms 等待，复杂界面自己再 `Start-Sleep`。
- 找不到元素时优先换思路：`windows` 找窗口 → `activate` → `hotkey` 走键盘路径（比找像素稳）。

## 适用边界

- 浏览器内的自动化优先用 `agent-browser`（有 DOM、更稳）；本 skill 用于**桌面客户端**。
- 本 skill 不做 OCR/元素识别，靠 `read_image` 的视觉判断。
- 不接管已在前台的输入法状态：中文输入建议直接 `type`（Unicode 注入绕过输入法）。
- 需要管理员权限的窗口（UAC 弹窗）点不到，需用户手动确认。

## 验证

改脚本或换机器后跑一次 `selftest`，`pass:true` 才算环境可用。
