$ErrorActionPreference = "Continue"

$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $InstallDir "runtime\python.exe"
$MainConfig = Join-Path $InstallDir "agent-config.json"
$WslSourcesPath = Join-Path $InstallDir "wsl-sources.json"

function Invoke-AgentSync([string]$ConfigPath, [string]$Label) {
  Write-Host "[$(Get-Date -Format s)] Syncing $Label"
  & $Python -m app.agent --config $ConfigPath sync
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "$Label sync failed with exit code $LASTEXITCODE"
    return $false
  }
  return $true
}

$MainOk = Invoke-AgentSync $MainConfig "Windows Codex + Hermes Desktop"

if (Test-Path $WslSourcesPath) {
  $Sources = @(Get-Content $WslSourcesPath -Raw | ConvertFrom-Json)
  foreach ($Source in $Sources) {
    Write-Host "[$(Get-Date -Format s)] Exporting Hermes CLI counters from WSL $($Source.distro)"
    & wsl.exe -d $Source.distro -- $Source.pythonPath `
      $Source.exporterPath $Source.sourcePath $Source.exportPath
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Unable to export Hermes CLI counters from WSL $($Source.distro)"
      continue
    }
    Invoke-AgentSync $Source.configPath "Hermes CLI - $($Source.distro)" | Out-Null
  }
}

if (-not $MainOk) { exit 1 }
