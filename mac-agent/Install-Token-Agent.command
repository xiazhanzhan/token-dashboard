#!/bin/zsh
set -euo pipefail
umask 077

PACKAGE_ROOT="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/Library/Application Support/Token Dashboard Agent"
RUNTIME_DIR="$INSTALL_DIR/runtime"
CONFIG_SOURCE="$PACKAGE_ROOT/agent-config.json"
CONFIG_TARGET="$INSTALL_DIR/agent-config.json"
PLIST="$HOME/Library/LaunchAgents/com.local.token-dashboard.agent.plist"
LABEL="com.local.token-dashboard.agent"

echo "==> 检查采集端安装包"
PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || { echo "需要先安装 Python 3.9 或更高版本。" >&2; exit 1; }
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
  echo "需要先安装 Python 3.9 或更高版本。" >&2
  exit 1
}
[[ -f "$CONFIG_SOURCE" ]] || { echo "安装包缺少 agent-config.json。" >&2; exit 1; }
[[ -d "$PACKAGE_ROOT/runtime/app" ]] || { echo "安装包缺少采集程序。" >&2; exit 1; }

echo "==> 安装到 $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$HOME/Library/LaunchAgents"
chmod 700 "$INSTALL_DIR"
rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"
cp -R "$PACKAGE_ROOT/runtime/app" "$RUNTIME_DIR/app"
cp "$CONFIG_SOURCE" "$CONFIG_TARGET"
cp "$PACKAGE_ROOT/Uninstall-Token-Agent.command" "$INSTALL_DIR/Uninstall-Token-Agent.command"
cp "$PACKAGE_ROOT/README-macOS.txt" "$INSTALL_DIR/README-macOS.txt"
chmod +x "$INSTALL_DIR/Uninstall-Token-Agent.command"

"$PYTHON" - "$CONFIG_TARGET" "$INSTALL_DIR" "$HOME" <<'PY'
import json, os, sys
from pathlib import Path

path, install_dir, home = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
config = json.loads(path.read_text(encoding="utf-8"))
name = str(config.get("device_name") or "Mac")
config.update({
    "platform": "macos",
    "profile_id": "macos-native",
    "data_dir": install_dir,
    "codex_home": str(home / ".codex"),
    "hermes_database_path": str(home / ".hermes" / "state.db"),
    "account_keys": {"codex": "codex", "hermes": "hermes"},
    "account_labels": {
        "codex": f"Codex · {name}",
        "hermes": f"Hermes · {name}",
    },
})
path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
os.chmod(path, 0o600)
PY

echo "==> 配置每分钟自动同步"
"$PYTHON" - "$PLIST" "$LABEL" "$PYTHON" "$RUNTIME_DIR" "$CONFIG_TARGET" "$INSTALL_DIR" <<'PY'
import os, plistlib, sys
from pathlib import Path

plist, label, python, runtime, config, install = sys.argv[1:]
payload = {
    "Label": label,
    "ProgramArguments": [python, "-m", "app.agent", "--config", config, "run"],
    "WorkingDirectory": runtime,
    "EnvironmentVariables": {"PYTHONPATH": runtime},
    "RunAtLoad": True,
    "KeepAlive": True,
    "ProcessType": "Background",
    "ThrottleInterval": 30,
    "Umask": 63,
    "StandardOutPath": str(Path(install) / "launchd.log"),
    "StandardErrorPath": str(Path(install) / "launchd-error.log"),
}
with open(plist, "wb") as handle:
    plistlib.dump(payload, handle)
os.chmod(plist, 0o600)
PY

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$PLIST"
launchctl enable "gui/$UID/$LABEL"

# Delete the transport copy of the credential after it is protected in the
# private application directory.
rm -f "$CONFIG_SOURCE"

echo "==> 尝试首次同步"
if ! PYTHONPATH="$RUNTIME_DIR" "$PYTHON" -m app.agent --config "$CONFIG_TARGET" sync; then
  echo "首次连接暂时失败；后台采集端会在网络恢复后自动重试。" >&2
fi

echo
echo "安装完成。此 Mac 会每 60 秒向中心主机提交一次 Token 统计。"
echo "按回车关闭窗口。"
read -r _
