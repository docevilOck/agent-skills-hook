# ==============================================================================
# deploy-rtk.ps1
# 为 agent-skills-hook 仓库中所有 agent 工具安装 rtk (Rust Token Killer)
#
# 用法:
#   .\scripts\deploy-rtk.ps1                    # 部署全部工具
#   .\scripts\deploy-rtk.ps1 -DryRun            # 仅检查，不修改
#   .\scripts\deploy-rtk.ps1 -Tool claude       # 仅部署 Claude Code
#   .\scripts\deploy-rtk.ps1 -Tool opencode     # 仅部署 OpenCode
#   .\scripts\deploy-rtk.ps1 -Tool codex        # 仅部署 Codex CLI
#
# Windows: rtk hook 模式不支持 → 使用项目本地模式 (rtk init)，AI 手动加 rtk 前缀
# Unix:    使用 rtk init -g 全局 hook 模式，命令自动改写
#
# 所有操作均为幂等 — 已配置则跳过。
# rtk 是一个 Rust 二进制，在 shell 命令到达 LLM 上下文前压缩输出 (节省 60-90% token)。
# ==============================================================================

param(
    [switch]$DryRun,
    [ValidateSet("claude", "opencode", "codex")]
    [string]$Tool = ""
)

$ErrorActionPreference = "Stop"

# ── 变量 ─────────────────────────────────────────────────────────────────────
$RepoRoot = if ($PSScriptRoot) {
    $p = Split-Path -Parent $PSScriptRoot
    if ((Split-Path $p -Leaf) -eq 'scripts') { Split-Path -Parent $p } else { $p }
} else {
    (Get-Item "$PWD").FullName
}
$HomeDir = $env:USERPROFILE
$LocalBin = Join-Path $HomeDir ".local\bin"
$IsWindows = $true   # PowerShell 专用脚本，必然是 Windows

# rtk GitHub releases
$RtkVersion = "0.28.2"
$RtkReleaseUrl = "https://github.com/rtk-ai/rtk/releases/download/v${RtkVersion}/rtk-x86_64-pc-windows-msvc.zip"
$RtkExpectedPath = Join-Path $LocalBin "rtk.exe"

# rtk 指令合并标记
$RtkMarker = "<!-- rtk-instructions"

# ── 输出函数 ─────────────────────────────────────────────────────────────────
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERR]   $args" -ForegroundColor Red }
function Write-Skip  { Write-Host "[SKIP]  $args" -ForegroundColor Yellow }
function Write-Section {
    Write-Host ""
    Write-Host "  $args" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

# ── 辅助函数 ─────────────────────────────────────────────────────────────────

function File-Contains {
    param([string]$Pattern, [string]$FilePath)
    if (Test-Path $FilePath) {
        return (Select-String -Path $FilePath -Pattern ([regex]::Escape($Pattern)) -SimpleMatch -Quiet)
    }
    return $false
}

# 验证 rtk 是 Token Killer (不是 Type Kit)
function Test-RtkValid {
    param([string]$RtkPath)
    if (-not (Test-Path $RtkPath)) { return $false }
    try {
        $out = & $RtkPath gain 2>&1 | Out-String
        return ($out -match "Token|token|saving|saved|Session|session")
    } catch {
        return $false
    }
}

# 获取可用 rtk 路径
function Get-RtkPath {
    $cmd = (Get-Command rtk -ErrorAction SilentlyContinue).Source
    if ($cmd -and (Test-RtkValid -RtkPath $cmd)) { return $cmd }
    if ((Test-Path $RtkExpectedPath) -and (Test-RtkValid -RtkPath $RtkExpectedPath)) {
        return $RtkExpectedPath
    }
    return $null
}

# 用 rtk init 生成指令内容 → 返回字符串
# Windows 下 rtk init 先打印 "Hook-based requires Unix" 到 stderr 然后回退到 --claude-md
# 需要局部关闭 ErrorActionPreference=Stop，否则 stderr 会中断执行
function Get-RtkInstructions {
    param([string]$RtkBin)

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) "rtk-temp-$(Get-Random)"
    $prevDir = Get-Location
    try {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        Set-Location $tempDir

        & $RtkBin init 2>$null | Out-Null

        $generatedFile = Join-Path $tempDir "CLAUDE.md"
        if ((Test-Path $generatedFile) -and ((Get-Item $generatedFile).Length -gt 100)) {
            return (Get-Content $generatedFile -Raw).TrimEnd()
        }
    } catch {
        Write-Warn "rtk init 异常: $_"
    } finally {
        Set-Location $prevDir -ErrorAction SilentlyContinue
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        $ErrorActionPreference = $prevEAP
    }

    Write-Warn "无法生成 rtk 指令内容"
    return $null
}

