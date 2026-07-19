# Windows 10/11 x64 中心主机：安装与使用说明

本文适用于 `Token-Dashboard-Host-Windows-x64.zip`：用一台 **Windows 10/11 x64** 电脑作为中心主机，保存统一数据库并显示看板，同时采集：

- 中心主机本机的 Windows Codex、Windows 原生 Hermes，以及 WSL 中的 Hermes CLI；
- 其他 Windows 电脑上的 Codex、原生 Hermes 和 WSL Hermes；
- 其他 Mac 上的 Codex 和 Hermes。

这是一套独立部署。安装包不会连接制作者的数据库、设备密钥或 Tailscale 网络。中心主机、远程电脑和 Tailnet 都应属于实际使用者本人。

> [!IMPORTANT]
> 当前已经有跨平台协议和配置层的自动测试，但 Windows PowerShell 安装、计划任务重启、系统权限、Tailscale Serve、真实 native/WSL 数据发现和卸载流程，仍需在真实 Windows 10/11 x64 电脑上完成最终冒烟验证。首次交付朋友使用前，请务必执行本文最后的“真实 Windows 验收清单”。

---

## 1. 先理解这套部署

```text
Windows 中心主机
├─ 中心服务：http://127.0.0.1:8765
├─ 中心数据库：%LOCALAPPDATA%\Token Dashboard\token-dashboard.sqlite3
├─ localhost Agent：采集这台 Windows 自己的数据
└─ Tailscale Serve HTTPS：接收其他 Windows / Mac 的上报

远程 Windows / Mac
└─ 各自的 Agent：每台设备使用一个独立写入密钥，通过 Tailnet HTTPS 上报
```

中心服务本身**不直接读取本机 Codex/Hermes**。它固定以“仅接收 Agent 数据”的方式运行；本机数据也由安装器自动创建的 localhost Agent 通过 `http://127.0.0.1:8765` 提交。这样，本机和远程设备使用同一套采集、排队和去重逻辑。

### 可以采集什么

| 电脑 | Codex | Hermes | 说明 |
|---|---|---|---|
| Windows 中心主机 | Windows 原生 Codex | Windows 原生 Hermes、WSL Hermes CLI | 安装中心主机时自动安装 localhost Agent |
| 远程 Windows | Windows 原生 Codex | Windows 原生 Hermes、WSL Hermes CLI | 使用 Windows Agent ZIP |
| 远程 Mac | macOS Codex | macOS Hermes | 使用 macOS Agent ZIP |

> [!NOTE]
> Windows Agent 当前采集的是 **Windows 原生 Codex** 和 **WSL 中的 Hermes**；它不会采集 WSL 里的 Codex。

---

## 2. 安装前准备

### 2.1 中心主机要求

- Windows 10 或 Windows 11，**x64**；不支持把本包当作 ARM64 或 Windows Server 安装包使用。
- 使用将来长期运行看板的那个 Windows 账号登录。程序、数据和计划任务都是按当前用户安装的。
- Python 3.9 或更高版本。
- 安装或更新中心主机时建议可连接互联网；安装器每次都会升级 `pip` 并确认中心服务依赖。
- 如果只统计中心主机本机，Tailscale 不是必需的。
- 如果要接收其他 Windows/Mac，中心主机和远程电脑都必须安装并登录 Tailscale，加入同一个 Tailnet，并允许彼此访问。
- 中心主机需要保持开机、网络可用，且该 Windows 用户已经登录。它不是登录前运行的 Windows Service。

### 2.2 安装 Python

1. 安装 Python 3.9 或更高版本。
2. 安装界面中勾选 **Add Python to PATH**。
3. 安装完成后，关闭旧的命令窗口，再开始安装 Token Dashboard。

安装器会依次尝试：

1. `py.exe -3` 找到的 Python 3；
2. PATH 中的 `python.exe`。

找到的版本必须不低于 3.9，否则安装会停止并显示 Python 要求。

### 2.3 准备 Tailscale（有远程设备时）

1. 在中心主机安装 Tailscale。
2. 登录朋友自己的 Tailscale 账号/Tailnet，不要使用安装包制作者的网络。
3. 在每台远程 Windows/Mac 上安装 Tailscale，并加入同一个 Tailnet。
4. 不要启用 Tailscale Funnel。此方案只使用 Tailnet 内的 Tailscale Serve。

官方参考：

