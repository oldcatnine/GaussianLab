@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Project environment is missing. See README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m gaussian_lab
if errorlevel 1 pause
