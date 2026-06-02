# ==============================================================================
# deploy-context-mode.ps1
# 为 agent-skills-hook 仓库中所有 agent 工具安装 context-mode
#
# 用法:
#   .\scripts\deploy-context-mode.ps1                    # 部署全部工具
#   .\scripts\deploy-context-mode.ps1 -DryRun            # 仅检查，不修改
#   .\scripts\deploy-context-mode.ps1 -Tool claude       # 仅部署 Claude Code
#   .\scripts\deploy-context-mode.ps1 -Tool opencode     # 仅部署 OpenCode
#   .\scripts\deploy-context-mode.ps1 -Tool codex        # 仅部署 Codex CLI
#   .\scripts\deploy-context-mode.ps1 -Tool qoder        # 仅部署 Qoder
#
# 所有操作均为幂等 — 已配置则跳过。
# Git 操作使用 SSH (git@github.com:...)。
# ==============================================================================

param(
    [switch]$DryRun,
    [ValidateSet("claude", "opencode", "codex", "qoder")]
    [string]$Tool = ""
)

$ErrorActionPreference = "Stop"

# ── 变量 ─────────────────────────────────────────────────────────────────────
# 容错路径解析：PSScriptRoot 可能在通过 -File 调用时为空
if ($PSScriptRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
} else {
    $RepoRoot = (Get-Item "$PWD").FullName
}
# 如果当前目录是 scripts/，回退到上级
if ((Split-Path $RepoRoot -Leaf) -eq 'scripts') {
    $RepoRoot = Split-Path -Parent $RepoRoot
}
$ContextModeRepo = "git@github.com:mksglu/context-mode.git"
$VendorDir = Join-Path $RepoRoot ".context-mode-vendor"
$HomeDir = $env:USERPROFILE

# npm global root
$NpmGlobalRoot = "$(npm root -g 2>$null)".Trim()

# context-mode binary
$CmBin = (Get-Command context-mode -ErrorAction SilentlyContinue).Source

# 路由标记 — 用于判断是否已合并
$MergeMarker = "context-mode — MANDATORY routing rules"

# ── 输出函数 ─────────────────────────────────────────────────────────────────
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERR]   $args" -ForegroundColor Red }
function Write-Skip  { Write-Host "[SKIP]  $args" -ForegroundColor Yellow }
function Write-Section {
    $line = "=" * 60
    Write-Host ""
    Write-Host "  $args" -ForegroundColor Cyan
    Write-Host $line -ForegroundColor Cyan
}

# ── 辅助函数 ─────────────────────────────────────────────────────────────────

# 检查文件内容是否包含指定字符串
function File-Contains {
    param([string]$Pattern, [string]$FilePath)
    if (Test-Path $FilePath) {
        return (Select-String -Path $FilePath -Pattern ([regex]::Escape($Pattern)) -SimpleMatch -Quiet)
    }
    return $false
}

# 检查 context-mode 是否已全局安装
function Test-CmInstalled {
    return ($CmBin -and (Test-Path $CmBin))
}

# 获取 context-mode 路由配置文件路径。
# 优先级: npm 全局路径 → vendor 缓存目录 → SSH 克隆
function Resolve-RoutingSrc {
    param([string]$RelativePath)

    # 1) npm 全局安装路径
    if ($NpmGlobalRoot) {
        $npmPath = Join-Path $NpmGlobalRoot "context-mode" | Join-Path -ChildPath $RelativePath
        if (Test-Path $npmPath) { return $npmPath }
    }

    # 2) vendor 缓存
    $vendorPath = Join-Path $VendorDir $RelativePath
    if (Test-Path $vendorPath) { return $vendorPath }

    # 3) SSH 克隆
    if (-not (Test-Path $VendorDir)) {
        Write-Info "通过 SSH 克隆 context-mode 配置 ($ContextModeRepo)..."
        if (-not $DryRun) {
            git clone --depth 1 $ContextModeRepo $VendorDir 2>&1 | Select-Object -Last 1
        } else {
            Write-Info "[DRY-RUN] git clone --depth 1 $ContextModeRepo $VendorDir"
        }
    }

    if (Test-Path $vendorPath) { return $vendorPath }
    return $null
}

