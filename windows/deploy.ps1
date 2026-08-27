# agent-skills-hook Windows 部署脚本
# 使用 SymbolicLink / Junction 链接方式部署 skills 和配置文件

param(
    [string]$Target = "all",
    [string]$RepoRoot = ""
)

if ($RepoRoot -eq "") {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}

$ErrorActionPreference = "Stop"

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RepoSkills = Join-Path $RepoRoot "agents\skills"
$ConfigRoot = Join-Path $RepoRoot "config"
$CodexAgents = Join-Path $ConfigRoot "codex\agents"
$SharedConfigRoot = Join-Path $ConfigRoot "shared"

# 验证 skills 目录存在
if (-not (Test-Path $RepoSkills)) {
    Write-Error "ERROR: $RepoSkills missing. Skills directory not found."
    exit 1
}

if (-not (Test-Path $CodexAgents)) {
    Write-Error "ERROR: $CodexAgents missing."
    exit 1
}

function Safe-Copy {
    param(
        [string]$Src,
        [string]$Dest,
        [bool]$Force = $true
    )
    
    $DestDir = Split-Path $Dest -Parent
    if ($DestDir -and -not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }
    
    if (Test-Path $Dest) {
        if ($Force) {
            Remove-Item $Dest -Recurse -Force
        } else {
            return
        }
    }
    
    Copy-Item $Src $Dest -Recurse -Force
}

function Safe-Link {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )

    $ParentDir = Split-Path $LinkPath -Parent
    if ($ParentDir -and -not (Test-Path $ParentDir)) {
        New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null
    }

    $existingItem = Get-Item $LinkPath -Force -ErrorAction SilentlyContinue
    if ($existingItem) {
        if ($existingItem.LinkType -and $existingItem.Target -eq $TargetPath) {
            return
        }
        Remove-Item $LinkPath -Recurse -Force
    }

    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath -Force | Out-Null
    Write-Host "Linked: $LinkPath -> $TargetPath"
}

function Safe-LinkFile {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )

    $ParentDir = Split-Path $LinkPath -Parent
    if ($ParentDir -and -not (Test-Path $ParentDir)) {
        New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null
    }

    $existingItem = Get-Item $LinkPath -Force -ErrorAction SilentlyContinue
    if ($existingItem) {
        if ($existingItem.LinkType -eq 'SymbolicLink' -and $existingItem.Target -eq $TargetPath) {
            return
        }
        Remove-Item $LinkPath -Force
    }

    cmd /c "mklink `"$LinkPath`" `"$TargetPath`"" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create symlink: $LinkPath -> $TargetPath"
    }
    Write-Host "Linked: $LinkPath -> $TargetPath"
}

function Copy-DirectoryTree {
    param(
        [string]$Src,
        [string]$Dest
    )

    if (-not (Test-Path $Src)) {
        return
    }

    if (Test-Path $Dest) {
        Remove-Item $Dest -Recurse -Force
    }

    New-Item -ItemType Directory -Path $Dest -Force | Out-Null

    $null = robocopy $Src $Dest /E /NFL /NDL /NJH /NJS /NC /NS
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed copying '$Src' to '$Dest' with exit code $LASTEXITCODE"
    }
}

