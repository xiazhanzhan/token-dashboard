@echo off
setlocal
set "TS=%ProgramFiles%\Tailscale\tailscale.exe"
if not exist "%TS%" set "TS=tailscale.exe"
echo Publishing the local dashboard only inside your Tailscale network...
"%TS%" serve --bg http://127.0.0.1:8765
if errorlevel 1 (
  echo.
  echo If Windows requests administrator permission, reopen this file as administrator.
) else (
  echo.
  echo Tailscale Serve is configured. The HTTPS address is shown above.
)
pause
