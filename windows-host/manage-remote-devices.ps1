$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$Python = Join-Path $InstallDir "venv\Scripts\python.exe"
$Backend = Join-Path $InstallDir "backend"
$env:PYTHONPATH = $Backend
$env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
$env:TOKEN_DASHBOARD_DB = Join-Path $DataDir "token-dashboard.sqlite3"
$env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"

Write-Host "Current devices:"
& $Python -m app.cli devices
if ($LASTEXITCODE -ne 0) { throw "Unable to read the device list" }
$DeviceId = (Read-Host "Enter a dev_ device ID to revoke, or press Enter to close").Trim()
if ($DeviceId) {
  if (-not $DeviceId.StartsWith("dev_")) { throw "Invalid device ID" }
  $Confirm = Read-Host "Type REVOKE to disable $DeviceId"
  if ($Confirm -eq "REVOKE") {
    $RawResult = (& $Python -m app.cli revoke-device $DeviceId | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Unable to revoke the device" }
    Write-Host $RawResult
    $Result = $RawResult | ConvertFrom-Json
    if ([int]$Result.updated -eq 1) {
      Write-Host "Device revoked. Existing history remains in the dashboard." -ForegroundColor Green
    } else {
      Write-Warning "No enabled remote device matched that ID. Nothing changed."
    }
  } else {
    Write-Host "Cancelled."
  }
}
