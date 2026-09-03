#!/bin/bash
# agent-skills-hook Linux 部署脚本
# 使用软链接方式部署配置

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(dirname "$SCRIPT_DIR")}"
TARGET="${TARGET:-all}"
STAMP="$(date +%Y%m%d-%H%M%S)"

# Skills 位于仓库根目录
REPO_SKILLS="$REPO_ROOT/agents/skills"
# 配置源位于 config/ 目录（自包含）
CONFIG_ROOT="$REPO_ROOT/config"
CODEX_AGENTS="$CONFIG_ROOT/codex/agents"
OPENCODE_CONFIG="$CONFIG_ROOT/opencode"
SHARED_CONFIG_ROOT="$CONFIG_ROOT/shared"

if [ ! -d "$REPO_SKILLS" ]; then
  echo "ERROR: $REPO_SKILLS missing. Skills directory not found." >&2
  exit 1
fi

if [ ! -d "$CODEX_AGENTS" ]; then
  echo "ERROR: $CODEX_AGENTS missing." >&2
  exit 1
fi

if [ ! -f "$OPENCODE_CONFIG/opencode.json" ]; then
  echo "ERROR: $OPENCODE_CONFIG/opencode.json missing." >&2
  exit 1
fi

safe_link() {
  local link_path="$1"
  local target_path="$2"
  mkdir -p "$(dirname "$link_path")"

  if [ -L "$link_path" ]; then
    local real
    real="$(readlink -f "$link_path" 2>/dev/null || true)"
    if [ "$real" = "$target_path" ]; then
      return 0
    fi
    rm -f "$link_path"
  elif [ -e "$link_path" ]; then
    rm -rf "$link_path"
  fi

  ln -s "$target_path" "$link_path"
}

merge_json_config() {
  local src="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"

  if [ ! -f "$dest" ]; then
    cp -a "$src" "$dest"
    return 0
  fi

  python3 - "$src" "$dest" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2])

with dest.open("r", encoding="utf-8") as f:
    merged = json.load(f)
with src.open("r", encoding="utf-8") as f:
    overlay = json.load(f)

def merge(base, overlay):
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = merge(base[key], value)
            continue
        if key in base and isinstance(base[key], list) and isinstance(value, list):
            merged_list = []
            seen = set()
            for item in base[key] + value:
                marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if marker in seen:
                    continue
                seen.add(marker)
                merged_list.append(item)
            base[key] = merged_list
            continue
        base[key] = value
    return base

merge(merged, overlay)

