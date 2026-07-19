#!/bin/zsh
set -euo pipefail

for LABEL in \
  "com.local.token-dashboard.snapshot" \
  "com.local.token-dashboard.server"; do
  PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  echo "已移除 $LABEL"
done
echo "看板程序和本地统计数据均保留。"
