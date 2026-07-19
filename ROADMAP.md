# Roadmap

Token Dashboard is developed as a privacy-first, local-first project. Roadmap
items describe direction rather than guaranteed delivery dates.

## 0.1 preview — current

- Codex and Hermes local collection.
- macOS and Windows Host packages.
- macOS and Windows remote Agents, including Hermes CLI in WSL.
- Multi-device and multi-account analytics.
- Three dashboard themes and Chinese/English UI.
- Per-device write credentials, offline delivery queues, backups, and device
  revocation.

## 0.2 — installation confidence

- Complete end-to-end Windows 10/11 x64 Host validation.
- Add macOS and Windows CI smoke-test coverage where practical.
- Improve installation diagnostics and source path discovery.
- Add versioned upgrade and rollback documentation.
- Publish checksums with every release.

## 0.3 — data quality and operations

- Add a visible data-quality and collector compatibility report.
- Add backup restore verification and migration diagnostics.
- Improve device last-seen, credential rotation, and revocation workflows.
- Add export of aggregated, non-sensitive usage data.

## 1.0 — stable self-hosted release

- Signed/notarized installation experience where release infrastructure allows.
- Stable database migration policy.
- Documented compatibility matrix for supported Codex and Hermes versions.
- Reproducible release workflow and expanded security scanning.

## Ideas under consideration

- Optional cost estimates and budget alerts.
- Additional local coding-agent sources, based on community demand and the
  availability of reliable local usage records.
- Optional application-level read authentication in addition to Tailnet access
  controls.
- Static demo site using synthetic data.

Open a feature request or start a Discussion before implementing a large item.
Privacy, data correctness, and installation reliability take priority over the
number of supported providers.

