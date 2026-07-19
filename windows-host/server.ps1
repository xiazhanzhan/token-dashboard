$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$Python = Join-Path $InstallDir "venv\Scripts\python.exe"
$Backend = Join-Path $InstallDir "backend"
$Frontend = Join-Path $InstallDir "frontend"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$env:PYTHONPATH = $Backend
$env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
$env:TOKEN_DASHBOARD_DB = Join-Path $DataDir "token-dashboard.sqlite3"
$env:TOKEN_DASHBOARD_FRONTEND_DIST = $Frontend
$env:TOKEN_DASHBOARD_DEVICE_NAME = "$env:COMPUTERNAME - Host"
$env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"
& $Python -m uvicorn app.main:app --app-dir $Backend --host 127.0.0.1 `
  --port 8765 --no-access-log *>> (Join-Path $DataDir "server.log")
