#!/bin/bash
# ==============================================================================
# deploy-context-mode.sh
# 为 agent-skills-hook 仓库中所有 agent 工具安装 context-mode
#
# 用法:
#   ./scripts/deploy-context-mode.sh          # 部署全部工具
#   ./scripts/deploy-context-mode.sh --dry-run # 仅检查，不修改
#   ./scripts/deploy-context-mode.sh --tool claude  # 仅部署 Claude Code
#   ./scripts/deploy-context-mode.sh --tool opencode # 仅部署 OpenCode
#   ./scripts/deploy-context-mode.sh --tool codex    # 仅部署 Codex CLI
#   ./scripts/deploy-context-mode.sh --tool qoder    # 仅部署 Qoder
#
# 所有操作均为幂等 — 已配置则跳过。
# Git 操作使用 SSH (git@github.com:...)。
# ==============================================================================

set -euo pipefail

# ── 颜色输出 ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()     { echo -e "${RED}[ERR]${NC}   $*"; }
skip()    { echo -e "${YELLOW}[SKIP]${NC}  $*"; }
section() { echo ""; echo -e "${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════${NC}"; }

# ── 参数解析 ─────────────────────────────────────────────────────────────────
DRY_RUN=false
TARGET_TOOL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --tool)    TARGET_TOOL="$2"; shift 2 ;;
    -h|--help)
      echo "用法: $0 [--dry-run] [--tool claude|opencode|codex|qoder]"
      exit 0
      ;;
    *) err "未知参数: $1"; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTEXT_MODE_REPO="git@github.com:mksglu/context-mode.git"

# Windows 下 npm root -g 可能带 CRLF，统一 strip
CM_GLOBAL_BIN="$(command -v context-mode 2>/dev/null || echo '')"
_cm_npm_root_raw="$(npm root -g 2>/dev/null || echo '')"
CM_NPM_ROOT="$(echo "$_cm_npm_root_raw" | tr -d '\r')"

# 路由文件回退缓存目录
CM_VENDOR_DIR="$REPO_ROOT/.context-mode-vendor"

# ── 辅助函数 ─────────────────────────────────────────────────────────────────

# 检查字符串是否已存在于文件中
file_contains() {
  local pattern="$1" file="$2"
  [ -f "$file" ] && grep -qF "$pattern" "$file" 2>/dev/null
}

# 检查 context-mode 插件服务是否已配置
is_cm_npm_installed() {
  [ -n "$CM_GLOBAL_BIN" ] && "$CM_GLOBAL_BIN" --version &>/dev/null
}

# 获取 context-mode 路由配置文件。
# 优先从 npm 全局安装路径取；取不到则通过 SSH 克隆到本地 vendor 目录。
# 用法: resolve_routing_src <relative-path>  → 输出绝对路径到 stdout
# 例:  resolve_routing_src configs/opencode/AGENTS.md
resolve_routing_src() {
  local rel="$1"

  # 1) npm 全局安装路径
  if [ -n "$CM_NPM_ROOT" ] && [ -f "$CM_NPM_ROOT/context-mode/$rel" ]; then
    echo "$CM_NPM_ROOT/context-mode/$rel"
    return 0
  fi

  # 2) 已缓存的 vendor 目录
  if [ -f "$CM_VENDOR_DIR/$rel" ]; then
    echo "$CM_VENDOR_DIR/$rel"
    return 0
  fi

  # 3) SSH 克隆到 vendor 目录
  if [ ! -d "$CM_VENDOR_DIR" ]; then
    info "通过 SSH 克隆 context-mode 配置 (git@github.com:mksglu/context-mode.git)..."
    if [ "$DRY_RUN" = false ]; then
      git clone --depth 1 "$CONTEXT_MODE_REPO" "$CM_VENDOR_DIR" 2>&1 | tail -1
    else
      info "[DRY-RUN] git clone --depth 1 $CONTEXT_MODE_REPO $CM_VENDOR_DIR"
    fi
  fi

  if [ -f "$CM_VENDOR_DIR/$rel" ]; then
    echo "$CM_VENDOR_DIR/$rel"
    return 0
  fi

  return 1
}

# ── 步骤 1: 环境检查 ────────────────────────────────────────────────────────
section "1. 环境检查"

