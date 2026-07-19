# Codex + Hermes Token Dashboard

## 多设备多账号 Token 统计平台

> 非官方社区项目，与 OpenAI、Codex、Hermes 及相关厂商不存在隶属、授权或背书关系。

当前公开版本为 **0.1.0 预览版**。macOS 流程已完成本机验证；Windows Host 安装器仍建议在代表性的 Windows 10/11 x64 设备上完成最终端到端验收。

一个自托管在个人电脑或家庭服务器上的 Token 用量统计看板，统一读取：

- Codex：`~/.codex/sessions/**/*.jsonl` 与 `~/.codex/archived_sessions/*.jsonl`
- Hermes：`~/.hermes/state.db`

界面提供今日、本周、本月、今年汇总，日/周/月/年趋势，Token 构成、模型排行、年度热力图和会话明细。中心服务仅绑定 `127.0.0.1:8765`，不会把提示词、消息或认证信息发送给第三方服务。

## 为什么选择本项目

许多 Token 工具擅长统计当前电脑；本项目更专注于构建一个**隐私优先的 Codex + Hermes 跨设备统计中心**，尤其适合拥有多台 Mac、Windows 或 WSL 设备，并希望由家庭服务器长期汇总数据的用户。

- **跨设备集中统计**：每台电脑在本地读取自己的 Codex/Hermes 用量，只把标准化 Token 事件发送到用户自己的中心主机。
- **双中心主机方案**：既可以使用 Mac 作为中心，也可以使用 Windows 作为中心；两种中心都能接收其他 Mac 或 Windows 采集端的数据。
- **私网访问优先**：中心服务保持监听 `127.0.0.1`，跨设备上报和远程访问推荐使用用户自己的 Tailscale Serve，不要求开放公网端口。
- **不收集对话内容**：事件只包含设备、来源、模型、时间、会话标识及 Token 计数；不保存或上传提示词、回复正文和认证凭据。
- **稳定增量与去重**：通过累计计数差值、来源游标和稳定事件 ID 处理追加、重复同步、计数重置与历史回溯。
- **面向日常使用**：提供 macOS/Windows Host、macOS/Windows Agent、CN/EN 界面、三套主题以及日/周/月/年可视化。

简而言之，它不仅是单机 Token 图表，更是一套可以部署在家庭服务器上的**多设备私人 Token 中心**。


### 界面主题

页头的调色板按钮可在三套主题之间切换：**曜石青玉**（默认）、**午夜极光**、**暖黑香槟**。选择只保存在本机浏览器的 `token-dashboard.theme` 中，不会进入 URL 或触发数据同步。

> 以下截图均由隔离演示数据库生成。设备、账号、会话、日期与 Token 数值全部为虚构示例，不包含任何用户数据。

#### 曜石青玉

![曜石青玉主题的 Token Dashboard 虚构数据演示](./docs/screenshots/themes/obsidian-jade-demo.png)

#### 午夜极光

![午夜极光主题的 Token Dashboard 虚构数据演示](./docs/screenshots/themes/midnight-aurora-demo.png)

#### 暖黑香槟

![暖黑香槟主题的 Token Dashboard 虚构数据演示](./docs/screenshots/themes/warm-champagne-demo.png)


## 安装与使用

普通用户建议从 GitHub Releases 下载对应系统的 Host 安装包。不要下载或转发其他用户已经配置好的单设备 Agent ZIP；其中包含只属于目标服务器和设备的写入凭据。

先把解压后的项目文件夹移动到不会再改名或删除的长期位置；`launchd` 会记录该绝对路径。

1. 双击 [`install.command`](./install.command)，完成依赖、前端构建和每日任务安装。
2. 以后双击 [`Token Dashboard.command`](./Token%20Dashboard.command)。
3. 浏览器会自动打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)。安装后的服务由 `launchd` 在登录后常驻；关闭启动窗口不会停止后台服务。

页面打开时后端每 60 秒同步一次；`launchd` 每天 00:05 执行同步和快照。Mac 当时休眠时，任务会在唤醒后补跑；程序启动还会补齐缺失历史快照。

### 两套中心主机安装包

执行 `./scripts/build-host-packages.sh` 会生成两套互相独立、均不含个人数据或设备密钥的发布包：

- `dist/Token-Dashboard-Host-macOS.zip`：Mac 作为中心，可生成 Windows/macOS 采集端。
- `dist/Token-Dashboard-Host-Windows-x64.zip`：Windows 作为中心，以本机 Agent 统一采集 native 与 WSL，并可生成 Windows/macOS 采集端。