- [在 Windows 安装 Tailscale](https://tailscale.com/docs/install/windows)
- [Tailscale Serve 说明](https://tailscale.com/docs/features/tailscale-serve)
- [Tailscale Serve 命令参考](https://tailscale.com/docs/reference/tailscale-cli/serve)

### 2.4 安装前检查表

- [ ] 收到的是 `Token-Dashboard-Host-Windows-x64.zip`。
- [ ] Windows 是 10/11 x64。
- [ ] Python 3.9+ 已安装并加入 PATH。
- [ ] 安装或更新中心主机时网络可用。
- [ ] 有远程设备时，中心主机的 Tailscale 已登录。
- [ ] 当前登录账号就是以后运行看板和读取本机 Codex/Hermes 的账号。

---

## 3. 解压并安装 Windows 中心主机

### 3.1 正确解压

1. 在文件资源管理器中找到 `Token-Dashboard-Host-Windows-x64.zip`。
2. 右键选择“全部解压”。
3. 解压到本机普通文件夹，例如“下载”或“桌面”。
4. 打开解压后的完整文件夹。

不要直接在 ZIP 预览窗口里运行 `.cmd`，也不要只复制其中一个安装文件。安装器需要同目录下的 `backend`、`frontend`、`templates` 和其他脚本。

如果 Windows 显示安全提醒，只应在确认 ZIP 来自可信发送者且文件名正确后继续。

### 3.2 执行安装

1. 双击 `Install-Token-Dashboard.cmd`。
2. 保持窗口打开，不要中途关闭。
3. 安装器会依次：
   - 检查安装包是否完整；
   - 检查 Python 版本；
   - 将中心程序安装到当前用户的 `%LOCALAPPDATA%`；
   - 创建或复用 Python 虚拟环境，并安装依赖；
   - 注册中心服务和每日快照计划任务；
   - 启动中心服务并等待最多约 30 秒；
   - 安装或更新这台 Windows 的 localhost Agent；
   - 扫描 Windows 原生 Hermes 和已有 WSL Hermes；
   - 执行第一次本机历史同步；
   - 创建桌面快捷方式；
   - 打开浏览器看板。
4. 看到绿色的 `Installation completed.` 后，安装完成。

中心主机一般不需要管理员权限。稍后配置 Tailscale Serve 时，如果 Windows/Tailscale 要求管理员权限，再按提示以管理员身份运行对应快捷方式。

### 3.3 安装后的目录

在下表中，可把路径直接粘贴到文件资源管理器地址栏：

| 内容 | 默认位置 |
|---|---|
| 中心程序、前端、Python 虚拟环境、维护脚本 | `%LOCALAPPDATA%\Token Dashboard Host` |
| 中心数据库和中心日志 | `%LOCALAPPDATA%\Token Dashboard` |
| 本机 localhost Agent、配置、本地队列和日志 | `%LOCALAPPDATA%\Token Dashboard Agent` |
| 手动备份 | 系统“文档”目录下的 `Token Dashboard Backups`（“文档”可能已重定向到 OneDrive） |

中心主机安装成功后，最初解压出来的主机安装文件夹可以删除。它本身不含已生成的远程设备密钥；真正需要特别保护的是以后在“下载”中生成的单设备 Agent ZIP。

### 3.4 桌面上的五类快捷方式

安装器会尝试创建：

| 快捷方式 | 用途 |
|---|---|
| `Token Dashboard` | 打开本机看板 |
| `Token Dashboard - Add Device` | 为一台远程 Windows 或 Mac 生成专属 Agent ZIP |
| `Token Dashboard - Devices` | 查看设备清单并吊销远程设备；对应 `Manage-Remote-Devices.cmd` |
| `Token Dashboard - Backup` | 创建一致性的中心数据库备份；对应 `Backup-Token-Dashboard.cmd` |
| `Token Dashboard - Tailscale` | 配置 Tailscale Serve HTTPS |

如果桌面快捷方式创建失败，也可以在 `%LOCALAPPDATA%\Token Dashboard Host` 中运行对应的 `.cmd` 文件，例如 `Manage-Remote-Devices.cmd` 或 `Backup-Token-Dashboard.cmd`。

---

## 4. 安装器创建的三个计划任务

打开“任务计划程序”，在“任务计划程序库”中应看到：

| 任务名称 | 触发方式 | 实际作用 | 正常状态 |
|---|---|---|---|
| `Token Dashboard Host` | 当前用户登录时 | 在 `127.0.0.1:8765` 持续运行中心服务 | 登录后通常为“正在运行” |
| `Token Dashboard Agent` | 每 1 分钟 | 采集本机 Windows native/WSL 数据并提交到 localhost | 两次运行之间通常为“就绪” |
| `Token Dashboard Daily Snapshot` | 每天 00:05 | 补齐缺失的日快照 | 平时通常为“就绪” |

中心服务和每日快照是当前用户、有限权限、交互式计划任务。中心任务支持失败后每分钟重启；任务错过时会在可用后补跑。电脑休眠或关机时不会采集或接收；恢复后 Agent 会继续同步本地队列，缺失快照也会补齐。

> [!WARNING]
> “每日快照”只是同一数据库中的日汇总，不是独立备份。必须另用 `Token Dashboard - Backup` 备份数据库。

---

## 5. localhost Agent 如何采集这台 Windows

### 5.1 Windows 原生数据位置

localhost Agent 默认读取：

- Codex：`%USERPROFILE%\.codex`
- Hermes：按下面顺序选择安装时已经存在的第一个数据库：
  1. `%HERMES_HOME%\state.db`（设置了 `HERMES_HOME` 时）；
  2. `%LOCALAPPDATA%\hermes\state.db`；
  3. `%USERPROFILE%\.hermes\state.db`。

如果安装时没有找到原生 Hermes，它会继续观察 `%LOCALAPPDATA%\hermes\state.db`。

### 5.2 WSL Hermes 扫描

安装器会枚举当时已经安装的所有 WSL 发行版，并检查各发行版中的：

```text
$HOME/.hermes/state.db
```

发现数据库后，WSL 内还必须存在以下任一 Python：

1. PATH 中的 `python3`；
2. `$HOME/.hermes/hermes-agent/venv/bin/python`。

每次同步时，Agent 会在 WSL 中只读 Hermes `sessions` 表，只导出会话 ID、开始时间、模型和各类 Token 计数到 Windows 本地的精简 SQLite 副本，再由 Agent 标准化上报。提示词、回复和原始 Hermes 数据库不会被复制到中心主机。

扫描结果保存在：

```text
%LOCALAPPDATA%\Token Dashboard Agent\hermes-locations.txt
```

> [!IMPORTANT]
> 原生 Hermes 路径和 WSL 发行版是在**安装 Agent 时扫描**的。如果安装后才新增 WSL、才安装 WSL Hermes、才补装 WSL Python，或 Hermes 数据库后来换了位置，请重新运行最新的中心主机安装器。重装会保留现有中心数据库和本机 Agent 身份，同时更新 Agent runtime 并重新扫描位置。

---

## 6. 第一次验证中心主机

### 6.1 验证网页

1. 双击桌面的 `Token Dashboard`。
2. 浏览器应打开：

   ```text
   http://127.0.0.1:8765
   ```

3. 如需只检查服务是否响应，可打开：

   ```text
   http://127.0.0.1:8765/api/health
   ```

能看到网页或 JSON 响应，说明中心服务已启动。刚安装、尚无 Codex/Hermes 历史时，健康信息可能显示无数据；只安装其中一个数据源时也可能显示部分可用，这不等于安装失败。

### 6.2 验证计划任务

1. 打开“任务计划程序”。
2. 检查上述三个任务都存在。
3. `Token Dashboard Host` 应处于运行状态。
4. 可右键 `Token Dashboard Agent` 选择“运行”，然后等待约一分钟刷新看板。

### 6.3 验证本机数据

1. 确认当前 Windows 账号中确实已有 Codex 或 Hermes 使用记录。
2. 等待 1～2 分钟。
3. 刷新看板。
4. 使用页面上的“设备”“来源”“账号”筛选，查看这台 Windows 的 Codex/Hermes 数据。
5. 如 WSL Hermes 没出现，先检查 `hermes-locations.txt`。

本机中心服务只监听 `127.0.0.1`，所以 `http://127.0.0.1:8765` 只能从中心主机本机直接访问。远程访问必须走下一节的 Tailscale Serve HTTPS。

---

## 7. 配置 Tailscale Serve

只有需要接收其他电脑的数据或从 Tailnet 访问看板时，才需要本节。

### 7.1 配置

1. 确认中心主机上的 Tailscale 已登录并在线。
2. 双击桌面的 `Token Dashboard - Tailscale`。
3. 脚本会发布：

   ```text
   http://127.0.0.1:8765
   ```

   到当前 Tailnet 内的 Tailscale Serve HTTPS。
4. 记下窗口显示的 `https://...ts.net` 地址。
5. 如果脚本提示需要管理员权限，关闭窗口，右键该快捷方式或 `%LOCALAPPDATA%\Token Dashboard Host\Configure-Tailscale-Serve.cmd`，选择“以管理员身份运行”。

该脚本实际运行的是后台 Serve 配置；它不会把中心服务改为监听局域网或公网地址。

### 7.2 验证

在同一个 Tailnet 的另一台电脑上：

1. 确认 Tailscale 在线；
2. 用浏览器打开刚才显示的 HTTPS 地址；
3. 能看到看板后，再生成远程 Agent ZIP。

如果打不开，不要先生成或反复生成 Agent ZIP。先检查中心主机是否在线、Tailscale 是否连接、Serve 是否已配置，以及 Tailnet 访问策略是否允许这两台设备互通。

> [!CAUTION]
> 看板和只读 API 当前没有应用层登录或独立的读取权限控制。设备写入接口需要各自的设备密钥，但任何被 Tailnet 访问策略允许连接此 Serve 地址的设备，都可能打开完整看板和读取汇总数据。因此应在 Tailscale 访问策略中只允许受信任设备访问中心主机。

> [!WARNING]
> 不要使用 Funnel，不要在路由器上做端口映射，也不要把 SQLite 数据库放到网络共享。当前安全边界是：中心服务只绑定 `127.0.0.1:8765`，远程连接仅通过自己的 Tailnet HTTPS。

---

## 8. 为每台远程电脑生成单设备 Agent ZIP

### 8.1 生成步骤

每增加一台电脑，都单独执行一次：

1. 先确认 Tailscale Serve 已配置且 HTTPS 地址可访问。
2. 双击 `Token Dashboard - Add Device`。
3. 输入设备名称，例如：

   ```text
   Work-MacBook
   ```

   建议每台电脑使用唯一、容易识别的名称。
4. 选择平台：
   - 输入 `W`：Windows；
   - 输入 `M`：macOS。
5. 输入 Dashboard HTTPS 地址：
   - 如果脚本已从 Tailscale 读取到默认地址，直接按回车采用方括号中的地址；
   - 如果没有默认值，粘贴第 7 节记录的完整 `https://...` 地址。
6. 成功后，ZIP 会生成在当前用户“下载”文件夹，名称类似：

   ```text
   Token-Dashboard-Agent-Work-MacBook-macos.zip
   Token-Dashboard-Agent-Office-PC-windows.zip
   ```

### 8.2 一个 ZIP 只给一台设备

生成 ZIP 时，中心数据库会同时创建一个 `dev_...` 设备 ID 和该设备独有的持久写入密钥。ZIP 中的 `agent-config.json` 含有这个密钥，因此：

- 不要把同一个 ZIP 安装到两台电脑；
- 不要把 ZIP 发到群聊、公开网盘或公共邮箱；
- 只通过受控方式交给命名的那台设备；
- 安装成功并验证后，删除中心主机“下载”中的 ZIP、传输副本和远程电脑上的原始 ZIP；
- 解压后的安装器会删除它自己目录中的 `agent-config.json`，但不会替你删除原始 ZIP。

如果生成过程在创建设备记录后失败，中心数据库中可能留下未使用设备。可通过 `Token Dashboard - Devices` 找到并吊销它，再排除错误后重试。

---

## 9. 在远程 Windows 安装 Agent

### 9.1 前置条件

- Windows 10/11 x64；
- Tailscale 已安装、已连接，并加入中心主机所在 Tailnet；
- 能从浏览器打开中心主机的 Tailscale Serve HTTPS 地址；
- 使用实际运行 Codex/Hermes 的 Windows 账号安装。

远程 Windows Agent ZIP 自带 x64 便携 Python runtime，**远程 Windows 不需要另装 Python**。

### 9.2 安装步骤

1. 将只属于该设备的 Windows Agent ZIP 复制到目标 Windows。
2. 右键“全部解压”到本机普通文件夹。
3. 打开解压后的文件夹。
4. 双击 `Install-Token-Agent.cmd`。
5. 安装器会：
   - 检查 `agent-config.json` 和便携 Python runtime；
   - 对非 localhost 地址检查 Tailscale 是否已安装并连接；
   - 安装到 `%LOCALAPPDATA%\Token Dashboard Agent`；
   - 将配置文件 ACL 限制为当前 Windows 用户可修改；
   - 扫描原生 Hermes 和 WSL Hermes；
   - 导入 Codex、Hermes Desktop 和 WSL Hermes 历史；
   - 创建每分钟运行一次的 `Token Dashboard Agent` 计划任务；
   - 删除解压目录里的 `agent-config.json`。
6. 看到 `Installation completed.` 后保持 Tailscale 在线。
7. 回到中心看板验证该设备已经有数据，再删除原始 ZIP 和传输副本。

### 9.3 验证远程 Windows

在目标 Windows：

- 任务计划程序中存在 `Token Dashboard Agent`；
- `%LOCALAPPDATA%\Token Dashboard Agent\hermes-locations.txt` 中列出预期的 native/WSL 路径；
- `%LOCALAPPDATA%\Token Dashboard Agent\scheduled-task.log` 持续有运行记录。

在中心主机：

1. 等待 1～2 分钟并刷新看板；
2. 在“设备”筛选中选择刚才的设备名称；
3. 分别检查 Codex 和 Hermes；
4. 如果该电脑只安装其中一个来源，另一个来源为空是正常的。

### 9.4 卸载远程 Windows Agent

1. 先在中心主机用 `Token Dashboard - Devices` 吊销该设备；
2. 双击 `%LOCALAPPDATA%\Token Dashboard Agent\Uninstall-Token-Agent.cmd`；
3. 卸载器只删除 `Token Dashboard Agent` 计划任务；
4. 本地配置、队列和日志仍保留在 `%LOCALAPPDATA%\Token Dashboard Agent`；确认不再需要后再手动删除该目录。

---

## 10. 在远程 Mac 安装 Agent

### 10.1 前置条件

- Tailscale 已安装、已连接，并加入中心主机所在 Tailnet；
- 能从浏览器打开中心主机的 Tailscale Serve HTTPS 地址；
- `python3` 已安装；安装脚本要求 Python 3.9 或更高版本；
- 使用实际运行 Codex/Hermes 的 macOS 用户安装。

### 10.2 安装步骤

1. 将只属于该 Mac 的 macOS Agent ZIP 复制到目标 Mac。
2. 双击 ZIP 解压。
3. 打开解压后的文件夹。
4. 双击 `Install-Token-Agent.command`。
5. 如果 macOS 显示安全确认，只在确认文件来源可信后选择允许；必要时右键文件选择“打开”。
6. 安装器会：
   - 安装到 `~/Library/Application Support/Token Dashboard Agent`；
   - 将目录权限设为仅当前用户访问，并将配置设为仅当前用户读写；
   - 读取 `~/.codex` 和 `~/.hermes/state.db`；
   - 注册 `com.local.token-dashboard.agent` LaunchAgent；
   - 启动持续运行的 Agent，每 60 秒同步一次；
   - 删除解压目录里的 `agent-config.json`；
   - 尝试第一次同步。
7. 按回车关闭安装窗口。
8. 回到中心看板验证后，删除原始 ZIP、传输副本和不再需要的解压目录。

Mac 的第一次连接失败不会撤销安装。后台 Agent 会在网络恢复后继续重试，因此 Tailscale 暂时断开时，可先恢复连接并等待 1～2 分钟。

### 10.3 验证远程 Mac

在 Mac 上可检查：

```text
~/Library/Application Support/Token Dashboard Agent/agent.log
~/Library/Application Support/Token Dashboard Agent/launchd.log
~/Library/Application Support/Token Dashboard Agent/launchd-error.log
```

在 Windows 中心看板中，用“设备”筛选选择该 Mac，分别检查 Codex/Hermes 数据。

### 10.4 卸载远程 Mac Agent

1. 先在中心主机用 `Token Dashboard - Devices` 吊销该设备；
2. 双击 `~/Library/Application Support/Token Dashboard Agent/Uninstall-Token-Agent.command`；
3. 脚本会停止并移除 `com.local.token-dashboard.agent` LaunchAgent；
4. 历史队列与配置仍保留在 `~/Library/Application Support/Token Dashboard Agent`；确认不再需要后再手动删除。

---

## 11. 日常使用

### 打开看板

- 在中心主机双击桌面 `Token Dashboard`；或
- 打开 `http://127.0.0.1:8765`。

同一 Tailnet 的其他设备可使用 Tailscale Serve 的 HTTPS 地址。该地址会显示完整看板，不只是上传接口，因此只应让受信任的 Tailnet 设备访问。

### 同步节奏

- Windows Agent：计划任务每 1 分钟执行一次；
- macOS Agent：LaunchAgent 持续运行，默认每 60 秒同步一次；
- 每批最多上报 200 个事件；
- 断网或中心主机离线时，尚未送达的事件留在 Agent 本地 SQLite 队列；后续成功连接时继续上传；
- 重复批次和重复事件会被识别，不应重复计数。

### 筛选数据

看板可按设备、账号、来源和模型筛选。设备名称来自生成 Agent ZIP 时输入的名称，因此建议使用唯一、稳定的名称，例如“Office-PC”“Work-MacBook”，不要给多台设备取同名。

### 睡眠、关机与登录

- 中心主机休眠或关机时，远程 Agent 无法上传；数据会留在远程本地等待后续上报。
- `Token Dashboard Host` 是当前用户登录触发的计划任务。重启后必须让安装该程序的用户登录。
- 每日 00:05 错过的快照任务会在任务可用后补跑，中心服务启动时也会补齐缺失快照。

---

## 12. 安全与隐私

### 程序会提交的内容

- Token 数量及分类；
- 时间；
- 来源（Codex/Hermes）；
- 模型；
- 设备/账号标签；
- 哈希后的会话标识。

### 程序不会提交的内容

- 提示词和回复正文；
- 原始 Codex JSONL；
- 原始 Hermes 数据库；
- Cookie、API Key、认证文件或登录凭据。

### 必须遵守的安全规则

1. 每台远程电脑生成一个独立 ZIP，不复用设备密钥。
2. Agent ZIP 视同密钥文件，安装验证后删除所有传输副本。
3. 只使用自己的 Tailnet；不要启用 Funnel。
4. 不要开放 `8765` 的路由器端口映射，不要把服务改为监听 `0.0.0.0`。
5. 不要把 `%LOCALAPPDATA%\Token Dashboard` 设为共享文件夹，也不要直接同步运行中的 SQLite 到多人云盘。
6. 备份含完整用量和设备历史，按私密数据保存。
7. Agent 安装目录中的 `agent-config.json` 含写入密钥。Windows 安装器会对它设置当前用户 ACL，macOS 安装器会设为 `0600`；不要手动复制或分享。
8. ZIP 丢失、误发或电脑丢失时，应立即吊销对应设备。

中心 Web 服务固定绑定 `127.0.0.1:8765`；安装器不会创建面向局域网或公网的监听端口。Tailscale Serve 是远程入口，且应限制在自己的 Tailnet 内。

设备密钥是持续有效的写入凭据，不是安装一次后自动失效的验证码；只有在中心主机吊销设备后才会失效。Agent 的本地数据库还会保存源路径和原始会话 ID，用于增量采集和断线补传，因此整个 `%LOCALAPPDATA%\Token Dashboard Agent` 目录都应按敏感数据保护。

当前版本还有以下边界：

- 所有日期默认按 `Asia/Shanghai` 汇总，普通界面没有时区切换。
- 每个 Agent 只读取安装它的当前 Windows/macOS 用户，不读取同一电脑的其他登录账号。
- 中心数据库、Agent 队列和日志没有自动容量上限；日志也没有自动轮转，应定期检查磁盘空间。
- 一个部署只能有一个权威中心，不支持 Windows/Mac 两个中心同时双向合并同一批 Agent。

---

## 13. 备份

### 13.1 创建备份

1. 在中心主机双击 `Token Dashboard - Backup`。
2. 看到绿色的 `Backup created:`。
3. 备份文件保存在：

   ```text
   系统“文档”目录\Token Dashboard Backups\token-dashboard-YYYYMMDD-HHMMSS.sqlite3
   ```

“文档”位置由 Windows 的 MyDocuments Known Folder 决定；如果系统把“文档”重定向到 OneDrive 或其他位置，备份也会保存在重定向后的目录中。

备份脚本使用 SQLite 的一致性备份操作，可以在中心服务运行时执行。每次会创建带时间戳的新文件，不覆盖旧备份。

### 13.2 建议时机

- 第一次安装并确认本机历史导入后；
- 添加多台远程设备并确认数据后；
- 更新中心主机前；
- 大规模吊销设备前；
- 卸载或手动删除数据前。

### 13.3 重要限制

当前安装包提供备份按钮，但没有一键恢复脚本。不要在中心服务运行时直接覆盖数据库，也不要把每日快照当作备份。如需恢复，应先停止中心和 Agent 任务，并由熟悉 SQLite/WAL 文件的维护人员处理。

恢复较旧的中心数据库不会让各 Agent 自动重传已经成功送达的事件：Agent 自己的 `agent.sqlite3` 仍会把这些事件标记为已送达。因此，旧备份中缺少的中心数据不能依靠“等待下一次同步”自动补齐；恢复前必须制定中心数据库与各 Agent 本地队列的协同恢复方案。

---

## 14. 更新

### 14.1 更新 Windows 中心主机和本机 Agent

中心安装器支持覆盖更新，并保留现有数据库。推荐流程：

1. 运行 `Token Dashboard - Backup`。
2. 将新的 `Token-Dashboard-Host-Windows-x64.zip` 解压到一个新的普通文件夹。
3. 在任务计划程序中右键 `Token Dashboard Host`，选择“结束”，确保旧服务已停止。
4. 双击新包中的 `Install-Token-Dashboard.cmd`。
5. 安装器会替换中心的 backend/frontend、维护脚本和 Agent 模板，复用现有虚拟环境并更新依赖。
6. 数据库已存在且 `%LOCALAPPDATA%\Token Dashboard Agent\agent-config.json` 仍存在时，安装器会保留本机 Agent 的原设备身份，只更新 Agent runtime，并重新扫描 Hermes/WSL 位置。
7. 安装完成后，检查三个计划任务、看板和本机数据。

不要为了更新先运行卸载，也不要删除下列目录：

```text
%LOCALAPPDATA%\Token Dashboard
%LOCALAPPDATA%\Token Dashboard Agent
```

如果数据库存在但本机 Agent 配置已被手动删除，重装时会创建名称带 `Recovery` 和随机短后缀的新本机采集设备身份，避免撞上旧名称。确认新身份正常后，可在 Devices 工具中吊销旧身份。

### 14.2 远程 Agent 更新/重新登记

当前脚本没有“按现有设备密钥生成升级 ZIP”的按钮。重新运行 `Token Dashboard - Add Device` 一定会创建新的设备 ID 和新密钥，不是原设备的原地升级。

如确需重新登记：

1. 使用一个从未在该中心数据库中使用过的唯一设备名称，为该实体设备生成新的单设备 ZIP；
2. 在原设备上安装新 ZIP；
3. 确认新身份可以继续上报；
4. 在中心主机吊销旧设备 ID；
5. 不要随意删除 Agent 的本地数据目录，否则历史可能以新设备身份重新上报，造成中心历史重复。

如只是日常使用且 Agent 正常，不需要定期重新生成 ZIP。

设备名称在中心数据库中全局唯一。吊销只会禁用设备，不会删除记录或释放名称；重新登记时不能复用已吊销设备的旧名称，例如可把 `Office-PC` 改为 `Office-PC-2`。

---

## 15. 查看和吊销设备

### 15.1 使用设备管理快捷方式

1. 双击 `Token Dashboard - Devices`。
2. 窗口会列出当前设备的 JSON 信息，包括：
   - `id`：设备 ID；
   - `name`：设备名称；
   - `platform`：平台；
   - `enabled`：是否启用；
   - `is_local`：是否为中心数据库的内建 local 记录；
   - `last_seen_at`：最近上报时间。
3. 找到要吊销的远程设备 `dev_...` ID。
4. 在提示处输入完整 `dev_...` ID。
5. 再输入大写的：

   ```text
   REVOKE
   ```

6. 看到 `Device revoked.` 即完成。

吊销只把设备设为禁用：

- 旧密钥之后的上报会收到认证失败；
- 其他设备不受影响；
- 该设备已有历史不会被删除；
- 该设备名称仍被保留，不能用于新设备；
- 当前脚本没有“重新启用旧密钥”操作，需要恢复采集时应创建新设备 ZIP。

> [!CAUTION]
> 中心主机的 localhost Agent 也是一个 `dev_...` 采集设备，名称通常是 `<电脑名> - Local Collector`。不要把它误认为闲置远程设备而吊销。`id` 为 `local`、`is_local` 为 `1` 的内建 Host 记录不能通过该命令吊销。

### 15.2 应立即吊销的情况

- Agent ZIP 发错人、上传到不可信位置或无法确认是否删除；
- 电脑丢失或转交他人；
- 同一个 ZIP 被误装到多台电脑；
- 某远程电脑永久停用；
- 生成 Agent 包失败后留下不用的设备记录。

---

## 16. 卸载 Windows 中心主机

### 16.1 推荐顺序

1. 中心主机保持运行时，使用 `Token Dashboard - Devices` 吊销不再使用的所有远程设备。
2. 在远程 Windows/Mac 上运行各自的 Agent 卸载脚本。
3. 使用 `Token Dashboard - Backup` 创建最后一次备份。
4. 在 `%LOCALAPPDATA%\Token Dashboard Host` 中双击 `Uninstall-Token-Dashboard.cmd`。

### 16.2 卸载脚本实际会做什么

它会：

- 停止并删除 `Token Dashboard Host`；
- 删除 `Token Dashboard Daily Snapshot`；
- 删除 `Token Dashboard Agent`。

它**不会**：

- 删除 `%LOCALAPPDATA%\Token Dashboard Host`；
- 删除 `%LOCALAPPDATA%\Token Dashboard` 中的数据库和日志；
- 删除 `%LOCALAPPDATA%\Token Dashboard Agent` 中的配置、队列和日志；
- 删除桌面快捷方式；
- 撤销已经配置在 Tailscale 中的 Serve 规则。

这样设计是为了防止误删数据库。确认已备份、已吊销设备且不再需要恢复后，才手动删除上述三个目录和桌面快捷方式。Tailscale Serve 需要在 Tailscale 自己的管理方式中另行关闭；当前卸载脚本不会替你处理。

---

## 17. 故障排查

### 17.1 双击安装后提示缺少组件

可能原因：直接从 ZIP 内运行、只复制了 `.cmd`、解压不完整。

处理：重新“全部解压”完整 ZIP，在完整目录中运行 `Install-Token-Dashboard.cmd`。

### 17.2 提示需要 Python 3.9 或更高版本

处理：

1. 安装 Python 3.9+；
2. 勾选 Add Python to PATH；
3. 关闭旧窗口后重试；
4. 如果电脑上有多个 Python，确保 `py -3` 或 `python` 指向受支持版本。

### 17.3 安装依赖失败

中心主机依赖需要从 Python 包源安装。检查互联网、公司代理/防火墙、证书拦截和磁盘空间，然后重新运行安装器。远程 Windows Agent 自带 runtime，不走这一步。

### 17.4 提示 Dashboard did not start

先查看：

```text
%LOCALAPPDATA%\Token Dashboard\server.log
```

再检查：

- `Token Dashboard Host` 任务是否正在运行；
- `8765` 端口是否被其他程序占用；
- 安装目录中的虚拟环境是否完整；
- 杀毒软件是否隔离了安装文件。

端口固定为 `127.0.0.1:8765`，当前脚本没有图形化改端口功能。应先关闭占用 8765 的其他程序，再重跑安装器。

### 17.5 重启后看板打不开

- 确认安装 Token Dashboard 的 Windows 用户已经登录；
- 在任务计划程序中检查并手动“运行” `Token Dashboard Host`；
- 打开 `http://127.0.0.1:8765/api/health`；
- 查看 `server.log`。

### 17.6 本机 Codex/Hermes 没数据

检查：

1. `Token Dashboard Agent` 计划任务是否存在；
2. 当前安装账号是否就是产生数据的账号；
3. `%USERPROFILE%\.codex` 是否存在；
4. 原生 Hermes 路径是否正确；
5. 下列日志：

   ```text
   %LOCALAPPDATA%\Token Dashboard Agent\scheduled-task.log
   %LOCALAPPDATA%\Token Dashboard Agent\agent.log
   ```

如果只有 Codex 或只有 Hermes，健康状态显示“部分可用”属于正常情况。

### 17.7 WSL Hermes 没数据

查看：

```text
%LOCALAPPDATA%\Token Dashboard Agent\hermes-locations.txt
```

常见结果：

- `no ~/.hermes/state.db`：该 WSL 用户下没有目标数据库；
- `Python was unavailable`：WSL 中既没有 `python3`，也没有 Hermes 自带 venv Python；
- 新增 WSL 后未扫描：安装时尚无该发行版。

修复路径或 Python 后，重新运行中心主机安装器以更新本机 Agent runtime 并重新扫描。Windows Agent 不读取 WSL Codex。

### 17.8 Tailscale Serve 配置失败

- 确认中心主机已安装并登录 Tailscale；
- 重新运行 `Token Dashboard - Tailscale`；
- 如果脚本提示权限问题，以管理员身份运行对应 `.cmd`；
- 不要改用 Funnel 或公网端口映射。

### 17.9 Add Device 没有自动给出 HTTPS 地址

默认地址来自中心主机本机的 Tailscale 状态和 DNS 名称。检查 Tailscale 是否在线；也可以手动粘贴 `Token Dashboard - Tailscale` 显示的 HTTPS 地址。

远程地址必须是 HTTPS。只有本机 `127.0.0.1`/`localhost` 才允许 HTTP。

### 17.10 远程 Windows Agent 提示 Tailscale 未安装或未连接

Windows Agent 对非 localhost 地址会主动检查 Tailscale：

1. 安装 Tailscale；
2. 登录正确 Tailnet；
3. 确认 Tailscale 状态正常；
4. 确认浏览器能打开中心 HTTPS 地址；
5. 重新运行 Agent 安装器。

### 17.11 远程 Mac 首次连接失败

Mac 安装器会保留安装并让后台 Agent 重试。恢复 Tailscale/网络，等待 1～2 分钟，再查看 `agent.log`、`launchd.log` 和 `launchd-error.log`。

### 17.12 日志显示 HTTP 401

表示设备密钥缺失、错误或已经吊销。不要修改 `agent-config.json` 猜测密钥，也不要复用其他设备的 ZIP。为该实体设备创建新 ZIP、安装并验证，再吊销旧设备记录。

### 17.13 Add Device 提示设备名称重复

中心数据库中的设备名称全局唯一。同名 Add Device 不会创建第二条记录，而会因名称冲突失败。即使旧设备已经吊销，它的记录和名称仍然保留，不会因吊销而释放。重新登记同一台实体设备时，请使用新的唯一名称，例如把 `Office-PC` 改为 `Office-PC-2`；不要反复用同一个名称重试。

### 17.14 Agent 断网后是否丢数据

Agent 会先把标准化事件保存在本地 `agent.sqlite3`，成功上报后记录已送达状态。网络恢复后，未送达事件会继续上传；不要在故障期间删除 Agent 数据目录。

### 17.15 需要查看哪些日志

| 位置 | 内容 |
|---|---|
| `%LOCALAPPDATA%\Token Dashboard\server.log` | 中心服务启动和运行错误 |
| `%LOCALAPPDATA%\Token Dashboard\snapshot.log` | 每日快照结果 |
| `%LOCALAPPDATA%\Token Dashboard Agent\scheduled-task.log` | Windows Agent 每分钟任务输出 |
| `%LOCALAPPDATA%\Token Dashboard Agent\agent.log` | Windows Agent 采集和上传日志 |
| `%LOCALAPPDATA%\Token Dashboard Agent\hermes-locations.txt` | native/WSL Hermes 扫描报告 |

安装脚本没有自动日志轮转。排障时不要把日志、数据库或 Agent 配置直接发到公共聊天；先检查其中是否含设备名、路径等私密信息。

---

## 18. 真实 Windows 首次交付验收清单

由于真实 Windows 安装器级冒烟验证尚未完成，首次交付前至少在一台全新的 Windows 10/11 x64 环境逐项确认：

### 中心主机

- [ ] Python 3.9+ 检测正确，安装与覆盖更新时依赖安装成功。
- [ ] 完整解压后可双击安装，无需手工复制文件。
- [ ] `Token Dashboard Host` 登录后启动，重启并重新登录后仍可访问。
- [ ] `Token Dashboard Agent` 每分钟运行。
- [ ] `Token Dashboard Daily Snapshot` 为 00:05，并验证错过后补跑。
- [ ] 桌面存在看板、Add Device、Devices、Backup、Tailscale 五类快捷方式。
- [ ] `http://127.0.0.1:8765` 和 `/api/health` 可访问。
- [ ] Windows 原生 Codex 可导入。
- [ ] Windows 原生 Hermes 可导入。
- [ ] 至少一个真实 WSL Hermes 可发现和同步；无 WSL Python 时提示符合预期。

### Tailscale 和远程设备

- [ ] Tailscale Serve HTTPS 仅在测试 Tailnet 内可访问，未启用 Funnel。
- [ ] Windows Agent ZIP 能在另一台 Windows 10/11 x64 安装并首传。
- [ ] macOS Agent ZIP 能在一台 Mac 安装并首传。
- [ ] 每台设备在看板中可独立筛选。
- [ ] 断开网络后产生的数据会在恢复后补传，且不会重复计数。
- [ ] 吊销一个设备后，该设备收到认证失败，其他设备继续正常工作。

### 维护流程

- [ ] Backup 快捷方式生成可打开的一致性 SQLite 文件。
- [ ] 使用新主机包覆盖安装后，数据库和本机 Agent 身份保留，Agent runtime 更新。
- [ ] 主机重启、用户注销/登录、电脑睡眠/唤醒后的行为符合本文说明。
- [ ] Windows Agent、Mac Agent 和中心主机卸载脚本均按预期只移除后台任务并保留数据。
- [ ] 完全删除前已确认 Tailscale Serve 需另行关闭。

在上述真实环境检查完成并记录结果之前，不应把“协议自动测试通过”表述成“Windows 安装包已经完成实机验收”。
