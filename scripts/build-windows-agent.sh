#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${1:-}"
OUTPUT="${2:-$PROJECT_ROOT/dist/Token-Dashboard-Agent-Windows-x64.zip}"
TEMPLATE_DIR="$PROJECT_ROOT/dist/templates"
TEMPLATE="$TEMPLATE_DIR/Token-Dashboard-Agent-Windows-x64.template.zip"
STAGE="$PROJECT_ROOT/.build/windows-agent-configured"

cleanup() {
  python3 - "$STAGE" <<'PY'
from pathlib import Path
import shutil, sys
stage = Path(sys.argv[1])
if stage.exists():
    shutil.rmtree(stage)
PY
}
trap cleanup EXIT

if [[ -z "$CONFIG" || ! -f "$CONFIG" ]]; then
  echo "Usage: $0 /path/to/agent-config.json [output.zip]" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUTPUT")" "$PROJECT_ROOT/.build"
"$PROJECT_ROOT/scripts/build-agent-templates.sh" "$TEMPLATE_DIR" >/dev/null

python3 - "$STAGE" <<'PY'
from pathlib import Path
import shutil, sys
stage = Path(sys.argv[1])
if stage.exists():
    shutil.rmtree(stage)
PY
mkdir -p "$STAGE"
unzip -q "$TEMPLATE" -d "$STAGE"
cp "$CONFIG" "$STAGE/agent-config.json"

(cd "$STAGE" && zip -qr "$OUTPUT" .)
chmod 600 "$OUTPUT"
echo "$OUTPUT"
shasum -a 256 "$OUTPUT"
