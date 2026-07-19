# Audience growth playbook

This maintainer-only playbook keeps project promotion focused on useful,
privacy-safe communication rather than star exchanges or unsolicited posting.

## Positioning

Token Dashboard is not trying to be a generic billing platform. Its initial
position is:

> A privacy-first, self-hosted Token usage dashboard for Codex and Hermes across
> multiple devices and accounts.

Lead with the user problem: usage is fragmented across computers and accounts,
while cloud dashboards may not provide a single private view.

## Launch checklist

- [ ] English README is the default landing page.
- [ ] Chinese README is linked at the top.
- [ ] Social Preview is uploaded in repository settings.
- [ ] GitHub Topics describe the problem and supported platforms.
- [ ] `v0.1.0` Release contains macOS and Windows Host packages plus checksums.
- [ ] Discussions are enabled with Announcements, Q&A, Ideas, and Show and Tell.
- [ ] Bug, feature, and installation issue forms are visible.
- [ ] Branch protection requires CI before merge.
- [ ] No post or screenshot exposes real data or a Tailnet address.

## Chinese launch post

### Title

我做了一个本地优先的 Codex + Hermes 多设备 Token 统计看板

### Body

我同时在多台 Mac、Windows 和 WSL 中使用 Codex 与 Hermes，但每台设备的
Token 记录彼此分散，很难统一查看每天、每周、每月和每年的实际用量。

因此我做了 Token Dashboard：每台电脑只在本地读取自己的用量记录，再把
标准化的 Token 计数发送到我自己的 Mac 或 Windows 中心主机。它不会上传提示词、
回复正文或认证信息，中心服务默认只监听 127.0.0.1，远程访问推荐使用自己的
Tailscale 网络。

目前支持多设备、多账号筛选、Codex/Hermes 对比、Token 构成、模型排行、年度
热力图、会话明细、中英文界面和三套主题。macOS 流程已经完成本机验证，Windows
Host 仍属于预览版本，希望有 Windows 10/11 用户帮助测试安装流程。

项目地址：https://github.com/xiazhanzhan/token-dashboard

如果你也有多设备统计需求，最希望下一步改进安装体验、数据诊断，还是增加新的
本地 AI 工具来源？欢迎提出具体使用场景。

## English launch post

### Title

Token Dashboard — local-first multi-device usage analytics for Codex and Hermes

### Body

I use Codex and Hermes across several Macs, Windows PCs, and WSL environments.
Their local usage records are useful, but fragmented, so I built Token Dashboard
to aggregate daily, weekly, monthly, and yearly Token usage on a computer that I
control.

Each Agent reads only local counters and sends normalized Token events to a Mac
or Windows Host. Prompts, assistant messages, API keys, and authentication data
are not collected. The service stays on `127.0.0.1`, with private remote access
designed around your own Tailscale network.

The preview includes multi-device/account filters, source comparison, Token
composition, model ranking, a calendar heatmap, session details, three themes,
and a Chinese/English UI.

Repository: https://github.com/xiazhanzhan/token-dashboard

The macOS flow has been validated locally. Windows Host testing is the area
where feedback would be most useful. Which environment should I test or support
next?

## Suggested channels

Share only where project showcases are welcome and follow each community's
rules. Prioritize a few high-quality posts over posting the same message
everywhere.

- Chinese: V2EX, Juejin, Zhihu, Bilibili, relevant developer groups.
- English: Show HN, relevant Codex/self-hosted/Local LLM communities, DEV
  Community, and project-friendly discussion channels.
- Upstream communities: use showcase or discussion areas; do not advertise in
  unrelated bug reports.

## Weekly metrics

GitHub Traffic retains a short rolling window, so record these once per week:

| Week | Unique visitors | Views | Clones | Release downloads | Stars | Forks | Issues opened | Median first response |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| YYYY-Www |  |  |  |  |  |  |  |  |

Also record the top referrers and the most-viewed documentation page. Evaluate
the complete path from repository visit to successful installation rather than
optimizing only for Stars.
