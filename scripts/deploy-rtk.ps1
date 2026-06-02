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

# rtk GitHub releases
$RtkVersion = "0.28.2"
$RtkReleaseUrl = "https://github.com/rtk-ai/rtk/releases/download/v${RtkVersion}/rtk-x86_64-pc-windows-msvc.zip"
$RtkExpectedPath = Join-Path $LocalBin "rtk.exe"

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
    # 优先 PATH 中的
    $cmd = (Get-Command rtk -ErrorAction SilentlyContinue).Source
    if ($cmd -and (Test-RtkValid -RtkPath $cmd)) { return $cmd }

    # 检查 local bin
    if ((Test-Path $RtkExpectedPath) -and (Test-RtkValid -RtkPath $RtkExpectedPath)) {
        return $RtkExpectedPath
    }
    return $null
}

# ── 步骤 1: 环境检查 ────────────────────────────────────────────────────────
function Step-CheckEnv {
    Write-Section "1. 环境检查"

    # 检查已有 rtk
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

    # 创建 local bin 目录
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

    # 下载预编译二进制
    $zipPath = Join-Path $env:TEMP "rtk-v${RtkVersion}.zip"
    $extractPath = Join-Path $env:TEMP "rtk-extract"

    try {
        Write-Info "下载 rtk v$RtkVersion ..."
        Invoke-WebRequest -Uri $RtkReleaseUrl -OutFile $zipPath -ErrorAction Stop

        Write-Info "解压..."
        if (Test-Path $extractPath) { Remove-Item $extractPath -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

        # 找到 rtk.exe 并复制
        $exe = Get-ChildItem -Path $extractPath -Name "rtk.exe" -Recurse | Select-Object -First 1
        $exeFull = Join-Path $extractPath $exe
        Copy-Item $exeFull $RtkExpectedPath -Force

        Write-OK "rtk 安装完成: $RtkExpectedPath"

        # 验证
        if (Test-RtkValid -RtkPath $RtkExpectedPath) {
            Write-OK "rtk 验证通过 (rtk gain)"
            $script:RtkBin = $RtkExpectedPath
        } else {
            Write-Err "rtk 安装后验证失败 — 可能下载了错误的包"
            Write-Err "请手动检查: $RtkExpectedPath"
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
        Write-Info "请手动添加: setx PATH `"`$env:PATH;$LocalBin`""
    }
}

# ── 步骤 3a: Claude Code ─────────────────────────────────────────────────────
function Step-Claude {
    Write-Section "3a. Claude Code (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 Claude Code 配置"
        return
    }

    # 检查是否已通过 rtk init -g 配置
    $rtkMd = Join-Path $HomeDir ".claude\RTK.md"
    $hookFile = Join-Path $HomeDir ".claude\hooks\rtk-rewrite.sh"
    $settingsFile = Join-Path $HomeDir ".claude\settings.json"

    $alreadyConfigured = (Test-Path $rtkMd) -and (Test-Path $hookFile)

    if ($alreadyConfigured) {
        # 进一步检查 settings.json 中是否有 rtk hook
        if (Test-Path $settingsFile) {
            $hasHook = Select-String -Path $settingsFile -Pattern "rtk-rewrite" -SimpleMatch -Quiet
            if ($hasHook) {
                Write-Skip "Claude Code: rtk 全局 hook 已配置"
                Write-Info "  Hook: $hookFile"
                Write-Info "  RTK.md: $rtkMd"
                return
            }
        }
    }

    Write-Info "执行 rtk init -g --auto-patch ..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] & $script:RtkBin init -g --auto-patch"
    } else {
        & $script:RtkBin init -g --auto-patch 2>&1 | ForEach-Object { Write-Info "  $_" }
        Write-OK "Claude Code rtk 配置完成"
    }
}

# ── 步骤 3b: Codex CLI ──────────────────────────────────────────────────────
function Step-Codex {
    Write-Section "3b. Codex CLI (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 Codex 配置"
        return
    }

    # rtk 有 codex 支持: rtk init -g --codex
    # 检查是否已配置
    $codexRtkMd = Join-Path $HomeDir ".codex\RTK.md"
    if (Test-Path $codexRtkMd) {
        Write-Skip "Codex CLI: rtk 已配置 ($codexRtkMd)"
        return
    }

    Write-Info "执行 rtk init -g --codex ..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] & $script:RtkBin init -g --codex"
    } else {
        try {
            & $script:RtkBin init -g --codex 2>&1 | ForEach-Object { Write-Info "  $_" }
            Write-OK "Codex CLI rtk 配置完成"
        } catch {
            Write-Warn "rtk init --codex 执行异常: $_"
            Write-Info "rtk 对 Codex 的 hook 支持请参考: https://github.com/rtk-ai/rtk/tree/master/hooks/codex"
        }
    }
}

# ── 步骤 3c: OpenCode ───────────────────────────────────────────────────────
function Step-OpenCode {
    Write-Section "3c. OpenCode (rtk)"

    if (-not $script:RtkBin) {
        Write-Warn "rtk 未就绪，跳过 OpenCode 配置"
        return
    }

    # rtk 对 OpenCode 使用 TypeScript 插件: rtk init -g --opencode
    $pluginPath = Join-Path $HomeDir ".config\opencode\plugins\rtk.ts"
    if (Test-Path $pluginPath) {
        Write-Skip "OpenCode: rtk 插件已安装 ($pluginPath)"
        return
    }

    Write-Info "执行 rtk init -g --opencode ..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] & $script:RtkBin init -g --opencode"
    } else {
        try {
            & $script:RtkBin init -g --opencode 2>&1 | ForEach-Object { Write-Info "  $_" }
            Write-OK "OpenCode rtk 配置完成"
        } catch {
            Write-Warn "rtk init --opencode 执行异常: $_"
            Write-Info "手动安装方式: 将 hooks/opencode/rtk.ts 复制到 ~/.config/opencode/plugins/"
        }
    }
}

# ── 步骤 4: 汇总 ─────────────────────────────────────────────────────────────
function Step-Summary {
    Write-Section "完成"

    Write-Host ""
    Write-Host "  ╔═════════════════════════════════════════════════════════╗"
    Write-Host "  ║  rtk 部署完成                                           ║"
    Write-Host "  ║                                                         ║"
    Write-Host "  ║  验证方式:                                               ║"
    Write-Host "  ║    • rtk gain          — 查看 token 节省统计             ║"
    Write-Host "  ║    • rtk gain --graph  — 带 ASCII 图                    ║"
    Write-Host "  ║    • rtk init --show   — 检查 hook 状态                 ║"
    Write-Host "  ║                                                         ║"
    Write-Host "  ║  使用方式 (在各工具中自动生效):                          ║"
    Write-Host "  ║    • git status  → 自动改为 rtk git status              ║"
    Write-Host "  ║    • npm test    → 自动改为 rtk npm test                ║"
    Write-Host "  ║    • cargo test  → 自动改为 rtk cargo test              ║"
    Write-Host "  ║  注意: 重启各 agent 工具以使 hook 生效                   ║"
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
