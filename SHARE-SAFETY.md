# Privacy-safe source package

This archive contains application source only. It intentionally excludes the
original owner's Token database, logs, screenshots, local paths, Tailnet URL,
remote-agent configuration, device credential, generated Agent ZIP, dependency
caches, and build output.

Run `install.command` on the recipient's Mac to create a new local database from
that recipient's own Codex and Hermes data. Remote access and remote collectors
must be configured with the recipient's own Tailscale network and newly issued
device credentials.