# 将路由指令合并到目标文件头部
function Merge-RoutingFile {
    param(
        [string]$SourceFile,
        [string]$DestFile
    )

    if (-not (Test-Path $SourceFile)) {
        Write-Warn "找不到源路由文件: $SourceFile"
        return $false
    }

    if (-not (Test-Path $DestFile)) {
        # 目标不存在则直接复制
        Write-Info "创建路由文件..."
        if (-not $DryRun) {
            Copy-Item $SourceFile $DestFile -Force
        }
        return $true
    }

    # 已存在 → 检查是否已合并
    if (File-Contains -Pattern $MergeMarker -FilePath $DestFile) {
        return $false
    }

    Write-Info "合并路由指令到 $DestFile..."
    if (-not $DryRun) {
        $separator = "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
        $separatorEnd = "<!-- ═══════════ end context-mode routing ═══════════ -->"
        $routingContent = Get-Content $SourceFile -Raw
        $existingContent = Get-Content $DestFile -Raw
        $merged = "$separator`r`n$routingContent`r`n$separatorEnd`r`n`r`n$existingContent"
        Set-Content -Path $DestFile -Value $merged -NoNewline -Encoding UTF8
    }
    return $true
}

# ── 步骤 1: 环境检查 ────────────────────────────────────────────────────────
function Step-CheckEnv {
    Write-Section "1. 环境检查"

    try {
        $nodeVer = node -v
        Write-OK "Node.js $nodeVer"
    } catch {
        Write-Err "Node.js 未安装。请安装 Node.js >= 22.5"
        exit 1
    }

    $major = [int]($nodeVer -replace 'v', '').Split('.')[0]
    if ($major -lt 22) {
        Write-Err "Node.js 版本过低: $nodeVer，需要 >= 22.5"
        exit 1
    }

    try {
        $npmVer = npm -v
        Write-OK "npm $npmVer"
    } catch {
        Write-Err "npm 未找到"
        exit 1
    }
}

# ── 步骤 2: 安装 context-mode 核心 ───────────────────────────────────────────
function Step-InstallCore {
    Write-Section "2. context-mode 核心安装"

    if (Test-CmInstalled) {
        $ver = & $CmBin --version 2>$null
        Write-OK "context-mode 已安装 (版本: $ver)"
    } else {
        Write-Info "正在全局安装 context-mode..."
        if (-not $DryRun) {
            npm install -g context-mode
            $script:CmBin = (Get-Command context-mode -ErrorAction SilentlyContinue).Source
            Write-OK "context-mode 安装完成"
        } else {
            Write-Info "[DRY-RUN] npm install -g context-mode"
        }
    }

    # 刷新 npm global root (安装后可能变化)
    $script:NpmGlobalRoot = "$(npm root -g 2>$null)".Trim()
}

