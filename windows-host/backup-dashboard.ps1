$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$Python = Join-Path $InstallDir "venv\Scripts\python.exe"
$Backend = Join-Path $InstallDir "backend"
$BackupDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Token Dashboard Backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$Output = Join-Path $BackupDir ("token-dashboard-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".sqlite3")
$env:PYTHONPATH = $Backend
$env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
$env:TOKEN_DASHBOARD_DB = Join-Path $DataDir "token-dashboard.sqlite3"
$env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"
& $Python -m app.cli backup --output $Output
if ($LASTEXITCODE -ne 0) { throw "Database backup failed" }
Write-Host ""
Write-Host "Backup created:" -ForegroundColor Green
Write-Host "  $Output"
Write-Host "It contains complete usage and device history. Keep it private."
