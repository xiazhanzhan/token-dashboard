#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/dist}"
STAGE_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/token-dashboard-hosts.XXXXXX")"
MAC_STAGE="$STAGE_PARENT/Token-Dashboard-Host-macOS"
WIN_STAGE="$STAGE_PARENT/Token-Dashboard-Host-Windows-x64"

cleanup() { rm -rf "$STAGE_PARENT"; }
trap cleanup EXIT

mkdir -p "$OUTPUT_DIR"
[[ -f "$PROJECT_ROOT/frontend/dist/index.html" ]] || {
  echo "Frontend build is missing. Run npm --prefix frontend run build first." >&2
  exit 1
}
"$PROJECT_ROOT/scripts/build-agent-templates.sh" "$PROJECT_ROOT/dist/templates" >/dev/null

echo "==> Staging the macOS host"
mkdir -p "$MAC_STAGE/backend" "$MAC_STAGE/frontend" "$MAC_STAGE/dist" "$MAC_STAGE/docs"
cp -R "$PROJECT_ROOT/backend/app" "$MAC_STAGE/backend/app"
cp "$PROJECT_ROOT/backend/requirements.txt" "$MAC_STAGE/backend/"
cp -R "$PROJECT_ROOT/frontend/dist" "$MAC_STAGE/frontend/dist"
cp -R "$PROJECT_ROOT/launchd" "$MAC_STAGE/launchd"
mkdir -p "$MAC_STAGE/scripts"
for item in daily-snapshot.sh server.sh smoke-test.sh uninstall-launch-agent.sh; do
  cp "$PROJECT_ROOT/scripts/$item" "$MAC_STAGE/scripts/"
done
cp "$PROJECT_ROOT/install.command" "$MAC_STAGE/"
cp "$PROJECT_ROOT/Token Dashboard.command" "$MAC_STAGE/"
cp "$PROJECT_ROOT/README.md" "$MAC_STAGE/"
cp "$PROJECT_ROOT/LICENSE" "$MAC_STAGE/"
cp "$PROJECT_ROOT/THIRD_PARTY_NOTICES.md" "$MAC_STAGE/"
cp "$PROJECT_ROOT/docs/CROSS_PLATFORM_DEPLOYMENT.md" "$MAC_STAGE/docs/"
cp "$PROJECT_ROOT/docs/INSTALL-MACOS-HOST.md" "$MAC_STAGE/"
cp -R "$PROJECT_ROOT/dist/templates" "$MAC_STAGE/dist/templates"
cp "$PROJECT_ROOT/mac-host/Create Remote Agent.command" "$MAC_STAGE/"
cp "$PROJECT_ROOT/mac-host/Configure Tailscale Serve.command" "$MAC_STAGE/"
cp "$PROJECT_ROOT/mac-host/Backup Token Dashboard.command" "$MAC_STAGE/"
cp "$PROJECT_ROOT/mac-host/Manage Remote Devices.command" "$MAC_STAGE/"
find "$MAC_STAGE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$MAC_STAGE" -type f -name '*.pyc' -delete
find "$MAC_STAGE" -type f \( -name '*.command' -o -name '*.sh' \) -exec chmod +x {} +

echo "==> Staging the Windows host"
mkdir -p "$WIN_STAGE/backend" "$WIN_STAGE/frontend" "$WIN_STAGE/templates"
cp -R "$PROJECT_ROOT/windows-host/." "$WIN_STAGE/"
cp -R "$PROJECT_ROOT/backend/app" "$WIN_STAGE/backend/app"
cp "$PROJECT_ROOT/backend/requirements-host.txt" "$WIN_STAGE/backend/"
cp -R "$PROJECT_ROOT/frontend/dist/." "$WIN_STAGE/frontend/"
cp "$PROJECT_ROOT/dist/templates/"*.template.zip "$WIN_STAGE/templates/"
cp "$PROJECT_ROOT/docs/INSTALL-WINDOWS-HOST.md" "$WIN_STAGE/"
cp "$PROJECT_ROOT/LICENSE" "$WIN_STAGE/"
cp "$PROJECT_ROOT/THIRD_PARTY_NOTICES.md" "$WIN_STAGE/"
find "$WIN_STAGE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$WIN_STAGE" -type f -name '*.pyc' -delete

echo "==> Running release privacy checks"
if rg -n -P '(?i:/Users/[A-Za-z0-9._-]+/|https://(?!your-)[a-z0-9-]+\.(?!your-)[a-z0-9-]+\.ts\.net)|100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.' "$MAC_STAGE" "$WIN_STAGE"; then
  echo "Host package privacy check failed: a local path or private network address remains." >&2
  exit 1
fi
if find "$MAC_STAGE" "$WIN_STAGE" -type f \( \
  -name 'agent-config*.json' -o -name '*.sqlite*' -o -name '*.db' \
  -o -name '*.log' -o -name '.env*' -o -name '*.jsonl' \
  -o -name '*.pem' -o -name '*.key' -o -name '*.p12' \
\) -print -quit | grep -q .; then
  echo "Host package privacy check failed: a private runtime file remains." >&2
  exit 1
fi

MAC_OUTPUT="$OUTPUT_DIR/Token-Dashboard-Host-macOS.zip"
WIN_OUTPUT="$OUTPUT_DIR/Token-Dashboard-Host-Windows-x64.zip"
rm -f "$MAC_OUTPUT" "$WIN_OUTPUT"
(cd "$STAGE_PARENT" && zip -qr "$MAC_OUTPUT" "$(basename "$MAC_STAGE")")
(cd "$STAGE_PARENT" && zip -qr "$WIN_OUTPUT" "$(basename "$WIN_STAGE")")
chmod 644 "$MAC_OUTPUT" "$WIN_OUTPUT"

echo "$MAC_OUTPUT"
shasum -a 256 "$MAC_OUTPUT"
echo "$WIN_OUTPUT"
shasum -a 256 "$WIN_OUTPUT"
