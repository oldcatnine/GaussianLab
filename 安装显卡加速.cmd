@echo off
cd /d "%~dp0"
where pwsh >nul 2>nul
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_cuda_runtime.ps1" %*
) else (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_cuda_runtime.ps1" %*
)
if errorlevel 1 (
  pause
  exit /b 1
)
pause
