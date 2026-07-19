$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "Token Dashboard Host"
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$BackendDir = Join-Path $InstallDir "backend"
$FrontendDir = Join-Path $InstallDir "frontend"
$VenvDir = Join-Path $InstallDir "venv"
$ServerTask = "Token Dashboard Host"
$SnapshotTask = "Token Dashboard Daily Snapshot"
$AgentTask = "Token Dashboard Agent"
$DatabasePath = Join-Path $DataDir "token-dashboard.sqlite3"
$DatabaseExisted = Test-Path $DatabasePath

function Find-Python {
  $Candidates = @()
  $PyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
  if ($PyLauncher) {
    $Resolved = (& $PyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null |
      Select-Object -First 1)
    if ($Resolved) { $Candidates += $Resolved.Trim() }
  }
  $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($PythonCommand) { $Candidates += $PythonCommand.Source }
  foreach ($Candidate in $Candidates | Select-Object -Unique) {
    $Supported = & $Candidate -c "import sys; print(int(sys.version_info >= (3,9)))" 2>$null
    if ($Supported -eq "1") { return $Candidate }
  }
  throw "Python 3.9 or newer is required. Install Python from python.org and enable Add Python to PATH."
}

function Register-UserTask([string]$Name, $Trigger, [string]$ScriptPath, [bool]$StartWhenAvailable) {
  $Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
  $Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
  $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -StartWhenAvailable:$StartWhenAvailable
  Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger `
    -Principal $Principal -Settings $Settings -Force | Out-Null
  Enable-ScheduledTask -TaskName $Name | Out-Null
}

function Stop-UserTask([string]$Name) {
  $Task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if (-not $Task) { return }
  Disable-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue | Out-Null
  Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    $Task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if (-not $Task -or $Task.State -ne "Running") { return }
    Start-Sleep -Milliseconds 250
  }
  throw "Unable to stop the existing scheduled task: $Name"
}

function New-CommandShortcut([string]$Name, [string]$Target) {
  try {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    if (-not $Desktop) { return }
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "$Name.lnk"))
    $Shortcut.TargetPath = $Target
    $Shortcut.WorkingDirectory = Split-Path -Parent $Target
    $Shortcut.Save()
  } catch {
    Write-Warning "Unable to create the desktop shortcut: $Name"
  }
}

Write-Host "==> Checking the Windows host package"
foreach ($Required in @(
  "backend\app", "backend\requirements-host.txt", "frontend\index.html",
  "templates\Token-Dashboard-Agent-Windows-x64.template.zip",
  "templates\Token-Dashboard-Agent-macOS.template.zip"
)) {
  if (-not (Test-Path (Join-Path $PackageRoot $Required))) {
    throw "Package component is missing: $Required"
  }
}
$BasePython = Find-Python
Write-Host "    Python: $BasePython"

Write-Host "==> Stopping existing dashboard tasks"
Stop-UserTask $ServerTask
Stop-UserTask $SnapshotTask

Write-Host "==> Installing the private dashboard"
New-Item -ItemType Directory -Force -Path $InstallDir, $DataDir | Out-Null
if (Test-Path $BackendDir) { Remove-Item -Recurse -Force $BackendDir }
if (Test-Path $FrontendDir) { Remove-Item -Recurse -Force $FrontendDir }
New-Item -ItemType Directory -Force -Path $BackendDir, $FrontendDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $PackageRoot "backend\app") $BackendDir
Copy-Item -Force (Join-Path $PackageRoot "backend\requirements-host.txt") $BackendDir
Copy-Item -Recurse -Force (Join-Path $PackageRoot "frontend\*") $FrontendDir
Copy-Item -Force (Join-Path $PackageRoot "server.ps1") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "snapshot.ps1") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Create-Remote-Agent.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "create-remote-agent.ps1") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Open-Token-Dashboard.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Backup-Token-Dashboard.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "backup-dashboard.ps1") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Manage-Remote-Devices.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "manage-remote-devices.ps1") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Configure-Tailscale-Serve.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "Uninstall-Token-Dashboard.cmd") $InstallDir
Copy-Item -Force (Join-Path $PackageRoot "README-Windows-Host.txt") $InstallDir
if (Test-Path (Join-Path $PackageRoot "INSTALL-WINDOWS-HOST.md")) {
  Copy-Item -Force (Join-Path $PackageRoot "INSTALL-WINDOWS-HOST.md") $InstallDir
}
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "templates") | Out-Null
Copy-Item -Force (Join-Path $PackageRoot "templates\*.zip") (Join-Path $InstallDir "templates")

Write-Host "==> Preparing the Python environment"
if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
  & $BasePython -m venv $VenvDir
}
$HostPython = Join-Path $VenvDir "Scripts\python.exe"
& $HostPython -m pip install --quiet --upgrade pip
& $HostPython -m pip install --quiet -r (Join-Path $BackendDir "requirements-host.txt")

Write-Host "==> Registering startup and daily snapshot tasks"
$LogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
Register-UserTask $ServerTask $LogonTrigger (Join-Path $InstallDir "server.ps1") $true
$DailyTrigger = New-ScheduledTaskTrigger -Daily -At "00:05"
Register-UserTask $SnapshotTask $DailyTrigger (Join-Path $InstallDir "snapshot.ps1") $true

Write-Host "==> Starting the dashboard"
Start-ScheduledTask -TaskName $ServerTask
$Healthy = $false
for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
  Start-Sleep -Seconds 1
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 2 | Out-Null
    $Healthy = $true
    break
  } catch {}
}
if (-not $Healthy) {
  throw "The dashboard did not start. Check $DataDir\server.log"
}

$ExistingAgentConfig = Join-Path $env:LOCALAPPDATA "Token Dashboard Agent\agent-config.json"
Write-Host "==> Installing or updating this Windows computer's collector"
$TempRoot = Join-Path $env:TEMP ("token-dashboard-local-agent-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
try {
  $Template = Join-Path $InstallDir "templates\Token-Dashboard-Agent-Windows-x64.template.zip"
  Expand-Archive -Path $Template -DestinationPath $TempRoot -Force
  $LocalConfig = Join-Path $TempRoot "agent-config.json"
  if ($DatabaseExisted -and (Test-Path $ExistingAgentConfig)) {
    Copy-Item -Force $ExistingAgentConfig $LocalConfig
    Write-Host "    Keeping the existing device identity and updating the collector runtime"
  } else {
    $env:PYTHONPATH = $BackendDir
    $env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
    $env:TOKEN_DASHBOARD_DB = $DatabasePath
    $env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"
    $CollectorName = if ($DatabaseExisted) {
      "$env:COMPUTERNAME - Local Collector Recovery " + [Guid]::NewGuid().ToString("N").Substring(0, 8)
    } else {
      "$env:COMPUTERNAME - Local Collector"
    }
    & $HostPython -m app.cli provision-device --name $CollectorName `
      --platform windows --server "http://127.0.0.1:8765" --output $LocalConfig | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $LocalConfig)) {
      throw "Unable to provision the local Windows collector"
    }
  }
  Stop-UserTask $AgentTask
  Unregister-ScheduledTask -TaskName $AgentTask -Confirm:$false `
    -ErrorAction SilentlyContinue
  & powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $TempRoot "install-agent.ps1")
  if ($LASTEXITCODE -ne 0) { throw "The local Windows collector installation failed" }
} finally {
  if (Test-Path $TempRoot) { Remove-Item -Recurse -Force $TempRoot }
}

New-CommandShortcut "Token Dashboard" (Join-Path $InstallDir "Open-Token-Dashboard.cmd")
New-CommandShortcut "Token Dashboard - Add Device" (Join-Path $InstallDir "Create-Remote-Agent.cmd")
New-CommandShortcut "Token Dashboard - Backup" (Join-Path $InstallDir "Backup-Token-Dashboard.cmd")
New-CommandShortcut "Token Dashboard - Devices" (Join-Path $InstallDir "Manage-Remote-Devices.cmd")
New-CommandShortcut "Token Dashboard - Tailscale" (Join-Path $InstallDir "Configure-Tailscale-Serve.cmd")

Start-Process "http://127.0.0.1:8765"
Write-Host ""
Write-Host "Installation completed." -ForegroundColor Green
Write-Host "Local dashboard: http://127.0.0.1:8765"
Write-Host ""
Write-Host "For other computers:"
Write-Host "  1. Run Configure-Tailscale-Serve.cmd once."
Write-Host "  2. Run Create-Remote-Agent.cmd for each Windows or Mac computer."
