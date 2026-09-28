@echo off
rem 便捷启动 dsh-tui 配置（Windows，默认 high 推理等级）。
rem 安装：将本文件与同目录的 dst-effort-high.yml 一起复制到 %USERPROFILE%\.local\bin 并加入 PATH。
rem 说明：默认档由 dsh-tui bundle 的 `effort: max` 钉死（优先级高于持久化的 /effort 选择），
rem      这里用 --patch 覆盖为 high；会话内 /effort 仍可临时改档。
setlocal
set "DST_PATCH=%~dp0dst-effort-high.yml"
if not exist "%DST_PATCH%" (
  echo dst: 未找到 "%DST_PATCH%"，按 dsh-tui 默认推理等级启动 1>&2
  dsh --profile dsh-tui %*
) else (
  dsh --profile dsh-tui --patch "%DST_PATCH%" %*
)
