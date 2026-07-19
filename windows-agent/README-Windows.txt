Token Dashboard Windows Agent
=============================

Purpose
-------
Read Codex and Hermes token counters from this Windows account and submit only
normalized token events to a Mac or Windows central host through Tailscale HTTPS.

Install
-------
1. Make sure Tailscale is connected to the same tailnet as the central host.
2. Extract this ZIP to a normal local folder.
3. Double-click "Install-Token-Agent.cmd".
4. Keep the window open until "Installation completed" appears.
5. Delete the downloaded ZIP after a successful installation because it
   contains this device's write-only enrollment token.

Default source paths
--------------------
%USERPROFILE%\.codex
%LOCALAPPDATA%\hermes\state.db (Hermes Desktop / native Windows)
~/.hermes/state.db inside every installed WSL distribution (older CLI)

The installer automatically checks both native Windows and every WSL
distribution. For WSL it exports only the sessions table's token counters into
a local temporary SQLite file; messages and prompts are never copied.

Privacy
-------
The agent never uploads prompts, responses, cookies, API keys, original JSONL
files, or the Hermes database. It sends token counts, timestamps, source,
model, device/account labels, and hashed session identifiers only.
