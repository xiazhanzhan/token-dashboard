#!/bin/zsh
set -euo pipefail

TAILSCALE="$(command -v tailscale || true)"
[[ -n "$TAILSCALE" ]] || TAILSCALE="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
[[ -x "$TAILSCALE" ]] || { echo "请先安装并登录 Tailscale。" >&2; exit 1; }

echo "正在把本地看板发布到你自己的 Tailscale 网络……"
"$TAILSCALE" serve --bg http://127.0.0.1:8765
echo
echo "配置完成。上方显示的 HTTPS 地址仅供你的 Tailnet 使用。"
echo "不要启用 Funnel。"
echo "按回车关闭窗口。"
read -r _