# ── 步骤 1: 环境检查 ────────────────────────────────────────────────────────
function Step-CheckEnv {
    Write-Section "1. 环境检查"

    if ($IsWindows) {
        Write-Info "检测到 Windows — 使用项目本地模式 (无 hook，AI 手动加 rtk 前缀)"
    }

    $existing = Get-RtkPath
    if ($existing) {
        $ver = & $existing --version 2>&1
        Write-OK "rtk 已安装: $ver ($existing)"
        $script:RtkBin = $existing
        return
    }

    Write-Info "rtk 未安装，将下载预编译二进制..."
}

# ── 步骤 2: 安装 rtk ────────────────────────────────────────────────────────
function Step-InstallRtk {
    Write-Section "2. rtk 核心安装"

    $existing = Get-RtkPath
    if ($existing) {
        Write-Skip "rtk 已就绪 ($existing)"
        return
    }

    if (-not (Test-Path $LocalBin)) {
        Write-Info "创建 $LocalBin ..."
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $LocalBin -Force | Out-Null
        }
    }

    if ($DryRun) {
        Write-Info "[DRY-RUN] 从 $RtkReleaseUrl 下载 rtk.exe 到 $RtkExpectedPath"
        $script:RtkBin = $RtkExpectedPath
        return
    }

    $zipPath = Join-Path $env:TEMP "rtk-v${RtkVersion}.zip"
    $extractPath = Join-Path $env:TEMP "rtk-extract"

    try {
        Write-Info "下载 rtk v$RtkVersion ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $RtkReleaseUrl -OutFile $zipPath -ErrorAction Stop

        Write-Info "解压..."
        if (Test-Path $extractPath) { Remove-Item $extractPath -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

        $exe = Get-ChildItem -Path $extractPath -Name "rtk.exe" -Recurse | Select-Object -First 1
        $exeFull = Join-Path $extractPath $exe
        Copy-Item $exeFull $RtkExpectedPath -Force

        Write-OK "rtk 安装完成: $RtkExpectedPath"

        if (Test-RtkValid -RtkPath $RtkExpectedPath) {
            Write-OK "rtk 验证通过 (rtk gain)"
            $script:RtkBin = $RtkExpectedPath
        } else {
            Write-Err "rtk 安装后验证失败"
            exit 1
        }
    } catch {
        Write-Err "下载失败: $_"
        Write-Info "备选方案: cargo install --git https://github.com/rtk-ai/rtk"
        exit 1
    } finally {
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    }

    # 确保 PATH 中有 local bin
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$LocalBin*") {
        Write-Warn "$LocalBin 不在用户 PATH 中"
        Write-Info '请运行: setx PATH "%PATH%;' + $LocalBin + '"'
    }
}

# ── 步骤 3a: Claude Code ─────────────────────────────────────────────────────
function Step-Claude {
    Write-Section "3a. Claude Code (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 Claude Code 配置"
        return
    }

    $claudeMd = Join-Path $RepoRoot "config\claude\CLAUDE.md"
    if (-not (Test-Path $claudeMd)) {
        Write-Warn "未找到 $claudeMd，跳过"
        return
    }

    # 检查是否已合并 rtk 指令
    if (File-Contains -Pattern $RtkMarker -FilePath $claudeMd) {
        Write-Skip "rtk 指令已存在 ($claudeMd)"
        return
    }

    Write-Info "生成 rtk 指令..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] 合并 rtk 指令到 $claudeMd"
        return
    }

    # 用 rtk init --claude-md 生成指令内容
    $instructions = Get-RtkInstructions -RtkBin $script:RtkBin
    if (-not $instructions) { return }

    # 合并到 config/claude/CLAUDE.md 头部
    $existingContent = Get-Content $claudeMd -Raw
    $separator = "<!-- ═══════════ rtk instructions (auto-generated, Windows manual mode) ═══════════ -->"
    $separatorEnd = "<!-- ═══════════ end rtk instructions ═══════════ -->"
    $merged = "$separator`r`n$instructions`r`n$separatorEnd`r`n`r`n$existingContent"
    Set-Content -Path $claudeMd -Value $merged -NoNewline -Encoding UTF8
    Write-OK "rtk 指令已合并到 $claudeMd"
}

