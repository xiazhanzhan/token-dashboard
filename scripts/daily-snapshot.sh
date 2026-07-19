#!/bin/zsh
set -euo pipefail
umask 077

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Token Dashboard Python 环境不存在，请先运行 install.command" >&2
  exit 1
fi

cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/backend"
"$PYTHON" -m app.cli snapshot
