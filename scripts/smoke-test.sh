#!/bin/zsh
set -euo pipefail

URL="${TOKEN_DASHBOARD_URL:-http://127.0.0.1:8765}"

health="$(curl --silent --show-error --fail "$URL/api/health")"
summary="$(curl --silent --show-error --fail "$URL/api/summary")"
page="$(curl --silent --show-error --fail "$URL/")"

python3 - "$health" "$summary" <<'PY'
import json, sys
health = json.loads(sys.argv[1])
summary = json.loads(sys.argv[2])
assert health["status"] in {"ok", "partial"}, health
assert set(health["sources"]) == {"codex", "hermes"}
assert set(summary["periods"]) == {"today", "week", "month", "year"}
assert summary["periods"]["year"]["current"]["totalTokens"] >= 0
print("API smoke test passed:", health["status"])
PY

if [[ "$page" != *"Token 仪表盘"* ]]; then
  echo "前端 HTML 未包含预期标题" >&2
  exit 1
fi

echo "Frontend smoke test passed: $URL"