# ── 步骤 3a: Claude Code ─────────────────────────────────────────────────────
function Step-Claude {
    Write-Section "3a. Claude Code"

    $settingsFile = Join-Path $HomeDir ".claude\settings.json"
    $routingDst = Join-Path $RepoRoot "config\claude\CLAUDE.md"

    # ── MCP 服务器 ──
    Write-Info "检查 MCP 服务器配置..."
    if ((Test-Path $settingsFile) -and (File-Contains -Pattern "context-mode" -FilePath $settingsFile)) {
        Write-Skip "MCP 服务器已配置 (settings.json)"
    } else {
        Write-Info "添加 context-mode MCP 服务器..."
        if (-not $DryRun) {
            # 用 node 做精确 JSON 合并（fsPath 用正斜杠，避免 JS 字符串中 \t\n\f 误解析）
            $fsPath = $settingsFile -replace '\\', '/'
            $nodeScript = @"
const fs = require('fs');
const path = '$fsPath';
let cfg = {};
if (fs.existsSync(path)) {
    cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
}
if (!cfg.mcpServers) cfg.mcpServers = {};
if (!cfg.mcpServers['context-mode']) {
    cfg.mcpServers['context-mode'] = { command: 'npx', args: ['-y', 'context-mode'] };
    fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\n', 'utf8');
    console.log('ok');
} else {
    console.log('skip');
}
"@
            $result = node -e $nodeScript 2>&1
            if ($result -match 'ok') {
                Write-OK "MCP 服务器已写入 $settingsFile"
            } elseif ($result -match 'skip') {
                Write-Skip "MCP 服务器已存在 (已确认)"
            } else {
                Write-Warn "JSON 合并返回: $result"
            }
        } else {
            Write-Info "[DRY-RUN] 将 context-mode MCP 添加到 $settingsFile"
        }
    }

    # ── 路由指令 (CLAUDE.md) ──
    Write-Info "检查路由指令..."
    $routingSrc = Resolve-RoutingSrc "configs\claude-code\CLAUDE.md"
    if ($routingSrc) {
        $merged = Merge-RoutingFile -SourceFile $routingSrc -DestFile $routingDst
        if ($merged) { Write-OK "路由指令已合并" } else { Write-Skip "路由指令已存在 ($routingDst)" }
    }

    # ── 提示 ──
    Write-Info "提示: 在 Claude Code 中运行以下命令可获得完整 hook 体验:"
    Write-Info "  /plugin marketplace add mksglu/context-mode"
    Write-Info "  /plugin install context-mode@context-mode"
}

# ── 步骤 3b: OpenCode ────────────────────────────────────────────────────────
function Step-OpenCode {
    Write-Section "3b. OpenCode"

    $pluginFile = Join-Path $RepoRoot "config\opencode\opencode.json"
    $routingDst = Join-Path $RepoRoot "config\opencode\AGENTS.md"

    if (-not (Test-Path $pluginFile)) {
        Write-Warn "未找到 OpenCode 配置文件: $pluginFile，跳过"
        return
    }

    # ── 插件注册 ──
    Write-Info "检查插件注册..."
    if (File-Contains -Pattern "context-mode" -FilePath $pluginFile) {
        Write-Skip "context-mode 已在 plugin 列表中 ($pluginFile)"
    } else {
        Write-Info "添加 context-mode 到 plugin 列表..."
        if (-not $DryRun) {
            # 用 node 做精确 JSON 合并（fsPath 用正斜杠，避免 JS 字符串中 \t\n\f 误解析）
            $fsPath = $pluginFile -replace '\\', '/'
            $nodeScript = @"
const fs = require('fs');
const path = '$fsPath';
const cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
if (!cfg.plugin) cfg.plugin = [];
if (!cfg.plugin.includes('context-mode')) {
    cfg.plugin.push('context-mode');
    fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\n', 'utf8');
    console.log('ok');
} else {
    console.log('skip');
}
"@
            $result = node -e $nodeScript 2>&1
            if ($result -match 'ok') {
                Write-OK "context-mode 已添加到 plugin 列表"
            } elseif ($result -match 'skip') {
                Write-Skip "context-mode 已在 plugin 列表中 (已确认)"
            } else {
                Write-Warn "JSON 合并返回: $result"
            }
        } else {
            Write-Info "[DRY-RUN] 将 context-mode 添加到 $pluginFile plugin 数组"
        }
    }

    # ── 路由指令 (AGENTS.md) ──
    Write-Info "检查路由指令..."
    $routingSrc = Resolve-RoutingSrc "configs\opencode\AGENTS.md"
    if ($routingSrc) {
        $merged = Merge-RoutingFile -SourceFile $routingSrc -DestFile $routingDst
        if ($merged) { Write-OK "路由指令已合并" } else { Write-Skip "路由指令已存在 ($routingDst)" }
    }
}

