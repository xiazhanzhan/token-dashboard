@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup-dashboard.ps1"
echo.
pause
