#!/bin/zsh
set -euo pipefail

LABEL="com.local.token-dashboard.agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
rm -f "$PLIST"

echo "后台采集任务已移除。"
echo "历史队列与配置仍保留在："
echo "  $HOME/Library/Application Support/Token Dashboard Agent"
echo "如不再使用，请在中心主机吊销该设备后再手动删除此目录。"
echo "按回车关闭窗口。"
read -r _
