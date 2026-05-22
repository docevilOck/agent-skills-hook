#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(dirname "$SCRIPT_DIR")}"
SRC="${HOME}/.cache/huggingface/hub/models--minishlab--potion-code-16M"
DEST="${REPO_ROOT}/third_party/semble/huggingface/hub/models--minishlab--potion-code-16M"
SNAPSHOT_REL="snapshots/86848193a842865570d9c8d3e7d268b66ab52752/model.safetensors"
MIN_BINARY_BYTES=1048576

is_semble_pointer_file() {
  local path="$1"
  [ -f "$path" ] || return 1
  local first_line
  first_line="$(head -n 1 "$path" 2>/dev/null || true)"
  [ "$first_line" = "version https://git-lfs.github.com/spec/v1" ]
}

assert_semble_local_cache_valid() {
  local cache_root="$1"
  local snapshot_file="$cache_root/$SNAPSHOT_REL"

  if [ ! -f "$snapshot_file" ]; then
    echo "ERROR: local Semble snapshot not found at $snapshot_file" >&2
    return 1
  fi

  local size
  size="$(wc -c < "$snapshot_file")"
  if [ "$size" -lt "$MIN_BINARY_BYTES" ] || is_semble_pointer_file "$snapshot_file"; then
    echo "ERROR: local Semble snapshot is not a valid binary safetensors file: $snapshot_file" >&2
    return 1
  fi
}

if [ ! -d "$SRC" ]; then
  echo "ERROR: local Semble model cache not found at $SRC" >&2
  exit 1
fi

assert_semble_local_cache_valid "$SRC"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SRC" "$DEST"

echo "Exported Semble model cache to $DEST"