NODE_VERSION=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_VERSION" ]; then
  err "Node.js 未安装。请安装 Node.js >= 22.5"
  exit 1
elif [ "$NODE_VERSION" -lt 22 ]; then
  err "Node.js 版本过低: $(node -v)，需要 >= 22.5"
  exit 1
fi
ok "Node.js $(node -v)"

if command -v npm &>/dev/null; then
  ok "npm $(npm -v)"
else
  err "npm 未找到"
  exit 1
fi

# ── 步骤 2: 安装 context-mode ───────────────────────────────────────────────
section "2. context-mode 核心安装"

if is_cm_npm_installed; then
  CM_VERSION=$("$CM_GLOBAL_BIN" --version 2>/dev/null || echo "unknown")
  ok "context-mode 已安装 (版本: $CM_VERSION)"
else
  info "正在全局安装 context-mode..."
  if [ "$DRY_RUN" = true ]; then
    info "[DRY-RUN] npm install -g context-mode"
  else
    npm install -g context-mode
    CM_GLOBAL_BIN="$(command -v context-mode)"
    ok "context-mode 安装完成 ($(context-mode --version 2>/dev/null || echo 'ok'))"
  fi
fi

# 刷新 CM_NPM_ROOT
CM_NPM_ROOT="$(npm root -g 2>/dev/null || echo '')"

# ── 步骤 3: 为各 agent 工具配置 ──────────────────────────────────────────────

# ==============================================================================
# Claude Code
# ==============================================================================
configure_claude() {
  section "3a. Claude Code"

  local SETTINGS_FILE="$HOME/.claude/settings.json"
  local ROUTING_SRC="$CM_NPM_ROOT/context-mode/configs/claude-code/CLAUDE.md"
  local ROUTING_DST="$REPO_ROOT/config/claude/CLAUDE.md"
  local MERGE_MARKER="context-mode — MANDATORY routing rules"

  # ── MCP 服务器 ──
  info "检查 MCP 服务器配置..."
  if [ -f "$SETTINGS_FILE" ] && file_contains '"context-mode"' "$SETTINGS_FILE"; then
    skip "MCP 服务器已配置 (settings.json)"
  else
    info "添加 context-mode MCP 服务器..."
    if [ "$DRY_RUN" = true ]; then
      info "[DRY-RUN] 将 context-mode MCP 添加到 $SETTINGS_FILE"
    else
      if [ -f "$SETTINGS_FILE" ]; then
        # 用 node 合并 JSON，保留已有字段
        node -e "
          const fs = require('fs');
          const cfg = JSON.parse(fs.readFileSync('$SETTINGS_FILE','utf8'));
          if(!cfg.mcpServers) cfg.mcpServers = {};
          if(!cfg.mcpServers['context-mode']) {
            cfg.mcpServers['context-mode'] = { command: 'npx', args: ['-y', 'context-mode'] };
            fs.writeFileSync('$SETTINGS_FILE', JSON.stringify(cfg, null, 2) + '\n');
            console.log('done');
          } else {
            console.log('exists');
          }
        "
      else
        # 新建 settings.json
        node -e "
          const fs = require('fs');
          const cfg = { mcpServers: { 'context-mode': { command: 'npx', args: ['-y', 'context-mode'] } } };
          fs.writeFileSync('$SETTINGS_FILE', JSON.stringify(cfg, null, 2) + '\n');
          console.log('done');
        "
      fi
      ok "MCP 服务器已写入 $SETTINGS_FILE"
    fi
  fi

  # ── 路由指令 (CLAUDE.md) ──
  info "检查路由指令..."
  if file_contains "$MERGE_MARKER" "$ROUTING_DST"; then
    skip "路由指令已存在 ($ROUTING_DST)"
  else
    if [ -f "$ROUTING_SRC" ]; then
      info "合并 context-mode 路由指令到 $ROUTING_DST..."
      if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] 将 $ROUTING_SRC 合并到 $ROUTING_DST"
      else
        local TMPFILE="${ROUTING_DST}.tmp.$$"
        {
          echo "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
          cat "$ROUTING_SRC"
          echo "<!-- ═══════════ end context-mode routing ═══════════ -->"
          echo ""
          cat "$ROUTING_DST"
        } > "$TMPFILE"
        mv "$TMPFILE" "$ROUTING_DST"
        ok "路由指令已合并"
      fi
    else
      warn "找不到源路由文件: $ROUTING_SRC"
      warn "请确认 context-mode npm 包已正确安装"
    fi
  fi

  # ── 提示: 完整插件体验 ──
  info "提示: 在 Claude Code 中运行以下命令可获得完整 hook 体验:"
  info "  /plugin marketplace add mksglu/context-mode"
  info "  /plugin install context-mode@context-mode"
}

