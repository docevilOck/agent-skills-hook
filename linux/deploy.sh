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
SEMBLE_REPO_CACHE="$REPO_ROOT/third_party/semble/huggingface/hub/models--minishlab--potion-code-16M"
SEMBLE_HUB_ROOT="$HOME/.cache/huggingface/hub"
SEMBLE_HUB_CACHE="$SEMBLE_HUB_ROOT/models--minishlab--potion-code-16M"

if [ ! -d "$REPO_SKILLS" ]; then
  echo "ERROR: $REPO_SKILLS missing. Run 'git submodule update --init --recursive agents/skills' first." >&2
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

merge_missing_skills() {
  local src="$1"
  local real="$src"
  [ -e "$src" ] || return 0
  if [ -L "$src" ]; then
    real="$(readlink -f "$src" 2>/dev/null || true)"
  fi
  [ -d "$real" ] || return 0

  shopt -s nullglob dotglob
  for item in "$real"/*; do
    [ -e "$item" ] || continue
    local name
    name="$(basename "$item")"
    if [ ! -e "$REPO_SKILLS/$name" ]; then
      cp -a "$item" "$REPO_SKILLS/"
    fi
  done
  shopt -u nullglob dotglob
}

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

ensure_semble_installed() {
  if command -v semble >/dev/null 2>&1; then
    echo "Semble already installed: $(command -v semble)"
    return 0
  fi

  echo "Semble not found. Installing semble[mcp]..."
  python -m pip install "semble[mcp]"
}

sync_semble_model_cache() {
  mkdir -p "$SEMBLE_HUB_ROOT"

  if [ ! -d "$SEMBLE_REPO_CACHE" ]; then
    echo "Semble repo cache not found at $SEMBLE_REPO_CACHE"
    echo "Skip cache sync. First run on a networked machine, then export the cache into the repo."
    return 0
  fi

  rm -rf "$SEMBLE_HUB_CACHE"
  cp -a "$SEMBLE_REPO_CACHE" "$SEMBLE_HUB_CACHE"
  echo "Semble model cache synced to $SEMBLE_HUB_CACHE"
}

ensure_codex_semble_mcp() {
  if codex mcp get semble >/tmp/codex_semble_get.txt 2>/dev/null; then
    if grep -q 'command: semble' /tmp/codex_semble_get.txt && grep -q 'HF_HUB_DISABLE_SYMLINKS' /tmp/codex_semble_get.txt; then
      echo "Codex MCP 'semble' already configured."
      rm -f /tmp/codex_semble_get.txt
      return 0
    fi
    codex mcp remove semble >/dev/null 2>&1 || true
  fi

  rm -f /tmp/codex_semble_get.txt
  codex mcp add semble --env HF_HUB_DISABLE_SYMLINKS=1 --env HF_HUB_DISABLE_SYMLINKS_WARNING=1 -- semble
  echo "Codex MCP 'semble' configured."
}

ensure_semble_installed
sync_semble_model_cache
ensure_codex_semble_mcp

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
  cp -a "$CONFIG_ROOT/codex/AGENTS.md" "$HOME/.codex/AGENTS.md"
  safe_link "$HOME/.codex/agents" "$CODEX_AGENTS"

  # 合并 skills
  merge_missing_skills "$HOME/.codex/skills"

  # 创建软链接
  safe_link "$HOME/.codex/skills" "$REPO_SKILLS"

  if [ -e "$HOME/.agents/skills" ]; then
    echo "Legacy Codex skill root detected at $HOME/.agents/skills. Archive or remove it to avoid duplicate skill scanning."
  fi

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
  [ -e "$HOME/.claude/skills" ] && cp -a "$HOME/.claude/skills" "$BACKUP_O/claude/"
  cp -a "$REPO_SKILLS" "$BACKUP_O/repo/"

  # 部署配置（从 config/ 复制）
  mkdir -p "$HOME/.config/opencode"
  cp -a "$CONFIG_ROOT/opencode/AGENTS.md" "$HOME/.config/opencode/AGENTS.md"
  merge_json_config "$OPENCODE_CONFIG/opencode.json" "$HOME/.config/opencode/opencode.json"

  # 合并 skills
  merge_missing_skills "$HOME/.config/opencode/skills"
  merge_missing_skills "$HOME/.claude/skills"

  # 创建软链接
  safe_link "$HOME/.config/opencode/skills" "$REPO_SKILLS"
  safe_link "$HOME/.claude/skills" "$HOME/.config/opencode/skills"

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
  cp -a "$CONFIG_ROOT/AGENTS.md" "$HOME/.claude/AGENTS.md"
  cp -a "$CONFIG_ROOT/claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md"

  # 合并 skills
  merge_missing_skills "$HOME/.claude/skills"

  # 创建软链接
  safe_link "$HOME/.claude/skills" "$REPO_SKILLS"

  echo "Claude Code deployed. Backup: $BACKUP_CL"
fi

# Qoder 部署（默认行为，每次运行无条件执行）
BACKUP_Q="$HOME/.qoder-backups/agent-skills-hook-$STAMP"
mkdir -p "$BACKUP_Q/qoder" "$BACKUP_Q/repo"

# 备份现有配置
[ -f "$HOME/.qoder/AGENTS.md" ] && cp -a "$HOME/.qoder/AGENTS.md" "$BACKUP_Q/qoder/AGENTS.md"
[ -e "$HOME/.qoder/skills" ] && cp -a "$HOME/.qoder/skills" "$BACKUP_Q/qoder/"
cp -a "$REPO_SKILLS" "$BACKUP_Q/repo/"

# 部署配置（从 config/qoder/ 复制）
mkdir -p "$HOME/.qoder"
cp -a "$CONFIG_ROOT/qoder/AGENTS.md" "$HOME/.qoder/AGENTS.md"

# 合并 skills
merge_missing_skills "$HOME/.qoder/skills"

# 创建软链接
safe_link "$HOME/.qoder/skills" "$REPO_SKILLS"

echo "Qoder deployed. Backup: $BACKUP_Q"

echo "Deployment complete."
