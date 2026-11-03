@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0scripts\start_spendsense.ps1" -Service tunnel
if errorlevel 1 (
  echo SpendSense tunnel failed to start. Check the message above.
  pause
)