# ==============================================================================
# OpenCode
# ==============================================================================
configure_opencode() {
  section "3b. OpenCode"

  local PLUGIN_FILE="$REPO_ROOT/config/opencode/opencode.json"
  local ROUTING_SRC="$CM_NPM_ROOT/context-mode/configs/opencode/AGENTS.md"
  local ROUTING_DST="$REPO_ROOT/config/opencode/AGENTS.md"
  local MERGE_MARKER="context-mode — MANDATORY routing rules"

  if [ ! -f "$PLUGIN_FILE" ]; then
    warn "未找到 OpenCode 配置文件: $PLUGIN_FILE，跳过"
    return
  fi

  # ── 插件注册 ──
  info "检查插件注册..."
  if file_contains '"context-mode"' "$PLUGIN_FILE"; then
    skip "context-mode 已在 plugin 列表中 ($PLUGIN_FILE)"
  else
    info "添加 context-mode 到 plugin 列表..."
    if [ "$DRY_RUN" = true ]; then
      info "[DRY-RUN] 将 context-mode 添加到 $PLUGIN_FILE plugin 数组"
    else
      node -e "
        const fs = require('fs');
        const cfg = JSON.parse(fs.readFileSync('$PLUGIN_FILE','utf8'));
        if(!cfg.plugin) cfg.plugin = [];
        if(!cfg.plugin.includes('context-mode')) {
          cfg.plugin.push('context-mode');
          fs.writeFileSync('$PLUGIN_FILE', JSON.stringify(cfg, null, 2) + '\n');
          console.log('done');
        } else {
          console.log('exists');
        }
      "
      ok "context-mode 已添加到 plugin 列表"
    fi
  fi

  # ── 路由指令 (AGENTS.md) ──
  info "检查路由指令..."
  if file_contains "$MERGE_MARKER" "$ROUTING_DST"; then
    skip "路由指令已存在 ($ROUTING_DST)"
  else
    if [ -f "$ROUTING_SRC" ]; then
      info "合并 context-mode 路由指令到 $ROUTING_DST..."
      if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] 将 $ROUTING_SRC 合并到 $ROUTING_DST"
      else
        local TMPFILE="${ROUTING_DST}.tmp.$$"
        {
          echo "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
          cat "$ROUTING_SRC"
          echo "<!-- ═══════════ end context-mode routing ═══════════ -->"
          echo ""
          cat "$ROUTING_DST"
        } > "$TMPFILE"
        mv "$TMPFILE" "$ROUTING_DST"
        ok "路由指令已合并"
      fi
    else
      warn "找不到源路由文件: $ROUTING_SRC"
    fi
  fi
}