function Merge-JsonConfig {
    param(
        [string]$Src,
        [string]$Dest
    )

    $DestDir = Split-Path $Dest -Parent
    if ($DestDir -and -not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }

    if (-not (Test-Path $Dest)) {
        Copy-Item $Src $Dest -Force
        return
    }

    $tmp = Join-Path $env:TEMP ("agent-skills-hook-merge-" + [guid]::NewGuid().ToString() + ".py")
    @'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2])

with src.open("r", encoding="utf-8-sig") as f:
    overlay = json.load(f)
try:
    with dest.open("r", encoding="utf-8-sig") as f:
        merged = json.load(f)
except Exception:
    backup = dest.with_suffix(dest.suffix + ".invalid.bak")
    backup.write_bytes(dest.read_bytes())
    merged = {}

def merge(base, overlay):
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = merge(base[key], value)
            continue
        if key in base and isinstance(base[key], list) and isinstance(value, list):
            base[key] = value
            continue
        base[key] = value
    return base

merge(merged, overlay)

with dest.open("w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
    f.write("\n")
'@ | Set-Content -Path $tmp -Encoding utf8

    python $tmp $Src $Dest
    Remove-Item $tmp -Force
}

function Ensure-CodeGraphInstalled {
    $cg = Get-Command codegraph -ErrorAction SilentlyContinue
    if ($null -ne $cg) {
        Write-Host "CodeGraph already installed: $($cg.Source)"
        return
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($null -eq $npm) {
        throw "codegraph not found in PATH, and npm is unavailable. Install Node.js/npm first."
    }

    Write-Host "CodeGraph not found. Installing @colbymchenry/codegraph via npm..."
    npm i -g @colbymchenry/codegraph
}

function Show-CodeGraphReminder {
    Write-Host "OpenCode MCP template now uses 'codegraph serve --mcp'."
    Write-Host "CodeGraph usage rules are documented in AGENTS.md."
    Write-Host "Per-repo indexing still needs 'codegraph init -i <repo>'."
}

function Deploy-McpServers {
    param(
        [string]$Runtime,
        [string[]]$ScopeArgs = @()
    )

    $McpJson = Join-Path $SharedConfigRoot "mcp_servers.json"
    if (-not (Test-Path $McpJson)) {
        Write-Host "MCP config not found at $McpJson, skipping MCP deployment for $Runtime"
        return
    }

    $exe = Get-Command $Runtime -ErrorAction SilentlyContinue
    if ($null -eq $exe) {
        Write-Warning "$Runtime CLI not found in PATH. Skipping MCP deployment."
        return
    }

    Write-Host "Deploying MCP servers for $Runtime..."
    $servers = Get-Content $McpJson -Raw | ConvertFrom-Json

    foreach ($prop in $servers.PSObject.Properties) {
        $name = $prop.Name
        $srv = $prop.Value

        # Remove existing (ignore errors)
        $rmArgs = @("mcp", "remove") + $ScopeArgs + @($name)
        & $Runtime @rmArgs 2>&1 | Out-Null

        # Add server: <runtime> mcp add [scope] <name> -- <command> <args...>
        $addArgs = @("mcp", "add") + $ScopeArgs + @($name, "--", $srv.command)
        if ($srv.args) { $addArgs += @($srv.args) }

        & $Runtime @addArgs 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  MCP server '$name' configured for $Runtime"
        } else {
            Write-Warning "  Failed to add MCP server '$name' for $Runtime"
        }
    }
}

Ensure-CodeGraphInstalled
Show-CodeGraphReminder

# Codex 部署
if ($Target -eq "codex" -or $Target -eq "all") {
    $BackupC = Join-Path $env:USERPROFILE ".codex-backups\agent-skills-hook-$Stamp"
    New-Item -ItemType Directory -Path "$BackupC\codex", "$BackupC\repo" -Force | Out-Null
    
    # 备份现有配置
    $CodexDir = Join-Path $env:USERPROFILE ".codex"
    if (Test-Path "$CodexDir\AGENTS.md") { Copy-Item "$CodexDir\AGENTS.md" "$BackupC\codex\AGENTS.md" -Force }
    if (Test-Path "$CodexDir\agents") { Copy-DirectoryTree "$CodexDir\agents" "$BackupC\codex\agents" }
    if (Test-Path "$CodexDir\skills") { Copy-DirectoryTree "$CodexDir\skills" "$BackupC\codex\skills" }
    Copy-DirectoryTree $RepoSkills "$BackupC\repo\skills"
    
    # 部署配置（从 config/ 复制）
    Safe-LinkFile "$CodexDir\AGENTS.md" "$ConfigRoot\codex\AGENTS.md"
    Safe-Link "$CodexDir\agents" $CodexAgents
    Safe-Link "$CodexDir\skills" $RepoSkills
    if (Test-Path "$env:USERPROFILE\.agents\skills") {
        Write-Host "Legacy Codex skill root detected at $env:USERPROFILE\.agents\skills. Archive or remove it to avoid duplicate skill scanning."
    }
    
    # Deploy MCP servers for Codex
    Deploy-McpServers -Runtime "codex"

    Write-Host "Codex deployed. Backup: $BackupC"
}

# OpenCode 部署
if ($Target -eq "opencode" -or $Target -eq "all") {
    $BackupO = Join-Path $env:USERPROFILE ".opencode-backups\agent-skills-hook-$Stamp"
    New-Item -ItemType Directory -Path "$BackupO\opencode", "$BackupO\claude", "$BackupO\repo" -Force | Out-Null
    
    # 备份现有配置
    $OpenCodeDir = Join-Path $env:USERPROFILE ".config\opencode"
    if (Test-Path "$OpenCodeDir\AGENTS.md") { Copy-Item "$OpenCodeDir\AGENTS.md" "$BackupO\opencode\AGENTS.md" -Force }
    if (Test-Path "$OpenCodeDir\agents") { Copy-DirectoryTree "$OpenCodeDir\agents" "$BackupO\opencode\agents" }
    if (Test-Path "$OpenCodeDir\skills") { Copy-DirectoryTree "$OpenCodeDir\skills" "$BackupO\opencode\skills" }
    if (Test-Path "$env:USERPROFILE\.claude\skills") { Copy-DirectoryTree "$env:USERPROFILE\.claude\skills" "$BackupO\claude\skills" }
    Copy-DirectoryTree $RepoSkills "$BackupO\repo\skills"
    
    # 部署配置（从 config/ 复制）
    New-Item -ItemType Directory -Path "$OpenCodeDir" -Force | Out-Null
    Safe-LinkFile "$OpenCodeDir\AGENTS.md" "$ConfigRoot\opencode\AGENTS.md"
    Safe-Link "$OpenCodeDir\agents" "$ConfigRoot\opencode\agents"
    Merge-JsonConfig "$ConfigRoot\opencode\opencode.json" "$OpenCodeDir\opencode.json"

    # DCP 配置：与 opencode.json 一样走深合并
    Merge-JsonConfig "$ConfigRoot\opencode\dcp.jsonc" "$OpenCodeDir\dcp.jsonc"

    Safe-Link "$OpenCodeDir\skills" $RepoSkills

    # 安装 opencode 插件（opencode plugin -g 负责 npm install + 配置写入）
    $OcExe = Get-Command opencode -ErrorAction SilentlyContinue
    if ($null -ne $OcExe) {
        $MergedConfig = Join-Path $OpenCodeDir "opencode.json"
        if (Test-Path $MergedConfig) {
            $OcConfig = Get-Content $MergedConfig -Raw | ConvertFrom-Json
            $Plugins = $OcConfig.plugin
            if ($Plugins -and $Plugins.Count -gt 0) {
                Write-Host "Installing opencode plugins..."
                foreach ($Pkg in $Plugins) {
                    $PkgName = ($Pkg -split '@')[0]
                    if ($Pkg -match '^@.+' -and ($Pkg -split '@').Count -gt 2) {
                        $PkgName = '@' + ($Pkg -split '@')[1]
                    }
                    Write-Host "  opencode plugin -g $PkgName"
                    $result = & opencode plugin -g $PkgName 2>&1
                    if ($LASTEXITCODE -ne 0) {
                        Write-Warning "  Failed to install plugin '$PkgName': $result"
                    }
                }
            }
        }
    }
    else {
        Write-Warning "opencode CLI not found in PATH. Install opencode first, then re-run deploy to install plugins."
    }

    if (Test-Path "$env:USERPROFILE\.agents\skills") {
        Write-Host "Legacy shared skill root detected at $env:USERPROFILE\.agents\skills. OpenCode now uses $OpenCodeDir\skills as the primary user skill root."
    }
    
    Write-Host "OpenCode deployed. Backup: $BackupO"
}

# Claude Code 部署
if ($Target -eq "claude" -or $Target -eq "all") {
    $BackupCL = Join-Path $env:USERPROFILE ".claude-backups\agent-skills-hook-$Stamp"
    New-Item -ItemType Directory -Path "$BackupCL\claude", "$BackupCL\repo" -Force | Out-Null
    
    # 备份现有配置
    $ClaudeDir = Join-Path $env:USERPROFILE ".claude"
    if (Test-Path "$ClaudeDir\AGENTS.md") { Copy-Item "$ClaudeDir\AGENTS.md" "$BackupCL\claude\AGENTS.md" -Force }
    if (Test-Path "$ClaudeDir\CLAUDE.md") { Copy-Item "$ClaudeDir\CLAUDE.md" "$BackupCL\claude\CLAUDE.md" -Force }
    if (Test-Path "$ClaudeDir\agents") { Copy-DirectoryTree "$ClaudeDir\agents" "$BackupCL\claude\agents" }
    if (Test-Path "$ClaudeDir\skills") { Copy-DirectoryTree "$ClaudeDir\skills" "$BackupCL\claude\skills" }
    Copy-DirectoryTree $RepoSkills "$BackupCL\repo\skills"

    # 部署配置（从 config/ 复制）
    New-Item -ItemType Directory -Path "$ClaudeDir" -Force | Out-Null
    Safe-LinkFile "$ClaudeDir\AGENTS.md" "$ConfigRoot\AGENTS.md"
    Safe-LinkFile "$ClaudeDir\CLAUDE.md" "$ConfigRoot\claude\CLAUDE.md"
    Safe-Link "$ClaudeDir\agents" "$ConfigRoot\claude\agents"
    Safe-Link "$ClaudeDir\skills" $RepoSkills
    
    # Deploy MCP servers for Claude Code (user scope)
    Deploy-McpServers -Runtime "claude" -ScopeArgs @("-s", "user")

    Write-Host "Claude Code deployed. Backup: $BackupCL"
}

# DSH (DeepSeek Harness) 部署
if ($Target -eq "dsh" -or $Target -eq "all") {
    $BackupD = Join-Path $env:USERPROFILE ".dsh-backups\agent-skills-hook-$Stamp"
    New-Item -ItemType Directory -Path "$BackupD\dsh" -Force | Out-Null

    # 备份现有配置
    $DshDir = Join-Path $env:USERPROFILE ".dsh"
    if (Test-Path "$DshDir\AGENTS.md") { Copy-Item "$DshDir\AGENTS.md" "$BackupD\dsh\AGENTS.md" -Force }

    # 部署配置（复用 Claude Code 的 CLAUDE.md 作为 DSH 全局指令）
    Safe-LinkFile "$DshDir\AGENTS.md" "$ConfigRoot\claude\CLAUDE.md"

    Write-Host "DSH deployed. Backup: $BackupD"
}

Write-Host "Deployment complete."
