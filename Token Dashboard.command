#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765"
PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"

if curl --silent --fail "$URL/api/health" >/dev/null 2>&1; then
  open "$URL"
  exit 0
fi

if [[ ! -x "$PYTHON" || ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]]; then
  echo "尚未安装 Token Dashboard，正在运行安装程序……"
  "$PROJECT_ROOT/install.command"
fi

SERVER_LABEL="com.local.token-dashboard.server"
SERVER_PLIST="$HOME/Library/LaunchAgents/$SERVER_LABEL.plist"
if [[ -f "$SERVER_PLIST" ]]; then
  launchctl kickstart "gui/$UID/$SERVER_LABEL" >/dev/null 2>&1 || true
  for _ in {1..40}; do
    if curl --silent --fail "$URL/api/health" >/dev/null 2>&1; then
      open "$URL"
      exit 0
    fi
    sleep 0.25
  done
fi

cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/backend"

echo "Token Dashboard 正在启动：http://127.0.0.1:8765"
echo "关闭本窗口或按 Control-C 可停止本次备用服务；后台服务和每日快照不受影响。"

"$PYTHON" -m uvicorn app.main:app \
  --app-dir "$PROJECT_ROOT/backend" \
  --host 127.0.0.1 \
  --port 8765 \
  --no-access-log &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for _ in {1..80}; do
  if curl --silent --fail "$URL/api/health" >/dev/null 2>&1; then
    open "$URL"
    wait "$SERVER_PID"
    exit $?
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "服务启动失败；请确认 8765 端口没有被其他程序占用。" >&2
    wait "$SERVER_PID"
    exit $?
  fi
  sleep 0.25
done

echo "服务启动超时。" >&2
exit 1
