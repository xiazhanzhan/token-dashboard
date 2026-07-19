#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
[[ -d "$PROJECT_ROOT/backend" ]] || PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "请先运行 install.command 安装中心看板。" >&2; exit 1; }

echo "创建一台远程采集设备"
printf "设备名称（例如 Work-MacBook）："
read -r DEVICE_NAME
[[ -n "$DEVICE_NAME" ]] || { echo "设备名称不能为空。" >&2; exit 1; }
printf "设备系统（输入 W 表示 Windows，M 表示 macOS）："
read -r PLATFORM_INPUT
case "${PLATFORM_INPUT:l}" in
  w|win|windows) PLATFORM="windows"; TEMPLATE="Token-Dashboard-Agent-Windows-x64.template.zip" ;;
  m|mac|macos) PLATFORM="macos"; TEMPLATE="Token-Dashboard-Agent-macOS.template.zip" ;;
  *) echo "系统必须选择 Windows 或 macOS。" >&2; exit 1 ;;
esac

TAILSCALE="$(command -v tailscale || true)"
[[ -n "$TAILSCALE" ]] || TAILSCALE="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
DEFAULT_SERVER=""
if [[ -x "$TAILSCALE" ]]; then
  DEFAULT_SERVER="$($TAILSCALE status --json 2>/dev/null | python3 -c '
import json,sys
try:
    name=json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip(".")
    print("https://"+name if name else "")
except Exception:
    print("")
' || true)"
fi
if [[ -n "$DEFAULT_SERVER" ]]; then
  printf "中心主机 HTTPS 地址 [%s]：" "$DEFAULT_SERVER"
else
  printf "中心主机的 Tailscale HTTPS 地址："
fi
read -r SERVER_URL
SERVER_URL="${SERVER_URL:-$DEFAULT_SERVER}"
[[ -n "$SERVER_URL" ]] || { echo "中心主机地址不能为空。" >&2; exit 1; }

SAFE_NAME="$(printf '%s' "$DEVICE_NAME" | tr -cs '[:alnum:]_-' '-' | sed 's/^-//;s/-$//')"
[[ -n "$SAFE_NAME" ]] || SAFE_NAME="device"
OUTPUT="$HOME/Downloads/Token-Dashboard-Agent-$SAFE_NAME-$PLATFORM.zip"

cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON" -m app.cli package-agent \
  --name "$DEVICE_NAME" \
  --platform "$PLATFORM" \
  --server "$SERVER_URL" \
  --template "$PROJECT_ROOT/dist/templates/$TEMPLATE" \
  --output "$OUTPUT"

echo
echo "采集端安装包已生成："
echo "  $OUTPUT"
echo "只发送给对应设备，安装成功后删除传输副本。"
echo "按回车关闭窗口。"
read -r _
