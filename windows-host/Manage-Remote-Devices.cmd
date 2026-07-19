@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0manage-remote-devices.ps1"
echo.
pause
