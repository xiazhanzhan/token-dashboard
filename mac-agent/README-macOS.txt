Token Dashboard macOS 采集端
================================

用途：
  安装在需要被统计的 Mac 上，将 Codex 和 Hermes Token 计数提交到
  另一台 Mac 或 Windows 中心主机。

安装：
  1. 先安装并登录 Tailscale，加入中心主机所属的 Tailnet。
  2. 解压此安装包。
  3. 双击“Install-Token-Agent.command”。
  4. macOS 如提示安全确认，请选择允许。

隐私：
  - 只提交模型、时间与 Token 计数。
  - 不提交提示词、消息正文、API Key 或 Codex/Hermes 认证文件。
  - 此 ZIP 含本设备独立密钥，安装成功后请删除 ZIP 和传输副本。

卸载：
  双击“Uninstall-Token-Agent.command”，然后请中心主机管理员吊销设备。
