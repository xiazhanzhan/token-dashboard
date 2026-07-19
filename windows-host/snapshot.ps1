$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$Python = Join-Path $InstallDir "venv\Scripts\python.exe"
$Backend = Join-Path $InstallDir "backend"
$env:PYTHONPATH = $Backend
$env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
$env:TOKEN_DASHBOARD_DB = Join-Path $DataDir "token-dashboard.sqlite3"
$env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"
& $Python -m app.cli snapshot *>> (Join-Path $DataDir "snapshot.log")
