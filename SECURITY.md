# Security Policy

## Supported versions

Security fixes are applied to the latest published release and the `main`
branch. Older releases may not receive backports.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose local
usage data, a Tailnet address, or a remote-device credential. Use GitHub's
private vulnerability reporting feature when it is enabled for this
repository. If it is not available, contact the repository owner privately.

Include only the minimum information needed to reproduce the problem. Never
attach a real Token database, Codex/Hermes data, log file, configured Agent ZIP,
or `agent-config.json`.

## Credential exposure response

If a `device_token`, configured Agent ZIP, or other credential is exposed:

1. Revoke the affected device from the dashboard host immediately.
2. Generate a new device package only after the old credential is revoked.
3. Remove the secret from every affected commit before pushing again.
4. If it was already pushed, follow GitHub's sensitive-data removal process.

Deleting the visible file alone does not invalidate a copied credential.

## Security boundaries

- The dashboard listens on `127.0.0.1:8765` only.
- Remote access is intended to use Tailscale Serve, not Funnel or public port
  forwarding.
- The dashboard currently has no application-level read login. Tailnet access
  rules are therefore part of the security boundary.
- Remote Agent credentials grant write access for one registered device and
  must not be reused or published.
- SQLite databases must stay on local storage and must not be placed on a
  network share.
