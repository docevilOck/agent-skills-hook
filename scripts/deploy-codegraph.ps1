# ==============================================================================
# deploy-codegraph.ps1
# 为仓库初始化 CodeGraph 代码知识图谱索引
#
# 用法:
#   .\scripts\deploy-codegraph.ps1                  # 初始化当前仓库
#   .\scripts\deploy-codegraph.ps1 -Path <dir>      # 初始化指定目录
#   .\scripts\deploy-codegraph.ps1 -DryRun          # 仅检查，不修改
#   .\scripts\deploy-codegraph.ps1 -Force           # 强制重建索引
#   .\scripts\deploy-codegraph.ps1 -NoIndex         # 仅安装 codegraph，不建索引
#
# 所有操作均为幂等 — 已初始化则跳过。
# ==============================================================================

param(
    [string]$Path = "",
    [switch]$DryRun,
    [switch]$Force,
    [switch]$NoIndex
)

$ErrorActionPreference = "Stop"

# ── 变量 ─────────────────────────────────────────────────────────────────────
$RepoRoot = if ($PSScriptRoot) {
    $p = Split-Path -Parent $PSScriptRoot
    if ((Split-Path $p -Leaf) -eq 'scripts') { Split-Path -Parent $p } else { $p }
} else {
    (Get-Item "$PWD").FullName
}

if ($Path) {
    $TargetPath = (Resolve-Path $Path -ErrorAction Stop).Path
} else {
    $TargetPath = $RepoRoot
}

$CodegraphDir = Join-Path $TargetPath ".codegraph"
$CodegraphDb = Join-Path $CodegraphDir "codegraph.db"

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

# ── 步骤 1: 检查 codegraph CLI ──────────────────────────────────────────────
function Step-CheckCLI {
    Write-Section "1. codegraph CLI 检查"

    $cg = Get-Command codegraph -ErrorAction SilentlyContinue
    if ($cg) {
        $ver = codegraph --version 2>&1
        Write-OK "codegraph CLI 已安装: $ver"
        return $true
    }

    Write-Info "codegraph CLI 未安装，将通过 npm 安装..."
    if ($DryRun) {
        Write-Info "[DRY-RUN] npm install -g codegraph"
        return $true
    }

    try {
        npm install -g codegraph
        $ver = codegraph --version 2>&1
        Write-OK "codegraph 安装完成: $ver"
        return $true
    } catch {
        Write-Err "codegraph 安装失败: $_"
        Write-Info "备选安装方式: npm install -g @anthropic-ai/codegraph"
        return $false
    }
}

# ── 步骤 2: 检查索引状态 ────────────────────────────────────────────────────
function Step-CheckStatus {
    Write-Section "2. 索引状态检查 ($TargetPath)"

    if ($Force) {
        Write-Info "Force 模式: 将重建索引"
        return "force"
    }

    try {
        $status = codegraph status 2>&1 | Out-String

        if ($status -match "Not initialized") {
            Write-Info "CodeGraph 未初始化"
            return "uninitialized"
        }

        if ($status -match "Ready|Indexed|initialized") {
            # 提取统计信息
            $filesLine = ($status -split "`n" | Select-String "files|Files" | Select-Object -First 1)
            if ($filesLine) { Write-Info $filesLine.ToString().Trim() }

            $nodesLine = ($status -split "`n" | Select-String "nodes|symbols|Symbols" | Select-Object -First 1)
            if ($nodesLine) { Write-Info $nodesLine.ToString().Trim() }

            Write-Skip "CodeGraph 已初始化，跳过"
            return "ok"
        }

        # 有 .codegraph 目录但状态不明 → 检查数据库
        if ((Test-Path $CodegraphDb) -and ((Get-Item $CodegraphDb).Length -gt 0)) {
            Write-Skip "CodeGraph 数据库已存在 ($CodegraphDb)"
            return "ok"
        }

        Write-Info "CodeGraph 状态未知，将初始化..."
        return "uninitialized"
    } catch {
        Write-Warn "codegraph status 执行失败: $_"
        # 回退：检查 .codegraph 目录
        if (Test-Path $CodegraphDir) {
            Write-Skip ".codegraph 目录已存在，假设已初始化"
            return "ok"
        }
        return "uninitialized"
    }
}

