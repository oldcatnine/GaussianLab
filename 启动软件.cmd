@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 项目运行环境不存在，请查阅 README.md。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m gaussian_lab
if errorlevel 1 pause
