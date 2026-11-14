$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $pythonPath -m PyInstaller --noconfirm GaussianLab.spec
if ($LASTEXITCODE -ne 0) { throw '可执行程序构建失败。' }
& $pythonPath scripts/prepare_release.py
if ($LASTEXITCODE -ne 0) { throw '发行文件整理失败。' }
Write-Output '发行文件已生成于 releases/v0.1.0。'
