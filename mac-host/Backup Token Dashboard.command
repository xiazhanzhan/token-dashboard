#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
[[ -d "$PROJECT_ROOT/backend" ]] || PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "请先安装 Token Dashboard。" >&2; exit 1; }

BACKUP_DIR="$HOME/Documents/Token Dashboard Backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
OUTPUT="$BACKUP_DIR/token-dashboard-$(date +%Y%m%d-%H%M%S).sqlite3"

PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON" -m app.cli backup --output "$OUTPUT"
echo
echo "备份完成："
echo "  $OUTPUT"
echo "备份包含完整 Token 历史和设备信息，请勿上传到公共网盘。"
echo "按回车关闭窗口。"
read -r _
