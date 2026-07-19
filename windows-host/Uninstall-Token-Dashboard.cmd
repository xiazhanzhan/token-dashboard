@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Stop-ScheduledTask -TaskName 'Token Dashboard Host' -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'Token Dashboard Host' -Confirm:$false -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'Token Dashboard Daily Snapshot' -Confirm:$false -ErrorAction SilentlyContinue"
schtasks.exe /Delete /TN "Token Dashboard Agent" /F >nul 2>&1
echo Dashboard and collector tasks were removed.
echo Programs and private data were kept under %%LOCALAPPDATA%%.
echo Revoke remote devices before deleting the database.
pause
