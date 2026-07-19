$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "Token Dashboard Agent"
$RuntimeTarget = Join-Path $InstallDir "runtime"
$ConfigSource = Join-Path $PackageRoot "agent-config.json"
$ConfigTarget = Join-Path $InstallDir "agent-config.json"
$TaskName = "Token Dashboard Agent"
$SyncCmd = Join-Path $InstallDir "sync-agent.cmd"
$SyncScript = Join-Path $InstallDir "sync-agent.ps1"
$WslSourcesPath = Join-Path $InstallDir "wsl-sources.json"
$ReportPath = Join-Path $InstallDir "hermes-locations.txt"

function Write-Utf8Json([string]$Path, $Value) {
  $Json = ConvertTo-Json -InputObject $Value -Depth 8
  $Utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Json, $Utf8)
}

function Protect-Config([string]$Path) {
  $Identity = "$env:USERDOMAIN\$env:USERNAME"
  & icacls.exe $Path /inheritance:r /grant:r "${Identity}:(M)" | Out-Null
}

Write-Host "==> Checking package"
if (-not (Test-Path $ConfigSource)) { throw "agent-config.json is missing" }
if (-not (Test-Path (Join-Path $PackageRoot "runtime\python.exe"))) {
  throw "Portable Python runtime is missing"
}

$Config = Get-Content $ConfigSource -Raw | ConvertFrom-Json
$ServerUri = [Uri]$Config.server_url
$IsLoopback = $ServerUri.IsLoopback
if (-not $IsLoopback) {
  Write-Host "==> Checking Tailscale connection"
  $TailscaleCommand = Get-Command tailscale.exe -ErrorAction SilentlyContinue
  $TailscalePath = if ($TailscaleCommand) { $TailscaleCommand.Source } else { $null }
  if (-not $TailscalePath) {
    $Candidate = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $Candidate) { $TailscalePath = $Candidate }
  }
  if (-not $TailscalePath) { throw "Tailscale is not installed or not available in PATH" }
  & $TailscalePath status | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Tailscale is not connected" }
} else {
  Write-Host "==> Using the local Windows dashboard"
}

Write-Host "==> Installing collector into $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
if (Test-Path $RuntimeTarget) { Remove-Item -Recurse -Force $RuntimeTarget }
Copy-Item -Recurse -Force (Join-Path $PackageRoot "runtime") $RuntimeTarget
Copy-Item -Force $ConfigSource $ConfigTarget
Copy-Item -Force (Join-Path $PackageRoot "sync-agent.ps1") $SyncScript
Copy-Item -Force (Join-Path $PackageRoot "wsl-hermes-export.py") `
  (Join-Path $InstallDir "wsl-hermes-export.py")
Copy-Item -Force (Join-Path $PackageRoot "Uninstall-Token-Agent.cmd") `
  (Join-Path $InstallDir "Uninstall-Token-Agent.cmd")
Copy-Item -Force (Join-Path $PackageRoot "README-Windows.txt") `
  (Join-Path $InstallDir "README-Windows.txt")

$Separator = [char]0x00B7
$Config | Add-Member -Force -NotePropertyName data_dir -NotePropertyValue $InstallDir
$Config | Add-Member -Force -NotePropertyName codex_home `
  -NotePropertyValue (Join-Path $env:USERPROFILE ".codex")
$Config | Add-Member -Force -NotePropertyName profile_id -NotePropertyValue "windows-native"
$Config | Add-Member -Force -NotePropertyName account_keys -NotePropertyValue @{
  codex = "codex"
  hermes = "hermes"
}
$Config | Add-Member -Force -NotePropertyName account_labels -NotePropertyValue @{
  codex = "Codex $Separator $($Config.device_name)"
  hermes = "Hermes Desktop $Separator $($Config.device_name)"
}

Write-Host "==> Checking Hermes Desktop and native CLI locations"
$NativeCandidates = @()
if ($env:HERMES_HOME) {
  $NativeCandidates += (Join-Path $env:HERMES_HOME "state.db")
}
$NativeCandidates += (Join-Path $env:LOCALAPPDATA "hermes\state.db")
$NativeCandidates += (Join-Path $env:USERPROFILE ".hermes\state.db")
$NativeHermes = $NativeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $NativeHermes) {
  $NativeHermes = Join-Path $env:LOCALAPPDATA "hermes\state.db"
  Write-Warning "No native Hermes state.db exists yet; watching $NativeHermes"
} else {
  Write-Host "    Found native Hermes: $NativeHermes" -ForegroundColor Green
}
$Config.hermes_database_path = $NativeHermes
Write-Utf8Json $ConfigTarget $Config
Protect-Config $ConfigTarget

