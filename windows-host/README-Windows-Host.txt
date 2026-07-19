Token Dashboard - Windows 中心主机
==================================

这是一套独立部署，不会连接安装包制作者的数据库或 Tailscale 网络。

安装前：
  1. Windows 10/11 x64。
  2. 安装 Python 3.9 或更高版本，并勾选 Add Python to PATH。
  3. 如需接收其他电脑数据，安装并登录自己的 Tailscale。

安装：
  双击 Install-Token-Dashboard.cmd。

安装后：
  - 本机看板：http://127.0.0.1:8765
  - 桌面会创建看板、添加设备、设备管理、备份和 Tailscale 快捷方式。
  - 首次运行 Configure-Tailscale-Serve.cmd，使看板只在 Tailnet 内可访问。
  - 每增加一台电脑，运行 Create-Remote-Agent.cmd，选择 Windows 或 macOS。
  - 将生成的 ZIP 只交给对应设备，安装后删除 ZIP。
  - 使用 Token Dashboard - Backup 创建一致性数据库备份。

安全边界：
  - Web 服务始终只绑定 127.0.0.1，不开放局域网或公网端口。
  - Tailscale Serve 仅用于自己的 Tailnet；不要使用 Funnel。
  - 每台采集端有独立、可吊销的写入密钥。
  - 数据库只保存在 %LOCALAPPDATA%\Token Dashboard。
  - 不上传提示词、消息、API Key 或认证文件。

后台任务：
  - Token Dashboard Host：登录后自动启动中心服务。
  - Token Dashboard Agent：每分钟采集本机 native/WSL 数据。
  - Token Dashboard Daily Snapshot：每天 00:05 保存快照，错过后补跑。