# ── 步骤 3b: Codex CLI ──────────────────────────────────────────────────────
function Step-Codex {
    Write-Section "3b. Codex CLI (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 Codex 配置"
        return
    }

    $codexAgentsMd = Join-Path $RepoRoot "config\codex\AGENTS.md"
    if (-not (Test-Path $codexAgentsMd)) {
        Write-Warn "未找到 $codexAgentsMd，跳过"
        return
    }

    if (File-Contains -Pattern $RtkMarker -FilePath $codexAgentsMd) {
        Write-Skip "rtk 指令已存在 ($codexAgentsMd)"
        return
    }

    Write-Info "合并 rtk 指令..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] 合并 rtk 指令到 $codexAgentsMd"
        return
    }

    $instructions = Get-RtkInstructions -RtkBin $script:RtkBin
    if (-not $instructions) { return }

    $existingContent = Get-Content $codexAgentsMd -Raw
    $separator = "<!-- ═══════════ rtk instructions (auto-generated, Windows manual mode) ═══════════ -->"
    $separatorEnd = "<!-- ═══════════ end rtk instructions ═══════════ -->"
    $merged = "$separator`r`n$instructions`r`n$separatorEnd`r`n`r`n$existingContent"
    Set-Content -Path $codexAgentsMd -Value $merged -NoNewline -Encoding UTF8
    Write-OK "rtk 指令已合并到 $codexAgentsMd"
}

# ── 步骤 3c: OpenCode ───────────────────────────────────────────────────────
function Step-OpenCode {
    Write-Section "3c. OpenCode (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 OpenCode 配置"
        return
    }

    $opencodeAgentsMd = Join-Path $RepoRoot "config\opencode\AGENTS.md"
    if (-not (Test-Path $opencodeAgentsMd)) {
        Write-Warn "未找到 $opencodeAgentsMd，跳过"
        return
    }

    if (File-Contains -Pattern $RtkMarker -FilePath $opencodeAgentsMd) {
        Write-Skip "rtk 指令已存在 ($opencodeAgentsMd)"
        return
    }

    Write-Info "合并 rtk 指令..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] 合并 rtk 指令到 $opencodeAgentsMd"
        return
    }

    $instructions = Get-RtkInstructions -RtkBin $script:RtkBin
    if (-not $instructions) { return }

    $existingContent = Get-Content $opencodeAgentsMd -Raw
    $separator = "<!-- ═══════════ rtk instructions (auto-generated, Windows manual mode) ═══════════ -->"
    $separatorEnd = "<!-- ═══════════ end rtk instructions ═══════════ -->"
    $merged = "$separator`r`n$instructions`r`n$separatorEnd`r`n`r`n$existingContent"
    Set-Content -Path $opencodeAgentsMd -Value $merged -NoNewline -Encoding UTF8
    Write-OK "rtk 指令已合并到 $opencodeAgentsMd"
}

# ── 步骤 4: 汇总 ─────────────────────────────────────────────────────────────
function Step-Summary {
    Write-Section "完成"

    Write-Host ""
    Write-Host "  ╔═════════════════════════════════════════════════════════╗"
    Write-Host "  ║  rtk 部署完成 (Windows 手动模式)                         ║"
    Write-Host "  ║                                                         ║"
    if ($IsWindows) {
        Write-Host "  ║  Windows 不支持 hook 自动改写命令。                     ║"
        Write-Host "  ║  AI 会手动在命令前加 rtk 前缀，效果相同。               ║"
        Write-Host "  ║  如需 hook 模式，请在 WSL 中运行。                       ║"
        Write-Host "  ║                                                         ║"
    }
    Write-Host "  ║  验证方式:                                               ║"
    Write-Host "  ║    • rtk gain          — 查看 token 节省统计             ║"
    Write-Host "  ║    • rtk gain --graph  — 带 ASCII 图                    ║"
    Write-Host "  ║                                                         ║"
    Write-Host "  ║  使用方式:                                               ║"
    Write-Host "  ║    • rtk git status    — 紧凑 git status                ║"
    Write-Host "  ║    • rtk npm test      — 紧凑测试输出                   ║"
    Write-Host "  ║    • rtk ls .          — 紧凑目录列表                   ║"
    Write-Host "  ╚═════════════════════════════════════════════════════════╝"
    Write-Host ""

    if ($DryRun) {
        Write-Warn "这是 dry-run 模式，未做实际修改。去掉 -DryRun 以执行部署。"
    }
}

# ── 主执行逻辑 ───────────────────────────────────────────────────────────────

Step-CheckEnv
Step-InstallRtk

if ($Tool) {
    switch ($Tool) {
        'claude'   { Step-Claude }
        'opencode' { Step-OpenCode }
        'codex'    { Step-Codex }
    }
} else {
    Step-Claude
    Step-Codex
    Step-OpenCode
}

Step-Summary