# ── 步骤 3: 初始化索引 ──────────────────────────────────────────────────────
function Step-InitIndex {
    param([string]$Status)
    Write-Section "3. 索引初始化"

    if ($Status -eq "ok") { return }
    if ($NoIndex) {
        Write-Skip "NoIndex 模式，跳过索引构建"
        return
    }

    if ($Status -eq "force") {
        Write-Info "强制重建索引: 清理现有 .codegraph ..."
        if (-not $DryRun) {
            Remove-Item $CodegraphDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Info "执行 codegraph init -i $TargetPath ..."
    Write-Info "(首次索引可能需要几分钟，取决于仓库大小)"

    if ($DryRun) {
        Write-Info "[DRY-RUN] codegraph init -i $TargetPath"
    } else {
        $startTime = Get-Date
        try {
            codegraph init -i $TargetPath 2>&1 | ForEach-Object { Write-Info "  $_" }
            $elapsed = (Get-Date) - $startTime
            Write-OK "索引完成 (耗时: $($elapsed.TotalSeconds.ToString('0'))s)"

            # 验证数据库
            if ((Test-Path $CodegraphDb) -and ((Get-Item $CodegraphDb).Length -gt 0)) {
                $dbSizeMB = [math]::Round((Get-Item $CodegraphDb).Length / 1MB, 1)
                Write-OK "数据库: $CodegraphDb ($dbSizeMB MB)"
            } else {
                Write-Warn "数据库文件未找到或为空，索引可能未成功"
            }
        } catch {
            Write-Err "索引构建失败: $_"
            Write-Info "可以稍后手动运行: codegraph init -i $TargetPath"
        }
    }
}

# ── 步骤 4: 验证 ────────────────────────────────────────────────────────────
function Step-Verify {
    Write-Section "4. 验证"

    if ($DryRun -or $NoIndex) { return }

    try {
        $status = codegraph status 2>&1 | Out-String
        $lines = $status -split "`n"

        # 显示关键统计
        $keyLines = $lines | Select-String "files|Files|nodes|symbols|Symbols|edges|Edges|status|Status|indexed|Indexed"
        foreach ($line in $keyLines) {
            Write-Info $line.ToString().Trim()
        }

        if ($status -match "Not initialized|Error|error") {
            Write-Warn "索引状态异常，请检查"
        } else {
            Write-OK "CodeGraph 正常"
        }
    } catch {
        Write-Warn "验证步骤异常: $_"
    }
}

# ── 汇总 ─────────────────────────────────────────────────────────────────────
function Step-Summary {
    Write-Section "完成"

    Write-Host ""
    Write-Host "  ╔═════════════════════════════════════════════════════════╗"
    Write-Host "  ║  CodeGraph 部署完成                                     ║"
    Write-Host "  ║                                                         ║"
    Write-Host "  ║  MCP 工具已在各 agent 的 config 中配置                  ║"
    Write-Host "  ║    • codegraph_context  — 任务上下文入口                ║"
    Write-Host "  ║    • codegraph_search   — 符号搜索                     ║"
    Write-Host "  ║    • codegraph_trace    — 调用链追踪                   ║"
    Write-Host "  ║    • codegraph_callers  — 调用者查询                   ║"
    Write-Host "  ║    • codegraph_callees  — 被调用者查询                 ║"
    Write-Host "  ║    • codegraph_impact   — 影响面分析                   ║"
    Write-Host "  ║    • codegraph_files    — 文件树浏览                   ║"
    Write-Host "  ║    • codegraph_node     — 符号详情                     ║"
    Write-Host "  ║    • codegraph_explore  — 多符号源码浏览               ║"
    Write-Host "  ║                                                         ║"
    Write-Host "  ║  更新索引: 文件变更后自动增量更新                       ║"
    Write-Host "  ║  手动重建: codegraph init -i --force <path>             ║"
    Write-Host "  ╚═════════════════════════════════════════════════════════╝"
    Write-Host ""

    if ($DryRun) {
        Write-Warn "这是 dry-run 模式，未做实际修改。去掉 -DryRun 以执行部署。"
    }
}

# ── 主执行逻辑 ───────────────────────────────────────────────────────────────

$step1 = Step-CheckCLI
if (-not $step1) { exit 1 }

$status = Step-CheckStatus
Step-InitIndex -Status $status
Step-Verify
Step-Summary
