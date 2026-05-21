#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(dirname "$SCRIPT_DIR")}"
SRC="${HOME}/.cache/huggingface/hub/models--minishlab--potion-code-16M"
DEST="${REPO_ROOT}/third_party/semble/huggingface/hub/models--minishlab--potion-code-16M"

if [ ! -d "$SRC" ]; then
  echo "ERROR: local Semble model cache not found at $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SRC" "$DEST"

echo "Exported Semble model cache to $DEST"