with dest.open("w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

install_opencode_plugins() {
  local opencode_dir="$1"

  if ! command -v opencode >/dev/null 2>&1; then
    echo "WARNING: opencode CLI not found in PATH. Install opencode first, then re-run deploy to install plugins."
    return 0
  fi

  local merged_config="$opencode_dir/opencode.json"
  if [ ! -f "$merged_config" ]; then
    return 0
  fi

  local plugins
  plugins="$(python3 -c "
import json, sys
with open(sys.argv[1], 'r') as f:
    cfg = json.load(f)
print('\n'.join(cfg.get('plugin', [])))
" "$merged_config")"

  if [ -z "$plugins" ]; then
    return 0
  fi

  echo "Installing opencode plugins..."
  while IFS= read -r pkg_raw; do
    [ -z "$pkg_raw" ] && continue
    local pkg_name
    pkg_name="$(python3 -c "
s = '''$pkg_raw'''.strip()
if s.startswith('@'):
    parts = s.split('@')
    print('@' + parts[1])
else:
    print(s.split('@')[0])
")"
    echo "  opencode plugin -g $pkg_name"
    if ! opencode plugin -g "$pkg_name"; then
      echo "  WARNING: Failed to install plugin '$pkg_name'"
    fi
  done <<< "$plugins"
}

deploy_mcp_servers() {
  local runtime="$1"
  local scope="${2:-}"

  local mcp_json="$SHARED_CONFIG_ROOT/mcp_servers.json"
  if [ ! -f "$mcp_json" ]; then
    echo "MCP config not found at $mcp_json, skipping MCP deployment for $runtime"
    return 0
  fi

  if ! command -v "$runtime" >/dev/null 2>&1; then
    echo "WARNING: $runtime CLI not found in PATH. Skipping MCP deployment."
    return 0
  fi

  echo "Deploying MCP servers for $runtime..."

  python3 - "$runtime" "$scope" "$mcp_json" <<'PY'
import json, subprocess, sys

runtime = sys.argv[1]
scope = sys.argv[2]
mcp_json = sys.argv[3]

with open(mcp_json, "r") as f:
    servers = json.load(f)

for name, srv in servers.items():
    print(f"  Configuring MCP server '{name}' for {runtime}...")

    rm_cmd = [runtime, "mcp", "remove"]
    if scope:
        rm_cmd.extend(["-s", scope])
    rm_cmd.append(name)
    subprocess.run(rm_cmd, capture_output=True)

    add_cmd = [runtime, "mcp", "add"]
    if scope:
        add_cmd.extend(["-s", scope])
    add_cmd.extend([name, "--", srv["command"]])
    add_cmd.extend(srv.get("args", []))

    result = subprocess.run(add_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  MCP server '{name}' configured for {runtime}")
    else:
        print(f"  WARNING: Failed to add MCP server '{name}': {result.stderr.strip()}")
PY
}

# Codex 部署
if [ "$TARGET" = "codex" ] || [ "$TARGET" = "all" ]; then
  BACKUP_C="$HOME/.codex-backups/agent-skills-hook-$STAMP"
  mkdir -p "$BACKUP_C/codex" "$BACKUP_C/repo"

  # 备份现有配置
  [ -f "$HOME/.codex/AGENTS.md" ] && cp -a "$HOME/.codex/AGENTS.md" "$BACKUP_C/codex/AGENTS.md"
  [ -e "$HOME/.codex/agents" ] && cp -a "$HOME/.codex/agents" "$BACKUP_C/codex/"
  [ -e "$HOME/.codex/skills" ] && cp -a "$HOME/.codex/skills" "$BACKUP_C/codex/"
  cp -a "$REPO_SKILLS" "$BACKUP_C/repo/"

  # 部署配置（从 config/ 复制）
  mkdir -p "$HOME/.codex"
  safe_link "$HOME/.codex/AGENTS.md" "$CONFIG_ROOT/codex/AGENTS.md"
  safe_link "$HOME/.codex/agents" "$CODEX_AGENTS"

  safe_link "$HOME/.codex/skills" "$REPO_SKILLS"

  if [ -e "$HOME/.agents/skills" ]; then
    echo "Legacy Codex skill root detected at $HOME/.agents/skills. Archive or remove it to avoid duplicate skill scanning."
  fi

  # Deploy MCP servers for Codex
  deploy_mcp_servers "codex"

  echo "Codex deployed. Backup: $BACKUP_C"
fi

# OpenCode 部署
if [ "$TARGET" = "opencode" ] || [ "$TARGET" = "all" ]; then
  BACKUP_O="$HOME/.opencode-backups/agent-skills-hook-$STAMP"
  mkdir -p "$BACKUP_O/opencode" "$BACKUP_O/claude" "$BACKUP_O/repo"

  # 备份现有配置
  [ -f "$HOME/.config/opencode/AGENTS.md" ] && cp -a "$HOME/.config/opencode/AGENTS.md" "$BACKUP_O/opencode/AGENTS.md"
  [ -f "$HOME/.config/opencode/opencode.json" ] && cp -a "$HOME/.config/opencode/opencode.json" "$BACKUP_O/opencode/opencode.json"
  [ -e "$HOME/.config/opencode/skills" ] && cp -a "$HOME/.config/opencode/skills" "$BACKUP_O/opencode/"
  [ -e "$HOME/.config/opencode/agents" ] && cp -a "$HOME/.config/opencode/agents" "$BACKUP_O/opencode/"
  [ -e "$HOME/.claude/skills" ] && cp -a "$HOME/.claude/skills" "$BACKUP_O/claude/"
  cp -a "$REPO_SKILLS" "$BACKUP_O/repo/"

  # 部署配置（从 config/ 复制）
  mkdir -p "$HOME/.config/opencode"
  safe_link "$HOME/.config/opencode/AGENTS.md" "$CONFIG_ROOT/opencode/AGENTS.md"
  merge_json_config "$OPENCODE_CONFIG/opencode.json" "$HOME/.config/opencode/opencode.json"

  # DCP 配置：与 opencode.json 一样走深合并
  merge_json_config "$OPENCODE_CONFIG/dcp.jsonc" "$HOME/.config/opencode/dcp.jsonc"

  safe_link "$HOME/.config/opencode/skills" "$REPO_SKILLS"
  safe_link "$HOME/.config/opencode/agents" "$CONFIG_ROOT/opencode/agents"
  safe_link "$HOME/.claude/skills" "$HOME/.config/opencode/skills"

  install_opencode_plugins "$HOME/.config/opencode"

  if [ -e "$HOME/.agents/skills" ]; then
    echo "Legacy shared skill root detected at $HOME/.agents/skills. OpenCode now uses $HOME/.config/opencode/skills as the primary user skill root."
  fi

  echo "OpenCode deployed. Backup: $BACKUP_O"
fi

# Claude Code 部署
if [ "$TARGET" = "claude" ] || [ "$TARGET" = "all" ]; then
  BACKUP_CL="$HOME/.claude-backups/agent-skills-hook-$STAMP"
  mkdir -p "$BACKUP_CL/claude" "$BACKUP_CL/repo"

  # 备份现有配置
  [ -f "$HOME/.claude/AGENTS.md" ] && cp -a "$HOME/.claude/AGENTS.md" "$BACKUP_CL/claude/AGENTS.md"
  [ -f "$HOME/.claude/CLAUDE.md" ] && cp -a "$HOME/.claude/CLAUDE.md" "$BACKUP_CL/claude/CLAUDE.md"
  [ -e "$HOME/.claude/skills" ] && cp -a "$HOME/.claude/skills" "$BACKUP_CL/claude/"
  cp -a "$REPO_SKILLS" "$BACKUP_CL/repo/"

  # 部署配置（从 config/ 复制）
  mkdir -p "$HOME/.claude"
  safe_link "$HOME/.claude/AGENTS.md" "$CONFIG_ROOT/AGENTS.md"
  safe_link "$HOME/.claude/CLAUDE.md" "$CONFIG_ROOT/claude/CLAUDE.md"

  safe_link "$HOME/.claude/skills" "$REPO_SKILLS"

  # Deploy MCP servers for Claude Code (user scope)
  deploy_mcp_servers "claude" "user"

  echo "Claude Code deployed. Backup: $BACKUP_CL"
fi

# DSH (DeepSeek Harness) 部署
if [ "$TARGET" = "dsh" ] || [ "$TARGET" = "all" ]; then
  BACKUP_D="$HOME/.dsh-backups/agent-skills-hook-$STAMP"
  mkdir -p "$BACKUP_D/dsh" "$BACKUP_D/repo"

  # 备份现有配置
  [ -f "$HOME/.dsh/AGENTS.md" ] && cp -a "$HOME/.dsh/AGENTS.md" "$BACKUP_D/dsh/AGENTS.md"
  [ -e "$HOME/.dsh/skills" ] && cp -a "$HOME/.dsh/skills" "$BACKUP_D/dsh/"
  cp -a "$REPO_SKILLS" "$BACKUP_D/repo/"

  # 部署配置（复用 Claude Code 的 CLAUDE.md 作为 DSH 全局指令）+ skills 软链接
  mkdir -p "$HOME/.dsh"
  safe_link "$HOME/.dsh/AGENTS.md" "$CONFIG_ROOT/claude/CLAUDE.md"
  safe_link "$HOME/.dsh/skills" "$REPO_SKILLS"

  # 部署 MCP servers：注入 dsh-tui profile 的 cordis.patch.yml（幂等）
  DSH_PROFILE_DIR="$HOME/.dsh/profiles/dsh-tui"
  if [ -f "$DSH_PROFILE_DIR/cordis.patch.yml" ]; then
    if grep -q "mcp-context-mode" "$DSH_PROFILE_DIR/cordis.patch.yml" 2>/dev/null; then
      echo "DSH MCP servers already configured."
    else
      python3 - "$SHARED_CONFIG_ROOT/mcp_servers.json" "$DSH_PROFILE_DIR/cordis.patch.yml" <<'PY'
import json, sys

mcp_json, patch_path = sys.argv[1], sys.argv[2]
with open(mcp_json, "r", encoding="utf-8") as f:
    servers = json.load(f)

lines = ["", "# 仓库 MCP servers（agent-skills-hook config/shared/mcp_servers.json）", "- insert:"]
for name, srv in servers.items():
    lines.append(f"    - id: mcp-{name}")
    lines.append("      name: '@deepseek-ai/dsh-mcp-client'")
    lines.append("      config:")
    lines.append(f"        serverName: {name}")
    lines.append("        transport: stdio")
    lines.append(f"        command: {srv['command']}")
    if srv.get("args"):
        args = ", ".join(f"'{a}'" for a in srv["args"])
        lines.append(f"        args: [{args}]")
block = "\n".join(lines) + "\n"

with open(patch_path, "a", encoding="utf-8") as f:
    f.write(block)
print("DSH MCP servers configured in cordis.patch.yml")
PY
    fi
  else
    echo "WARNING: $DSH_PROFILE_DIR/cordis.patch.yml not found. Skipping DSH MCP deployment."
  fi

  echo "DSH deployed. Backup: $BACKUP_D"
fi

echo "Deployment complete."
