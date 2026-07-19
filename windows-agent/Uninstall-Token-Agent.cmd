@echo off
setlocal
schtasks.exe /Delete /TN "Token Dashboard Agent" /F
echo Background task removed. Local agent data remains under:
echo %LOCALAPPDATA%\Token Dashboard Agent
pause
