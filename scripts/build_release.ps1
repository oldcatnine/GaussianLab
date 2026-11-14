$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $pythonPath -m PyInstaller --noconfirm GaussianLab.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
& $pythonPath scripts/prepare_release.py
if ($LASTEXITCODE -ne 0) { throw 'Release staging failed.' }
Write-Output 'Release files are available in releases/v0.1.0.'
