@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_spendsense.ps1" -Service all
if errorlevel 1 (
  echo SpendSense did not start completely. Check the message above.
  pause
)