两套中心都只监听 `127.0.0.1:8765`。其他设备通过该用户自己的 Tailscale Serve HTTPS 地址上报；不得使用 Funnel 或将 SQLite 设为网络共享。

详细操作说明：

- [`docs/INSTALL-MACOS-HOST.md`](./docs/INSTALL-MACOS-HOST.md)
- [`docs/INSTALL-WINDOWS-HOST.md`](./docs/INSTALL-WINDOWS-HOST.md)

### 手动命令

```bash
cd ~/token-dashboard

# 启动生产看板
PYTHONPATH=backend backend/.venv/bin/python -m uvicorn app.main:app \
  --app-dir backend --host 127.0.0.1 --port 8765

# 同步数据
PYTHONPATH=backend backend/.venv/bin/python -m app.cli sync

# 同步并补齐每日快照
PYTHONPATH=backend backend/.venv/bin/python -m app.cli snapshot
```

移除每日后台任务但保留程序与数据：

```bash
./scripts/uninstall-launch-agent.sh
```

## Token 口径

- `总 Token = 非缓存输入 + 缓存读取 + 缓存写入 + 输出`。
- Codex 的 `cached_input_tokens` 是输入子集，导入时从输入中扣除，避免重复。
- Hermes 已将缓存与非缓存输入分列，直接使用其标准化计数。
- 推理 Token 是输出子项，只单独展示，不再次加入总量。
- Codex 使用累计计数差值生成逐次事件；不会把只反映上下文大小、但未推进累计计数的记录算作用量。
- Hermes 的历史数据库只有会话累计值，首次回溯按会话开始日期归档；安装后的新增差值按同步观察时间记录。

本地统计数据库位于：

```text
~/Library/Application Support/Token Dashboard/token-dashboard.sqlite3
```

日志位于：

```text
~/Library/Logs/Token Dashboard/
```

## API

- `GET /api/health`：数据源和同步状态
- `POST /api/sync`：立即同步
- `GET /api/summary?source=&model=`：今日/周/月/年汇总
- `GET /api/timeseries?granularity=day|week|month|year&from=&to=&source=&model=`
- `GET /api/models?from=&to=&source=`
- `GET /api/calendar?year=&source=&model=`
- `GET /api/sessions?source=&model=&limit=&offset=&sort=latest|tokens`

交互式接口文档：[http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs)

创建远程采集设备时必须显式提供该用户自己的服务器地址，程序不会内置任何个人 Tailnet 地址：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.cli provision-device \
  --name "My Windows PC" \
  --platform windows \
  --server "https://YOUR-MAC.YOUR-TAILNET.ts.net" \
  --output /path/to/agent-config.json
```

如需让 macOS 或 Windows 任一作为中心主机，并采集其他 Mac/Windows，参见
[`docs/CROSS_PLATFORM_DEPLOYMENT.md`](./docs/CROSS_PLATFORM_DEPLOYMENT.md)。该文档定义四种主机/采集端组合、配置示例、安装包边界和验收清单。

## 开发与测试

```bash
# 后端
backend/.venv/bin/pip install -r backend/requirements-dev.txt
backend/.venv/bin/pytest

# 前端
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build

# 服务启动后冒烟测试
./scripts/smoke-test.sh
```

前端开发服务器固定为 `127.0.0.1:5173`，并将 `/api` 代理到 `127.0.0.1:8765`。

## 数据表

- `usage_events`：标准化用量事件，不保存对话正文。
- `source_cursors`：Codex 文件增量读取位置和累计计数状态。
- `hermes_sessions`：Hermes 会话累计计数检查点。
- `daily_snapshots`：按日期、来源、模型保存的幂等快照。
- `source_status`、`sync_runs`：数据源健康状态和同步审计。

## 安全与隐私

- 不要提交数据库、日志、真实使用截图、Tailnet 地址、`agent-config.json` 或配置完成的 Agent ZIP；公开文档截图只能使用隔离生成的虚构演示数据。
- 远程访问应使用 Tailscale Serve；不要使用 Funnel 或把端口直接暴露到公网。
- 安全问题请参阅 [`SECURITY.md`](./SECURITY.md)，贡献说明见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。

## 许可证

项目源码使用 [MIT License](./LICENSE)。第三方组件及其许可证说明见 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。