# ==============================================================================
# Codex CLI
# ==============================================================================
configure_codex() {
  section "3c. Codex CLI"

  local CODEX_CONFIG="$HOME/.codex/config.toml"
  local CODEX_HOOKS="$HOME/.codex/hooks.json"
  local CODEX_AGENTS_GLOBAL="$HOME/.codex/AGENTS.md"
  local ROUTING_SRC="$CM_NPM_ROOT/context-mode/configs/codex/AGENTS.md"
  local ROUTING_DST="$REPO_ROOT/config/codex/AGENTS.md"
  local MERGE_MARKER="context-mode — MANDATORY routing rules"

  local CODEX_CONFIG_EXISTS=false
  [ -f "$CODEX_CONFIG" ] && CODEX_CONFIG_EXISTS=true

  # ── MCP 服务器 ──
  info "检查 MCP 服务器配置..."
  if $CODEX_CONFIG_EXISTS && file_contains '[mcp_servers.context-mode]' "$CODEX_CONFIG"; then
    skip "MCP 服务器已配置 (config.toml)"
  else
    info "添加 context-mode MCP 服务器..."

    local MCP_BLOCK="
# ── context-mode (auto-generated by deploy-context-mode.sh) ──
[mcp_servers.context-mode]
command = \"context-mode\"

[mcp_servers.context-mode.env]
CONTEXT_MODE_PLATFORM = \"codex\""

    if [ "$DRY_RUN" = true ]; then
      info "[DRY-RUN] 将 MCP 服务器配置追加到 $CODEX_CONFIG"
    else
      if $CODEX_CONFIG_EXISTS; then
        echo "$MCP_BLOCK" >> "$CODEX_CONFIG"
      else
        # 新建最小 config.toml
        echo '[features]' > "$CODEX_CONFIG"
        echo 'hooks = true' >> "$CODEX_CONFIG"
        echo "$MCP_BLOCK" >> "$CODEX_CONFIG"
      fi
      ok "MCP 服务器已添加到 $CODEX_CONFIG"
    fi
  fi

  # ── Hooks ──
  info "检查 Hooks 配置..."
  if [ -f "$CODEX_HOOKS" ] && file_contains '"context-mode hook codex' "$CODEX_HOOKS"; then
    skip "Hooks 已配置 ($CODEX_HOOKS)"
  else
    info "配置 context-mode hooks..."
    if [ "$DRY_RUN" = true ]; then
      info "[DRY-RUN] 合并 context-mode hooks 到 $CODEX_HOOKS"
    else
      node -e "
        const fs = require('fs');
        const cmHooks = {
          PreToolUse: [{
            matcher: 'local_shell|shell|shell_command|exec_command|Bash|Shell|Read|Edit|Write|WebFetch|Grep|Glob|Agent|ctx_execute|ctx_execute_file|ctx_batch_execute|ctx_fetch_and_index|ctx_search|ctx_index|mcp__',
            hooks: [{ type: 'command', command: 'context-mode hook codex pretooluse' }]
          }],
          PostToolUse: [{
            hooks: [{ type: 'command', command: 'context-mode hook codex posttooluse' }]
          }],
          SessionStart: [{
            hooks: [{ type: 'command', command: 'context-mode hook codex sessionstart' }]
          }],
          PreCompact: [{
            hooks: [{ type: 'command', command: 'context-mode hook codex precompact' }]
          }],
          UserPromptSubmit: [{
            hooks: [{ type: 'command', command: 'context-mode hook codex userpromptsubmit' }]
          }],
          Stop: [{
            hooks: [{ type: 'command', command: 'context-mode hook codex stop' }]
          }]
        };

        let final;
        if (fs.existsSync('$CODEX_HOOKS')) {
          const existing = JSON.parse(fs.readFileSync('$CODEX_HOOKS', 'utf8'));
          if (!existing.hooks) existing.hooks = {};
          for (const [k, v] of Object.entries(cmHooks)) {
            if (!existing.hooks[k]) {
              existing.hooks[k] = v;
            } else {
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
        fs.writeFileSync('$CODEX_HOOKS', JSON.stringify(final, null, 2) + '\n', 'utf8');
        console.log('done');
      "
      ok "hooks.json 已配置 (合并模式)"
    fi
  fi

  # ── 全局 AGENTS.md ──
  info "检查全局 AGENTS.md..."
  if [ -f "$CODEX_AGENTS_GLOBAL" ] && file_contains "$MERGE_MARKER" "$CODEX_AGENTS_GLOBAL"; then
    skip "全局路由指令已存在 ($CODEX_AGENTS_GLOBAL)"
  else
    if [ -f "$ROUTING_SRC" ]; then
      if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] 复制路由指令到 $CODEX_AGENTS_GLOBAL"
      else
        if [ -f "$CODEX_AGENTS_GLOBAL" ]; then
          local TMPFILE="${CODEX_AGENTS_GLOBAL}.tmp.$$"
          {
            echo "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
            cat "$ROUTING_SRC"
            echo "<!-- ═══════════ end context-mode routing ═══════════ -->"
            echo ""
            cat "$CODEX_AGENTS_GLOBAL"
          } > "$TMPFILE"
          mv "$TMPFILE" "$CODEX_AGENTS_GLOBAL"
        else
          cp "$ROUTING_SRC" "$CODEX_AGENTS_GLOBAL"
        fi
        ok "全局路由指令已就位"
      fi
    else
      warn "找不到源路由文件: $ROUTING_SRC"
    fi
  fi

  # ── 仓库 AGENTS.md ──
  info "检查仓库路由指令..."
  if file_contains "$MERGE_MARKER" "$ROUTING_DST"; then
    skip "仓库路由指令已存在 ($ROUTING_DST)"
  else
    if [ -f "$ROUTING_SRC" ]; then
      if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] 合并路由指令到 $ROUTING_DST"
      else
        local TMPFILE="${ROUTING_DST}.tmp.$$"
        {
          echo "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
          cat "$ROUTING_SRC"
          echo "<!-- ═══════════ end context-mode routing ═══════════ -->"
          echo ""
          cat "$ROUTING_DST"
        } > "$TMPFILE"
        mv "$TMPFILE" "$ROUTING_DST"
        ok "仓库路由指令已合并"
      fi
    fi
  fi
}

# ==============================================================================
# Qoder (OpenCode 兼容)
# ==============================================================================
configure_qoder() {
  section "3d. Qoder"

  local ROUTING_SRC="$CM_NPM_ROOT/context-mode/configs/opencode/AGENTS.md"
  local ROUTING_DST="$REPO_ROOT/config/qoder/AGENTS.md"
  local MERGE_MARKER="context-mode — MANDATORY routing rules"

  if [ ! -f "$ROUTING_DST" ]; then
    warn "未找到 Qoder 配置文件: $ROUTING_DST，跳过"
    return
  fi

  # Qoder 兼容 OpenCode 插件架构
  info "注意: Qoder 与 OpenCode 共享插件架构。"
  info "如果 Qoder 支持 opencode.json 风格的 plugin 配置，请手动添加 context-mode。"

  # ── 路由指令 (AGENTS.md) ──
  info "检查路由指令..."
  if file_contains "$MERGE_MARKER" "$ROUTING_DST"; then
    skip "路由指令已存在 ($ROUTING_DST)"
  else
    if [ -f "$ROUTING_SRC" ]; then
      info "合并 context-mode 路由指令到 $ROUTING_DST..."
      if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] 将 $ROUTING_SRC 合并到 $ROUTING_DST"
      else
        local TMPFILE="${ROUTING_DST}.tmp.$$"
        {
          echo "<!-- ═══════════ context-mode routing (auto-generated) ═══════════ -->"
          cat "$ROUTING_SRC"
          echo "<!-- ═══════════ end context-mode routing ═══════════ -->"
          echo ""
          cat "$ROUTING_DST"
        } > "$TMPFILE"
        mv "$TMPFILE" "$ROUTING_DST"
        ok "路由指令已合并"
      fi
    else
      warn "找不到源路由文件: $ROUTING_SRC"
    fi
  fi
}

