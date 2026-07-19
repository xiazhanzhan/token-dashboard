# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-19

Initial public preview.

### Added

- Local Codex and Hermes Token collection with daily, weekly, monthly, and
  yearly aggregation.
- React, TypeScript, and ECharts dashboard with three themes and Chinese/English
  interface switching.
- macOS Host package that can collect from remote macOS and Windows computers.
- Windows x64 Host package that can collect from remote Windows and macOS
  computers.
- Tailscale Serve integration, per-device write credentials, offline Agent
  delivery queues, backups, and device revocation.
- Privacy-safe source distribution, automated backend/frontend tests, and
  Dependabot configuration.

### Known limitations

- The Windows Host installer has static and automated test coverage but still
  requires final end-to-end validation on representative Windows 10/11 x64
  systems before the preview label is removed.
- Hermes historical session totals may not contain per-call timestamps and are
  therefore assigned to the session start date during the initial import.