# ── 步骤 3c: Codex CLI ───────────────────────────────────────────────────────
function Step-Codex {
    Write-Section "3c. Codex CLI"

    $codexConfig = Join-Path $HomeDir ".codex\config.toml"
    $codexHooks = Join-Path $HomeDir ".codex\hooks.json"
    $codexGlobalAgents = Join-Path $HomeDir ".codex\AGENTS.md"
    $routingDst = Join-Path $RepoRoot "config\codex\AGENTS.md"

    $codexConfigExists = Test-Path $codexConfig

    # ── MCP 服务器 ──
    Write-Info "检查 MCP 服务器配置..."
    if ($codexConfigExists -and (File-Contains -Pattern "[mcp_servers.context-mode]" -FilePath $codexConfig)) {
        Write-Skip "MCP 服务器已配置 (config.toml)"
    } else {
        Write-Info "添加 context-mode MCP 服务器..."
        if (-not $DryRun) {
            $mcpBlock = @"

# ── context-mode (auto-generated by deploy-context-mode.ps1) ──
[mcp_servers.context-mode]
command = "context-mode"

[mcp_servers.context-mode.env]
CONTEXT_MODE_PLATFORM = "codex"
"@
            if ($codexConfigExists) {
                Add-Content -Path $codexConfig -Value $mcpBlock
            } else {
                Set-Content -Path $codexConfig -Value @"
[features]
hooks = true
$mcpBlock
"@
            }
            Write-OK "MCP 服务器已添加到 $codexConfig"
        } else {
            Write-Info "[DRY-RUN] 将 MCP 服务器配置追加到 $codexConfig"
        }
    }

    # ── Hooks ──
    Write-Info "检查 Hooks 配置..."
    if ((Test-Path $codexHooks) -and (File-Contains -Pattern "context-mode hook codex" -FilePath $codexHooks)) {
        Write-Skip "Hooks 已配置 ($codexHooks)"
    } else {
        Write-Info "配置 context-mode hooks..."
        if (-not $DryRun) {
            $cmHooksJson = @"
{
    "PreToolUse": [
        {
            "matcher": "local_shell|shell|shell_command|exec_command|Bash|Shell|Read|Edit|Write|WebFetch|Grep|Glob|Agent|ctx_execute|ctx_execute_file|ctx_batch_execute|ctx_fetch_and_index|ctx_search|ctx_index|mcp__",
            "hooks": [{ "type": "command", "command": "context-mode hook codex pretooluse" }]
        }
    ],
    "PostToolUse": [
        { "hooks": [{ "type": "command", "command": "context-mode hook codex posttooluse" }] }
    ],
    "SessionStart": [
        { "hooks": [{ "type": "command", "command": "context-mode hook codex sessionstart" }] }
    ],
    "PreCompact": [
        { "hooks": [{ "type": "command", "command": "context-mode hook codex precompact" }] }
    ],
    "UserPromptSubmit": [
        { "hooks": [{ "type": "command", "command": "context-mode hook codex userpromptsubmit" }] }
    ],
    "Stop": [
        { "hooks": [{ "type": "command", "command": "context-mode hook codex stop" }] }
    ]
}
"@
            # 用 node 合并：如果 hooks.json 已存在，保留原有 hook + 追加 context-mode hook
            $fsPath = $codexHooks -replace '\\', '/'
            $nodeScript = @"
const fs = require('fs');
const path = '$fsPath';
const cmHooks = $cmHooksJson;

let final;
if (fs.existsSync(path)) {
    const existing = JSON.parse(fs.readFileSync(path, 'utf8'));
    if (!existing.hooks) existing.hooks = {};
    for (const [k, v] of Object.entries(cmHooks)) {
        if (!existing.hooks[k]) {
            existing.hooks[k] = v;
        } else {
            // 只合并 context-mode 的 hook，不重复
            const existingCommands = JSON.stringify(existing.hooks[k]);
            for (const entry of v) {
                if (!existingCommands.includes(JSON.stringify(entry.hooks[0].command))) {
                    existing.hooks[k].push(entry);
                }
            }
        }
    }
    final = existing;
} else {
    final = { hooks: cmHooks };
}
fs.writeFileSync(path, JSON.stringify(final, null, 2) + '\n', 'utf8');
console.log('ok');
"@
            $result = node -e $nodeScript 2>&1
            if ($result -match 'ok') {
                Write-OK "hooks.json 已配置 (合并模式)"
            } else {
                Write-Warn "hooks 合并返回: $result"
            }
        } else {
            Write-Info "[DRY-RUN] 合并 context-mode hooks 到 $codexHooks"
        }
    }

    # ── 全局 AGENTS.md ──
    Write-Info "检查全局 AGENTS.md..."
    $routingSrc = Resolve-RoutingSrc "configs\codex\AGENTS.md"
    if ($routingSrc) {
        if ((Test-Path $codexGlobalAgents) -and (File-Contains -Pattern $MergeMarker -FilePath $codexGlobalAgents)) {
            Write-Skip "全局路由指令已存在 ($codexGlobalAgents)"
        } else {
            $merged = Merge-RoutingFile -SourceFile $routingSrc -DestFile $codexGlobalAgents
            if ($merged) { Write-OK "全局路由指令已就位" }
        }
    }

    # ── 仓库 AGENTS.md ──
    Write-Info "检查仓库路由指令..."
    if ($routingSrc) {
        $merged = Merge-RoutingFile -SourceFile $routingSrc -DestFile $routingDst
        if ($merged) { Write-OK "仓库路由指令已合并" } else { Write-Skip "仓库路由指令已存在 ($routingDst)" }
    }
}

