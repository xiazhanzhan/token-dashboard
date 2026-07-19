$ErrorActionPreference = "Stop"
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA "Token Dashboard"
$Python = Join-Path $InstallDir "venv\Scripts\python.exe"
$Backend = Join-Path $InstallDir "backend"

$Name = Read-Host "Device name (for example Work-MacBook)"
if (-not $Name.Trim()) { throw "Device name cannot be empty" }
$PlatformInput = (Read-Host "Platform: type W for Windows or M for macOS").Trim().ToLower()
$Platform = if ($PlatformInput -in @("w", "win", "windows")) { "windows" } `
  elseif ($PlatformInput -in @("m", "mac", "macos")) { "macos" } `
  else { throw "Platform must be Windows or macOS" }

$DefaultServer = ""
$TailscaleCommand = Get-Command tailscale.exe -ErrorAction SilentlyContinue
$TailscalePath = if ($TailscaleCommand) { $TailscaleCommand.Source } else { $null }
if (-not $TailscalePath) {
  $Candidate = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
  if (Test-Path $Candidate) { $TailscalePath = $Candidate }
}
if ($TailscalePath) {
  try {
    $Status = (& $TailscalePath status --json | ConvertFrom-Json)
    $DnsName = [string]$Status.Self.DNSName
    if ($DnsName) { $DefaultServer = "https://" + $DnsName.TrimEnd('.') }
  } catch {}
}
$Prompt = if ($DefaultServer) { "Dashboard HTTPS address [$DefaultServer]" } `
  else { "Dashboard Tailscale HTTPS address" }
$Server = (Read-Host $Prompt).Trim()
if (-not $Server) { $Server = $DefaultServer }
if (-not $Server) { throw "Dashboard address cannot be empty" }

$SafeName = (($Name -replace '[^a-zA-Z0-9_-]', '-') -replace '-+', '-').Trim('-')
if (-not $SafeName) { $SafeName = "device" }
$Output = Join-Path ([Environment]::GetFolderPath("UserProfile")) `
  "Downloads\Token-Dashboard-Agent-$SafeName-$Platform.zip"
$TemplateName = if ($Platform -eq "windows") `
  { "Token-Dashboard-Agent-Windows-x64.template.zip" } `
  else { "Token-Dashboard-Agent-macOS.template.zip" }
$Template = Join-Path $InstallDir "templates\$TemplateName"

$env:PYTHONPATH = $Backend
$env:TOKEN_DASHBOARD_DATA_DIR = $DataDir
$env:TOKEN_DASHBOARD_DB = Join-Path $DataDir "token-dashboard.sqlite3"
$env:TOKEN_DASHBOARD_COLLECT_LOCAL = "0"
& $Python -m app.cli package-agent --name $Name --platform $Platform `
  --server $Server --template $Template --output $Output
if ($LASTEXITCODE -ne 0) { throw "Agent package creation failed" }

Write-Host ""
Write-Host "Agent package created:" -ForegroundColor Green
Write-Host "  $Output"
Write-Host "Send it only to the named device and delete the transport copy after installation."
