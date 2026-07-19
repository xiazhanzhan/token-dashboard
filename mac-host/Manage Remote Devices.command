#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
[[ -d "$PROJECT_ROOT/backend" ]] || PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "请先安装 Token Dashboard。" >&2; exit 1; }

echo "当前设备："
PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON" -m app.cli devices
echo
printf "如需吊销设备，请输入 dev_ 开头的设备 ID；只查看请直接回车："
read -r DEVICE_ID
if [[ -n "$DEVICE_ID" ]]; then
  [[ "$DEVICE_ID" == dev_* ]] || { echo "设备 ID 格式不正确。" >&2; exit 1; }
  printf "输入 REVOKE 确认吊销 %s：" "$DEVICE_ID"
  read -r CONFIRM
  [[ "$CONFIRM" == "REVOKE" ]] || { echo "已取消。"; exit 0; }
  PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON" -m app.cli revoke-device "$DEVICE_ID"
  echo "设备已吊销；它以后不能再上传数据，既有历史仍保留。"
fi
echo "按回车关闭窗口。"
read -r _
