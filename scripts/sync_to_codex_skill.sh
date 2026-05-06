#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TARGET_ROOT="${2:-/Users/richardq/.codex/skills/Trade Lens}"
BACKUP_ROOT="${3:-/Users/richardq/.codex/skills/.backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/Trade Lens-${STAMP}"

mkdir -p "${TARGET_ROOT}" "${BACKUP_ROOT}"

rsync -a \
  --exclude 'analysis_history/' \
  --exclude 'background.md' \
  --exclude 'assets.md' \
  --exclude 'trade.md' \
  --exclude 'market_data.md' \
  --exclude '.env' \
  --exclude '*.env' \
  --exclude '*.key' \
  --exclude '*.pem' \
  --exclude 'secrets.*' \
  --exclude 'credentials.*' \
  --exclude 'token.*' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  "${TARGET_ROOT}/" "${BACKUP_DIR}/"

rsync -a --delete \
  --exclude '.git/' \
  --exclude '.gitignore' \
  --exclude 'analysis_history/' \
  --exclude 'background.md' \
  --exclude 'assets.md' \
  --exclude 'trade.md' \
  --exclude 'market_data.md' \
  --exclude '.env' \
  --exclude '*.env' \
  --exclude '*.key' \
  --exclude '*.pem' \
  --exclude 'secrets.*' \
  --exclude 'credentials.*' \
  --exclude 'token.*' \
  --exclude 'Trade Lens/' \
  --exclude 'SKILL 2.md' \
  --exclude 'SKILL 3.md' \
  --exclude 'agents/openai 2.yaml' \
  --exclude 'templates/* 2.md' \
  --exclude 'templates/* 3.md' \
  --exclude 'templates/* 4.md' \
  --exclude 'src/tradelens/data/providers/futu_provider 2.py' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  "${SOURCE_ROOT}/" "${TARGET_ROOT}/"

echo "Synced ${SOURCE_ROOT} -> ${TARGET_ROOT}"
echo "Backup: ${BACKUP_DIR}"
