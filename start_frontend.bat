@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0scripts\start_spendsense.ps1" -Service frontend
if errorlevel 1 (
  echo SpendSense frontend failed to start. Check the message above.
  pause
)
