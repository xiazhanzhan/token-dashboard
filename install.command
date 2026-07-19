#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "==> 检查运行环境"
command -v python3 >/dev/null || { echo "需要 Python 3" >&2; exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
  echo "需要 Python 3.9 或更高版本" >&2
  exit 1
}

echo "==> 安装 Python 环境"
if [[ ! -x backend/.venv/bin/python ]]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements.txt

echo "==> 安装并构建前端"
if [[ -f frontend/dist/index.html && "${TOKEN_DASHBOARD_REBUILD_FRONTEND:-0}" != "1" ]]; then
  echo "    使用安装包内已构建的看板"
else
  command -v node >/dev/null || { echo "重新构建前端需要 Node.js" >&2; exit 1; }
  command -v npm >/dev/null || { echo "重新构建前端需要 npm" >&2; exit 1; }
  if [[ -f frontend/package-lock.json ]]; then
    npm --prefix frontend ci --silent
  else
    npm --prefix frontend install --silent
  fi
  npm --prefix frontend run build
fi

echo "==> 配置每日快照任务"
chmod +x "Token Dashboard.command" scripts/*.sh
LOG_DIR="$HOME/Library/Logs/Token Dashboard"
DATA_DIR="$HOME/Library/Application Support/Token Dashboard"
PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR" "$DATA_DIR" "$PLIST_DIR"
chmod 700 "$LOG_DIR" "$DATA_DIR"

escape_sed() {
  printf '%s' "$1" | sed 's/[&|]/\\&/g'
}

PROJECT_ESCAPED="$(escape_sed "$PROJECT_ROOT")"
LOG_ESCAPED="$(escape_sed "$LOG_DIR")"

install_agent() {
  local label="$1"
  local template="$2"
  local plist="$PLIST_DIR/$label.plist"
  sed \
    -e "s|__PROJECT_ROOT__|$PROJECT_ESCAPED|g" \
    -e "s|__LOG_DIR__|$LOG_ESCAPED|g" \
    "$template" > "$plist"
  plutil -lint "$plist"
  launchctl bootout "gui/$UID/$label" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$UID" "$plist"
  launchctl enable "gui/$UID/$label"
}

install_agent \
  "com.local.token-dashboard.snapshot" \
  launchd/com.local.token-dashboard.snapshot.plist.template
install_agent \
  "com.local.token-dashboard.server" \
  launchd/com.local.token-dashboard.server.plist.template

echo "==> 首次同步与历史快照"
PYTHONPATH="$PROJECT_ROOT/backend" backend/.venv/bin/python -m app.cli snapshot >/dev/null

echo
echo "安装完成。以后双击："
echo "  $PROJECT_ROOT/Token Dashboard.command"
echo "本地地址：http://127.0.0.1:8765"
echo "按回车关闭此窗口。"
read -r _
