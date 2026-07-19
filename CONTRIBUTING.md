# Contributing

Thank you for helping improve Token Dashboard.

## Before opening a pull request

1. Do not include real Token usage, session identifiers, local paths, Tailnet
   addresses, databases, logs, configured Agent ZIPs, or credentials.
2. Keep the service bound to `127.0.0.1` unless a reviewed design explicitly
   changes the security model.
3. Add or update tests when behavior changes.
4. Run the backend and frontend checks below.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
backend/.venv/bin/pytest -q

npm --prefix frontend ci
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

## Pull requests

- Explain what changed and why.
- Describe privacy or migration impact when data collection changes.
- Use synthetic fixtures and screenshots only.
- Keep unrelated changes in separate pull requests.

## Release safety

Only generic Host packages and unconfigured Agent templates may be released.
A configured single-device Agent ZIP contains a credential and must never be
attached to an issue, pull request, commit, or release.
