#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${1:-}"
OUTPUT="${2:-$PROJECT_ROOT/dist/Token-Dashboard-Agent-macOS.zip}"
TEMPLATE_DIR="$PROJECT_ROOT/dist/templates"
TEMPLATE="$TEMPLATE_DIR/Token-Dashboard-Agent-macOS.template.zip"

if [[ -z "$CONFIG" || ! -f "$CONFIG" ]]; then
  echo "Usage: $0 /path/to/agent-config.json [output.zip]" >&2
  exit 2
fi

"$PROJECT_ROOT/scripts/build-agent-templates.sh" "$TEMPLATE_DIR" >/dev/null
PYTHONPATH="$PROJECT_ROOT/backend" "$PROJECT_ROOT/backend/.venv/bin/python" - \
  "$TEMPLATE" "$CONFIG" "$OUTPUT" <<'PY'
import json, sys
from pathlib import Path
from app.deployment import package_agent

template, config_path, output = map(Path, sys.argv[1:])
config = json.loads(config_path.read_text(encoding="utf-8"))
package_agent(template, output, config)
PY
echo "$OUTPUT"
shasum -a 256 "$OUTPUT"