Write-Host "==> Checking older Hermes CLI installations inside WSL"
$WslSources = @()
$LocationReport = @("Hermes location scan: $(Get-Date -Format s)")
$LocationReport += "Native: $NativeHermes (exists: $(Test-Path $NativeHermes))"
$WslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($WslCommand) {
  $Distros = @(& wsl.exe --list --quiet 2>$null) | ForEach-Object {
    ($_ -replace "`0", "").Trim()
  } | Where-Object { $_ }
  foreach ($Distro in $Distros) {
    & wsl.exe -d $Distro -- sh -lc 'test -f "$HOME/.hermes/state.db"' 2>$null
    if ($LASTEXITCODE -ne 0) {
      $LocationReport += "WSL ${Distro}: no ~/.hermes/state.db"
      continue
    }
    $HomePath = ((& wsl.exe -d $Distro -- sh -lc 'printf %s "$HOME"' 2>$null) |
      Select-Object -First 1).Trim()
    $PythonPath = ((& wsl.exe -d $Distro -- sh -lc `
      'if command -v python3 >/dev/null 2>&1; then command -v python3; elif [ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]; then printf %s "$HOME/.hermes/hermes-agent/venv/bin/python"; fi' `
      2>$null) | Select-Object -First 1).Trim()
    if (-not $PythonPath) {
      $LocationReport += "WSL ${Distro}: found $HomePath/.hermes/state.db, but Python was unavailable"
      Write-Warning "Found Hermes in WSL $Distro but could not find Python"
      continue
    }
    $WslInstallDir = ((& wsl.exe -d $Distro -- wslpath -a $InstallDir 2>$null) |
      Select-Object -First 1).Trim()
    $SafeDistro = (($Distro.ToLower() -replace '[^a-z0-9_-]', '-') -replace '-+', '-').Trim('-')
    if (-not $SafeDistro) { $SafeDistro = "linux" }
    $ExportWindows = Join-Path $InstallDir "wsl-$SafeDistro-sessions.db"
    $ExportWsl = "$($WslInstallDir.TrimEnd('/'))/wsl-$SafeDistro-sessions.db"
    $ExporterWsl = "$($WslInstallDir.TrimEnd('/'))/wsl-hermes-export.py"
    $WslConfigPath = Join-Path $InstallDir "agent-config-wsl-$SafeDistro.json"
    $WslDataDir = Join-Path $InstallDir "data-wsl-$SafeDistro"
    $DisabledCodex = Join-Path $InstallDir "disabled-codex-wsl-$SafeDistro"
    $WslConfig = [ordered]@{
      schema_version = 1
      server_url = $Config.server_url
      device_id = $Config.device_id
      device_name = $Config.device_name
      device_token = $Config.device_token
      profile_id = "wsl-$SafeDistro"
      data_dir = $WslDataDir
      codex_home = $DisabledCodex
      hermes_database_path = $ExportWindows
      timezone = "Asia/Shanghai"
      sync_interval_seconds = 60
      account_keys = @{
        codex = "codex-wsl-$SafeDistro"
        hermes = "hermes-wsl-$SafeDistro"
      }
      account_labels = @{
        codex = "Codex $Separator WSL $Distro"
        hermes = "Hermes CLI $Separator WSL $Distro"
      }
    }
    Write-Utf8Json $WslConfigPath $WslConfig
    Protect-Config $WslConfigPath
    $WslSources += [ordered]@{
      distro = $Distro
      pythonPath = $PythonPath
      sourcePath = "$HomePath/.hermes/state.db"
      exporterPath = $ExporterWsl
      exportPath = $ExportWsl
      configPath = $WslConfigPath
    }
    $LocationReport += "WSL ${Distro}: $HomePath/.hermes/state.db"
    Write-Host "    Found WSL Hermes CLI: $Distro $HomePath/.hermes/state.db" -ForegroundColor Green
  }
}
Write-Utf8Json $WslSourcesPath $WslSources
[System.IO.File]::WriteAllLines($ReportPath, $LocationReport)

$Python = Join-Path $RuntimeTarget "python.exe"
$Log = Join-Path $InstallDir "scheduled-task.log"
$SyncContent = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SyncScript" >> "$Log" 2>&1
"@
Set-Content -Path $SyncCmd -Value $SyncContent -Encoding ASCII

Write-Host "==> Importing Codex, Hermes Desktop, and WSL Hermes CLI history"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $SyncScript
if ($LASTEXITCODE -ne 0) { throw "Initial collector sync failed" }

Write-Host "==> Registering one-minute background task"
$TaskCommand = '"' + $SyncCmd + '"'
& schtasks.exe /Create /TN $TaskName /SC MINUTE /MO 1 /TR $TaskCommand /F | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Unable to create scheduled task" }

# Remove the unpacked secret after it has been copied and ACL-protected. The
# downloaded ZIP should also be deleted after verification.
Remove-Item -Force $ConfigSource

Write-Host ""
Write-Host "Installation completed." -ForegroundColor Green
Write-Host "Device: $($Config.device_name)"
Write-Host "Dashboard: $($Config.server_url)"
Write-Host "Hermes location report: $ReportPath"
Write-Host "The first native and WSL historical imports have been submitted."
