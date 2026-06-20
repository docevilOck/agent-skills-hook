#!/usr/bin/env bash
# append-findings.sh — 在 findings/ 下创建标准化决策文件
# 用法: append-findings.sh <target> <subdir> <topic> <type> <content-file>
#   target: findings 或 daily
#   subdir: spec|detail|review|gate
#   topic:  决策主题（用于文件名）
#   type:   类型标签
#   content-file: 包含决策内容的临时文件路径

set -euo pipefail

TARGET="${1:-}"
SUBDIR="${2:-}"
TOPIC="${3:-}"
TYPE="${4:-}"
CONTENT_FILE="${5:-}"

if [ -z "$TARGET" ] || [ -z "$SUBDIR" ] || [ -z "$TOPIC" ] || [ -z "$TYPE" ] || [ -z "$CONTENT_FILE" ]; then
  echo "用法: append-findings.sh <target> <subdir> <topic> <type> <content-file>" >&2
  exit 1
fi

DATE_PREFIX="$(date +%y-%m-%d)"
TIMESTAMP_LONG="$(date +%Y-%m-%d)"
FILENAME="${DATE_PREFIX}_${TOPIC}.md"
PROJECT="$(basename "$(pwd)")"

if [ "$TARGET" = "daily" ]; then
  BASE_DIR="${HOME}/.config/opencode/daily"
  OUTPUT="${BASE_DIR}/${FILENAME}"
else
  BASE_DIR="./findings/${SUBDIR}"
  OUTPUT="${BASE_DIR}/${FILENAME}"
fi

mkdir -p "$(dirname "$OUTPUT")"

{
  echo "# ${TOPIC}"
  echo ""
  echo "> 日期：${TIMESTAMP_LONG} | 项目：${PROJECT} | 类型：${TYPE}"
  echo ""
  cat "$CONTENT_FILE"
} > "$OUTPUT"

echo "findings: ${OUTPUT}"

rm -f "$CONTENT_FILE"