# ── 步骤 3d: Qoder (OpenCode 兼容) ──────────────────────────────────────────
function Step-Qoder {
    Write-Section "3d. Qoder"

    $routingDst = Join-Path $RepoRoot "config\qoder\AGENTS.md"

    if (-not (Test-Path $routingDst)) {
        Write-Warn "未找到 Qoder 配置文件: $routingDst，跳过"
        return
    }

    Write-Info "注意: Qoder 与 OpenCode 共享插件架构。"
    Write-Info "如果 Qoder 支持 opencode.json 风格的 plugin 配置，请手动添加 context-mode。"

    # ── 路由指令 (AGENTS.md) ──
    Write-Info "检查路由指令..."
    $routingSrc = Resolve-RoutingSrc "configs\opencode\AGENTS.md"
    if ($routingSrc) {
        $merged = Merge-RoutingFile -SourceFile $routingSrc -DestFile $routingDst
        if ($merged) { Write-OK "路由指令已合并" } else { Write-Skip "路由指令已存在 ($routingDst)" }
    }
}

# ── 步骤 4: 汇总 ─────────────────────────────────────────────────────────────
function Step-Summary {
    Write-Section "完成"

    Write-Host ""
    Write-Host "  ┌─────────────────────────────────────────────────────────┐"
    Write-Host "  │  context-mode 部署完成                                  │"
    Write-Host "  │                                                         │"
    Write-Host "  │  验证方式 (在各工具中运行):                              │"
    Write-Host "  │    • Claude Code: /context-mode:ctx-doctor 或 ctx stats │"
    Write-Host "  │    • OpenCode:    ctx stats                             │"
    Write-Host "  │    • Codex CLI:   ctx stats                             │"
    Write-Host "  │    • Qoder:       ctx stats                             │"
    Write-Host "  │                                                         │"
    Write-Host "  │  注意: 重启各 agent 工具以使配置生效                     │"
    Write-Host "  └─────────────────────────────────────────────────────────┘"
    Write-Host ""

    if ($DryRun) {
        Write-Warn "这是 dry-run 模式，未做实际修改。去掉 -DryRun 以执行部署。"
    }
}

# ── 主执行逻辑 ───────────────────────────────────────────────────────────────

Step-CheckEnv
Step-InstallCore

if ($Tool) {
    switch ($Tool) {
        'claude'   { Step-Claude }
        'opencode' { Step-OpenCode }
        'codex'    { Step-Codex }
        'qoder'    { Step-Qoder }
    }
} else {
    Step-Claude
    Step-OpenCode
    Step-Codex
    Step-Qoder
}

Step-Summary
