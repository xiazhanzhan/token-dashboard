#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/dist/templates}"
PYTHON_VERSION="3.13.14"
PYTHON_ZIP="python-$PYTHON_VERSION-embed-amd64.zip"
PYTHON_URL="https://www.python.org/ftp/python/$PYTHON_VERSION/$PYTHON_ZIP"
PYTHON_SHA256="90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"
CACHE_DIR="$PROJECT_ROOT/.build-cache"
STAGE_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/token-dashboard-templates.XXXXXX")"

cleanup() { rm -rf "$STAGE_PARENT"; }
trap cleanup EXIT

mkdir -p "$OUTPUT_DIR" "$CACHE_DIR"
if [[ ! -f "$CACHE_DIR/$PYTHON_ZIP" ]]; then
  curl --fail --location --progress-bar "$PYTHON_URL" -o "$CACHE_DIR/$PYTHON_ZIP"
fi
ACTUAL="$(shasum -a 256 "$CACHE_DIR/$PYTHON_ZIP" | awk '{print $1}')"
[[ "$ACTUAL" == "$PYTHON_SHA256" ]] || {
  echo "Python runtime SHA-256 mismatch: $ACTUAL" >&2
  exit 1
}

WINDOWS="$STAGE_PARENT/windows"
mkdir -p "$WINDOWS/runtime"
unzip -q "$CACHE_DIR/$PYTHON_ZIP" -d "$WINDOWS/runtime"
cat > "$WINDOWS/runtime/python313._pth" <<'EOF'
python313.zip
.
import site
EOF
cp -R "$PROJECT_ROOT/backend/app" "$WINDOWS/runtime/app"
find "$WINDOWS/runtime/app" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$WINDOWS/runtime/app" -type f -name '*.pyc' -delete
CERTIFI_DIR="$("$PROJECT_ROOT/backend/.venv/bin/python" -c \
  'import certifi; from pathlib import Path; print(Path(certifi.__file__).parent)')"
cp -R "$CERTIFI_DIR" "$WINDOWS/runtime/certifi"
cp "$PROJECT_ROOT/windows-agent/Install-Token-Agent.cmd" "$WINDOWS/"
cp "$PROJECT_ROOT/windows-agent/install-agent.ps1" "$WINDOWS/"
cp "$PROJECT_ROOT/windows-agent/sync-agent.ps1" "$WINDOWS/"
cp "$PROJECT_ROOT/windows-agent/wsl-hermes-export.py" "$WINDOWS/"
cp "$PROJECT_ROOT/windows-agent/Uninstall-Token-Agent.cmd" "$WINDOWS/"
cp "$PROJECT_ROOT/windows-agent/README-Windows.txt" "$WINDOWS/"
cp "$PROJECT_ROOT/LICENSE" "$WINDOWS/"
cp "$PROJECT_ROOT/THIRD_PARTY_NOTICES.md" "$WINDOWS/"

MACOS="$STAGE_PARENT/macos"
mkdir -p "$MACOS/runtime"
cp -R "$PROJECT_ROOT/backend/app" "$MACOS/runtime/app"
find "$MACOS/runtime/app" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$MACOS/runtime/app" -type f -name '*.pyc' -delete
cp "$PROJECT_ROOT/mac-agent/Install-Token-Agent.command" "$MACOS/"
cp "$PROJECT_ROOT/mac-agent/Uninstall-Token-Agent.command" "$MACOS/"
cp "$PROJECT_ROOT/mac-agent/README-macOS.txt" "$MACOS/"
cp "$PROJECT_ROOT/LICENSE" "$MACOS/"
cp "$PROJECT_ROOT/THIRD_PARTY_NOTICES.md" "$MACOS/"
chmod +x "$MACOS"/*.command

WINDOWS_OUTPUT="$OUTPUT_DIR/Token-Dashboard-Agent-Windows-x64.template.zip"
MACOS_OUTPUT="$OUTPUT_DIR/Token-Dashboard-Agent-macOS.template.zip"
rm -f "$WINDOWS_OUTPUT" "$MACOS_OUTPUT"
(cd "$WINDOWS" && zip -qr "$WINDOWS_OUTPUT" .)
(cd "$MACOS" && zip -qr "$MACOS_OUTPUT" .)
chmod 644 "$WINDOWS_OUTPUT" "$MACOS_OUTPUT"

for template in "$WINDOWS_OUTPUT" "$MACOS_OUTPUT"; do
  if unzip -l "$template" | grep -q 'agent-config.json'; then
    echo "Template privacy check failed: a credential file was included." >&2
    exit 1
  fi
done

echo "$WINDOWS_OUTPUT"
shasum -a 256 "$WINDOWS_OUTPUT"
echo "$MACOS_OUTPUT"
shasum -a 256 "$MACOS_OUTPUT"