# ── 主执行逻辑 ───────────────────────────────────────────────────────────────

if [ -n "$TARGET_TOOL" ]; then
  case "$TARGET_TOOL" in
    claude)   configure_claude ;;
    opencode) configure_opencode ;;
    codex)    configure_codex ;;
    qoder)    configure_qoder ;;
    *)
      err "未知工具: $TARGET_TOOL (可选: claude, opencode, codex, qoder)"
      exit 1
      ;;
  esac
else
  configure_claude
  configure_opencode
  configure_codex
  configure_qoder
fi

# ── 汇总 ─────────────────────────────────────────────────────────────────────
section "完成"

echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  context-mode 部署完成                                  │"
echo "  │                                                         │"
echo "  │  验证方式 (在各工具中运行):                              │"
echo "  │    • Claude Code: /context-mode:ctx-doctor 或 ctx stats │"
echo "  │    • OpenCode:    ctx stats                             │"
echo "  │    • Codex CLI:   ctx stats                             │"
echo "  │    • Qoder:       ctx stats                             │"
echo "  │                                                         │"
echo "  │  注意: 重启各 agent 工具以使配置生效                     │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""

if [ "$DRY_RUN" = true ]; then
  warn "这是 dry-run 模式，未做实际修改。去掉 --dry-run 以执行部署。"
fi
